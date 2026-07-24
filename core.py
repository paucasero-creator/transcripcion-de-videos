#!/usr/bin/env python3
"""
Transcriptor de vídeos de YouTube.

Transcribe un vídeo de YouTube a partir de su enlace. Hay dos métodos:

  - audio       (por defecto): descarga el audio con yt-dlp y lo transcribe con
                Whisper (OpenAI, en local). Es más preciso y funciona aunque el
                vídeo no tenga subtítulos. Detecta el idioma automáticamente y
                admite muchos idiomas.
  - subtitulos: usa los subtítulos de YouTube (más rápido, pero a menudo de peor
                calidad y no siempre disponibles).

Opcionalmente genera un breve resumen con los puntos más importantes usando la
API de Claude (Anthropic).

Uso:
    python transcriptor.py "https://www.youtube.com/watch?v=VIDEO_ID"
    python transcriptor.py "URL" --metodo subtitulos
    python transcriptor.py "URL" --idioma en          # forzar idioma
    python transcriptor.py "URL" --modelo small        # tamaño de Whisper
    python transcriptor.py "URL" --resumen --guardar transcripcion.txt

Requisitos:
    pip install -r requirements.txt
    Además, Whisper necesita 'ffmpeg' instalado en el sistema.

Para el resumen es necesario definir la variable de entorno ANTHROPIC_API_KEY.
"""

import os
import re
import sys
import tempfile

# Idiomas preferidos para el método de subtítulos, en orden de prioridad.
IDIOMAS_PREFERIDOS = ["es", "es-ES", "es-419", "en"]

MODELO_CLAUDE = "claude-opus-4-8"

# Tamaños de modelo de Whisper disponibles (de más rápido/ligero a más preciso).
MODELOS_WHISPER = ["tiny", "base", "small", "medium", "large"]


def extraer_id_video(url: str) -> str:
    """Extrae el ID del vídeo a partir de las distintas formas de URL de YouTube."""
    patrones = [
        r"(?:v=|\/)([0-9A-Za-z_-]{11}).*",
        r"(?:embed\/)([0-9A-Za-z_-]{11})",
        r"(?:youtu\.be\/)([0-9A-Za-z_-]{11})",
        r"(?:shorts\/)([0-9A-Za-z_-]{11})",
    ]
    for patron in patrones:
        coincidencia = re.search(patron, url)
        if coincidencia:
            return coincidencia.group(1)

    if re.fullmatch(r"[0-9A-Za-z_-]{11}", url):
        return url

    raise ValueError(f"No se ha podido extraer el ID del vídeo de: {url}")


# ---------------------------------------------------------------------------
# Método 1: transcripción desde el audio (Whisper) — por defecto
# ---------------------------------------------------------------------------

def descargar_audio(url: str, carpeta: str) -> str:
    """Descarga el audio del vídeo con yt-dlp y devuelve la ruta del archivo."""
    try:
        import yt_dlp
    except ImportError:
        raise RuntimeError(
            "Falta la librería 'yt-dlp'. Instálala con: pip install yt-dlp"
        )

    plantilla = os.path.join(carpeta, "audio.%(ext)s")
    opciones = {
        "format": "bestaudio/best",
        "outtmpl": plantilla,
        "quiet": True,
        "no_warnings": True,
        # Headers para evitar que YouTube bloquee
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        },
        # Reintentos y timeouts robustos
        "socket_timeout": 30,
        "retries": 3,
        # Descargar subtítulos si están disponibles (fallback a audio limpio)
        "skip_unavailable_fragments": True,
        "fragment_retries": 3,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "128",
            }
        ],
    }

    # Cookies de YouTube para saltar el bloqueo "confirma que no eres un bot"
    # (necesario en servidores como Render). Se pueden aportar de dos formas:
    #   - YT_COOKIES_FILE: ruta a un archivo de cookies (formato Netscape).
    #   - YT_COOKIES: contenido del archivo de cookies directamente (útil como
    #     variable de entorno en Render). Se vuelca a un archivo temporal.
    cookies_file = os.environ.get("YT_COOKIES_FILE")
    cookies_data = os.environ.get("YT_COOKIES")
    if not cookies_file and cookies_data:
        cookies_file = os.path.join(carpeta, "cookies.txt")
        with open(cookies_file, "w", encoding="utf-8") as f:
            f.write(cookies_data)
    if cookies_file and os.path.exists(cookies_file):
        opciones["cookiefile"] = cookies_file

    # Opción para usar un proxy (p. ej. residencial) y evitar el bloqueo por IP.
    proxy = os.environ.get("YT_PROXY")
    if proxy:
        opciones["proxy"] = proxy

    try:
        with yt_dlp.YoutubeDL(opciones) as ydl:
            ydl.download([url])
    except Exception as e:
        raise RuntimeError(
            f"No se ha podido descargar el audio de YouTube: {e}. "
            "Si el vídeo está protegido, intenta con la versión HTML (sube un archivo)."
        )

    ruta = os.path.join(carpeta, "audio.mp3")
    if not os.path.exists(ruta):
        for nombre in os.listdir(carpeta):
            if nombre.startswith("audio."):
                return os.path.join(carpeta, nombre)
        raise RuntimeError("No se ha encontrado el archivo de audio descargado.")
    return ruta


def transcribir_con_whisper(url: str, modelo: str, idioma: str | None) -> str:
    """Descarga el audio y lo transcribe con Whisper (en local)."""
    try:
        import whisper
    except ImportError:
        raise RuntimeError(
            "Falta la librería 'openai-whisper'. Instálala con: "
            "pip install openai-whisper (y asegúrate de tener ffmpeg instalado)."
        )

    with tempfile.TemporaryDirectory() as carpeta:
        print("Descargando el audio del vídeo...", file=sys.stderr)
        ruta_audio = descargar_audio(url, carpeta)

        print(f"Cargando el modelo de Whisper '{modelo}'...", file=sys.stderr)
        modelo_whisper = whisper.load_model(modelo)

        print("Transcribiendo el audio (esto puede tardar un rato)...",
              file=sys.stderr)
        opciones = {}
        if idioma:
            opciones["language"] = idioma
        resultado = modelo_whisper.transcribe(ruta_audio, **opciones)

    idioma_detectado = resultado.get("language")
    if idioma_detectado and not idioma:
        print(f"Idioma detectado: {idioma_detectado}", file=sys.stderr)

    texto = resultado.get("text", "").strip()
    if not texto:
        raise RuntimeError("Whisper no ha devuelto ninguna transcripción.")
    return texto


# ---------------------------------------------------------------------------
# Método 2: transcripción desde los subtítulos de YouTube
# ---------------------------------------------------------------------------

def transcribir_con_subtitulos(video_id: str, idioma: str | None) -> str:
    """Obtiene la transcripción de los subtítulos de YouTube."""
    from youtube_transcript_api import YouTubeTranscriptApi
    from youtube_transcript_api._errors import (
        NoTranscriptFound,
        TranscriptsDisabled,
        VideoUnavailable,
    )

    try:
        lista = YouTubeTranscriptApi.list_transcripts(video_id)
    except TranscriptsDisabled:
        raise RuntimeError(
            "Este vídeo tiene los subtítulos desactivados. Prueba con "
            "--metodo audio."
        )
    except VideoUnavailable:
        raise RuntimeError("El vídeo no está disponible.")

    idiomas = [idioma] if idioma else IDIOMAS_PREFERIDOS

    transcript = None
    try:
        transcript = lista.find_transcript(idiomas)
    except NoTranscriptFound:
        for t in lista:
            transcript = t
            break

    if transcript is None:
        raise RuntimeError(
            "No se ha encontrado ningún subtítulo. Prueba con --metodo audio."
        )

    datos = transcript.fetch()
    texto = " ".join(fragmento["text"].strip() for fragmento in datos)
    return re.sub(r"\s+", " ", texto).strip()


# ---------------------------------------------------------------------------
# Resumen con Claude
# ---------------------------------------------------------------------------

def generar_resumen(texto: str) -> str:
    """Genera un breve resumen con los puntos más importantes usando Claude."""
    try:
        import anthropic
    except ImportError:
        raise RuntimeError(
            "Falta la librería 'anthropic'. Instálala con: pip install anthropic"
        )

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Para generar el resumen define la variable de entorno ANTHROPIC_API_KEY."
        )

    client = anthropic.Anthropic(api_key=api_key)

    prompt = (
        "A continuación tienes la transcripción completa de un vídeo. Redacta un "
        "resumen breve y claro, en el mismo idioma que la transcripción, que "
        "recoja las ideas y los puntos más importantes. Empieza con un párrafo "
        "de resumen general y después incluye una lista con los puntos clave.\n\n"
        f"Transcripción:\n{texto}"
    )

    with client.messages.stream(
        model=MODELO_CLAUDE,
        max_tokens=1500,
        thinking={"type": "adaptive"},
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        mensaje = stream.get_final_message()

    partes = [bloque.text for bloque in mensaje.content if bloque.type == "text"]
    return "\n".join(partes).strip()


# Nombres legibles de idioma para el prompt de traducción.
NOMBRES_IDIOMA = {
    "es": "español", "en": "inglés", "fr": "francés", "de": "alemán",
    "it": "italiano", "pt": "portugués", "ca": "catalán", "gl": "gallego",
    "eu": "euskera", "zh": "chino", "ja": "japonés", "ru": "ruso",
    "ar": "árabe",
}


def traducir(texto: str, idioma_destino: str) -> str:
    """Traduce la transcripción al idioma indicado usando Claude."""
    try:
        import anthropic
    except ImportError:
        raise RuntimeError(
            "Falta la librería 'anthropic'. Instálala con: pip install anthropic"
        )

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Para traducir define la variable de entorno ANTHROPIC_API_KEY."
        )

    nombre = NOMBRES_IDIOMA.get(idioma_destino, idioma_destino)
    client = anthropic.Anthropic(api_key=api_key)

    prompt = (
        f"Traduce el siguiente texto al {nombre}. Devuelve únicamente la "
        "traducción, sin comentarios ni notas, respetando el sentido y el tono "
        "original. Si el texto ya está en ese idioma, devuélvelo tal cual.\n\n"
        f"Texto:\n{texto}"
    )

    with client.messages.stream(
        model=MODELO_CLAUDE,
        max_tokens=8000,
        thinking={"type": "adaptive"},
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        mensaje = stream.get_final_message()

    partes = [bloque.text for bloque in mensaje.content if bloque.type == "text"]
    return "\n".join(partes).strip()


def transcribir(url: str, metodo: str = "audio", idioma: str | None = None,
                modelo: str = "base") -> str:
    """Función de alto nivel: transcribe un vídeo con el método indicado.

    El método 'audio' funciona con cualquier web que soporte yt-dlp (YouTube,
    Twitter/X, Instagram, TikTok, Vimeo, Facebook...). El método 'subtitulos'
    es solo para YouTube.
    Si el audio de YouTube falla por cookies, cambia automáticamente a subtítulos.
    """
    if metodo == "audio":
        # El audio no necesita ID: yt-dlp acepta la URL directamente (multi-web).
        try:
            return transcribir_con_whisper(url, modelo, idioma)
        except RuntimeError as e:
            # Si falla por cookies/autenticación de YouTube, intenta con subtítulos.
            if "cookies" in str(e).lower() or "sign in" in str(e).lower():
                print("Audio bloqueado por YouTube; intentando con subtítulos...", file=sys.stderr)
                try:
                    video_id = extraer_id_video(url)
                    return transcribir_con_subtitulos(video_id, idioma)
                except (ValueError, RuntimeError):
                    # Si no es YouTube o no hay subtítulos, devuelve el error del audio.
                    raise e
            raise

    # Método subtítulos: solo YouTube (necesita el ID del vídeo).
    video_id = extraer_id_video(url)
    return transcribir_con_subtitulos(video_id, idioma)
