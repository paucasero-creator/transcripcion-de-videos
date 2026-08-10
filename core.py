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
# Utilidades de yt-dlp (cookies / proxy)
# ---------------------------------------------------------------------------

def _aplicar_cookies_proxy(opciones: dict, carpeta: str | None) -> None:
    """Añade cookies y proxy a las opciones de yt-dlp si están configurados por
    variables de entorno. Sirve para saltar el bloqueo de YouTube en servidores.

    - YT_COOKIES_FILE: ruta a un archivo de cookies (formato Netscape).
    - YT_COOKIES: contenido del archivo de cookies (se vuelca a un temporal).
    - YT_PROXY: URL de un proxy.
    """
    cookies_file = os.environ.get("YT_COOKIES_FILE")
    cookies_data = os.environ.get("YT_COOKIES")
    if not cookies_file and cookies_data and carpeta:
        cookies_file = os.path.join(carpeta, "cookies.txt")
        with open(cookies_file, "w", encoding="utf-8") as f:
            f.write(cookies_data)
    if cookies_file and os.path.exists(cookies_file):
        opciones["cookiefile"] = cookies_file

    proxy = os.environ.get("YT_PROXY")
    if proxy:
        opciones["proxy"] = proxy


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

    _aplicar_cookies_proxy(opciones, carpeta)

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


def transcribir_con_whisper(url: str, modelo: str, idioma: str | None):
    """Descarga el audio y lo transcribe con Whisper (en local).

    Devuelve una tupla (texto, segmentos), donde segmentos es una lista de
    diccionarios {'inicio': segundos, 'fin': segundos, 'texto': str}.
    """
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

    segmentos = [
        {"inicio": s.get("start", 0.0), "fin": s.get("end", 0.0),
         "texto": s.get("text", "").strip()}
        for s in resultado.get("segments", [])
    ]
    return texto, segmentos


# ---------------------------------------------------------------------------
# Método 2: transcripción desde los subtítulos de YouTube
# ---------------------------------------------------------------------------

def transcribir_con_subtitulos(video_id: str, idioma: str | None):
    """Obtiene la transcripción de los subtítulos de YouTube.

    Devuelve una tupla (texto, segmentos) con marcas de tiempo.
    """
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
    segmentos = [
        {"inicio": f.get("start", 0.0),
         "fin": f.get("start", 0.0) + f.get("duration", 0.0),
         "texto": f["text"].strip()}
        for f in datos
    ]
    texto = re.sub(r"\s+", " ", " ".join(s["texto"] for s in segmentos)).strip()
    return texto, segmentos


# ---------------------------------------------------------------------------
# Llamadas a Claude (resumen y traducción)
# ---------------------------------------------------------------------------

def _llamar_claude(prompt: str, max_tokens: int) -> str:
    """Envía un prompt a Claude y devuelve el texto, con errores claros."""
    try:
        import anthropic
    except ImportError:
        raise RuntimeError(
            "Falta la librería 'anthropic'. Instálala con: pip install anthropic"
        )

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Falta la clave de Anthropic. Crea un archivo .env con "
            "ANTHROPIC_API_KEY=tu-clave (ver .env.example)."
        )

    client = anthropic.Anthropic(api_key=api_key)

    try:
        with client.messages.stream(
            model=MODELO_CLAUDE,
            max_tokens=max_tokens,
            thinking={"type": "adaptive"},
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            mensaje = stream.get_final_message()
    except anthropic.AuthenticationError:
        raise RuntimeError(
            "La clave de Anthropic no es válida. Revisa el archivo .env: la clave "
            "debe empezar por 'sk-ant-', sin comillas ni espacios. Consíguela en "
            "https://console.anthropic.com/keys"
        )
    except anthropic.APIStatusError as e:
        raise RuntimeError(f"Error de la API de Anthropic ({e.status_code}): {e.message}")
    except anthropic.APIError as e:
        raise RuntimeError(f"Error al llamar a la API de Anthropic: {e}")

    partes = [bloque.text for bloque in mensaje.content if bloque.type == "text"]
    return "\n".join(partes).strip()


def generar_resumen(texto: str) -> str:
    """Genera un breve resumen con los puntos más importantes usando Claude."""
    prompt = (
        "A continuación tienes la transcripción completa de un vídeo. Redacta un "
        "resumen breve y claro, en el mismo idioma que la transcripción, que "
        "recoja las ideas y los puntos más importantes. Empieza con un párrafo "
        "de resumen general y después incluye una lista con los puntos clave.\n\n"
        f"Transcripción:\n{texto}"
    )
    return _llamar_claude(prompt, max_tokens=1500)


# Nombres legibles de idioma para el prompt de traducción.
NOMBRES_IDIOMA = {
    "es": "español", "en": "inglés", "fr": "francés", "de": "alemán",
    "it": "italiano", "pt": "portugués", "ca": "catalán", "gl": "gallego",
    "eu": "euskera", "zh": "chino", "ja": "japonés", "ru": "ruso",
    "ar": "árabe",
}


def _trocear(texto: str, maximo: int = 4500) -> list:
    """Parte el texto en trozos de como mucho 'maximo' caracteres, respetando
    los límites de frase siempre que se pueda (para el traductor gratuito)."""
    if len(texto) <= maximo:
        return [texto]
    trozos = []
    actual = ""
    for frase in re.split(r"(?<=[\.\?\!])\s+", texto):
        if len(actual) + len(frase) + 1 > maximo:
            if actual:
                trozos.append(actual.strip())
            # Si una sola frase supera el máximo, córtala a lo bruto.
            while len(frase) > maximo:
                trozos.append(frase[:maximo])
                frase = frase[maximo:]
            actual = frase
        else:
            actual = (actual + " " + frase).strip()
    if actual:
        trozos.append(actual.strip())
    return trozos


def traducir_gratis(texto: str, idioma_destino: str) -> str:
    """Traduce el texto usando el traductor de Google (deep-translator), gratis
    y sin necesidad de clave de API."""
    try:
        from deep_translator import GoogleTranslator
    except ImportError:
        raise RuntimeError(
            "Falta la librería 'deep-translator'. Instálala con: "
            "pip install deep-translator"
        )

    try:
        traductor = GoogleTranslator(source="auto", target=idioma_destino)
        partes = [traductor.translate(t) for t in _trocear(texto) if t.strip()]
    except Exception as e:
        raise RuntimeError(f"No se ha podido traducir: {e}")

    return " ".join(p for p in partes if p).strip()


def traducir_claude(texto: str, idioma_destino: str) -> str:
    """Traduce la transcripción al idioma indicado usando Claude (más preciso,
    requiere ANTHROPIC_API_KEY)."""
    nombre = NOMBRES_IDIOMA.get(idioma_destino, idioma_destino)
    prompt = (
        f"Traduce el siguiente texto al {nombre}. Devuelve únicamente la "
        "traducción, sin comentarios ni notas, respetando el sentido y el tono "
        "original. Si el texto ya está en ese idioma, devuélvelo tal cual.\n\n"
        f"Texto:\n{texto}"
    )
    return _llamar_claude(prompt, max_tokens=8000)


def traducir(texto: str, idioma_destino: str, motor: str = "gratis") -> str:
    """Traduce el texto. motor='gratis' usa Google (sin clave); motor='claude'
    usa Claude (más preciso, requiere clave)."""
    if motor == "claude":
        return traducir_claude(texto, idioma_destino)
    return traducir_gratis(texto, idioma_destino)


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


# ---------------------------------------------------------------------------
# Descarga de vídeo en máxima calidad y capítulos
# ---------------------------------------------------------------------------

def descargar_video(url: str, carpeta: str, altura_max: int | None = None):
    """Descarga el vídeo con la mejor calidad disponible (vídeo+audio unidos con
    ffmpeg) y devuelve (ruta_archivo, titulo).

    altura_max limita la resolución (p. ej. 1080). Si es None, usa la máxima.
    """
    try:
        import yt_dlp
    except ImportError:
        raise RuntimeError(
            "Falta la librería 'yt-dlp'. Instálala con: pip install yt-dlp"
        )

    if altura_max:
        formato = (
            f"bestvideo[height<={altura_max}]+bestaudio/"
            f"best[height<={altura_max}]/best"
        )
    else:
        formato = "bestvideo+bestaudio/best"

    plantilla = os.path.join(carpeta, "%(title).150B.%(ext)s")
    opciones = {
        "format": formato,
        "outtmpl": plantilla,
        "merge_output_format": "mp4",
        "quiet": True,
        "no_warnings": True,
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        },
        "socket_timeout": 30,
        "retries": 3,
    }
    _aplicar_cookies_proxy(opciones, carpeta)

    try:
        with yt_dlp.YoutubeDL(opciones) as ydl:
            info = ydl.extract_info(url, download=True)
            ruta = ydl.prepare_filename(info)
    except Exception as e:
        raise RuntimeError(f"No se ha podido descargar el vídeo: {e}")

    # Tras unir, la extensión suele ser .mp4; si no existe, busca el archivo real.
    base, _ = os.path.splitext(ruta)
    ruta_mp4 = base + ".mp4"
    if os.path.exists(ruta_mp4):
        ruta = ruta_mp4
    elif not os.path.exists(ruta):
        ficheros = [f for f in os.listdir(carpeta)]
        if ficheros:
            ruta = os.path.join(carpeta, ficheros[0])
        else:
            raise RuntimeError("No se ha encontrado el vídeo descargado.")

    titulo = info.get("title") or "video"
    return ruta, titulo


def obtener_capitulos(url: str):
    """Devuelve (capitulos, titulo) de un vídeo de YouTube. Cada capítulo es
    {'inicio': segundos, 'titulo': str}. Son los capítulos que pone el autor
    del vídeo. Devuelve lista vacía si el vídeo no tiene capítulos."""
    try:
        import yt_dlp
    except ImportError:
        raise RuntimeError(
            "Falta la librería 'yt-dlp'. Instálala con: pip install yt-dlp"
        )

    opciones = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        },
    }
    _aplicar_cookies_proxy(opciones, None)

    try:
        with yt_dlp.YoutubeDL(opciones) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as e:
        raise RuntimeError(f"No se ha podido obtener la información del vídeo: {e}")

    capitulos = [
        {"inicio": c.get("start_time", 0.0), "titulo": c.get("title", "").strip()}
        for c in (info.get("chapters") or [])
    ]
    return capitulos, (info.get("title") or "video")


def capitulos_texto(capitulos: list) -> str:
    """Formatea los capítulos como líneas '[min:seg] Título'."""
    return "\n".join(
        f"[{formato_tiempo(c['inicio'])}] {c['titulo']}"
        for c in capitulos if c.get("titulo") is not None
    )


# ---------------------------------------------------------------------------
# Marcas de tiempo y análisis de temas (para sacar clips)
# ---------------------------------------------------------------------------

def formato_tiempo(segundos: float) -> str:
    """Convierte segundos a formato mm:ss o hh:mm:ss."""
    segundos = int(segundos)
    horas, resto = divmod(segundos, 3600)
    minutos, seg = divmod(resto, 60)
    if horas:
        return f"{horas}:{minutos:02d}:{seg:02d}"
    return f"{minutos}:{seg:02d}"


def transcripcion_con_marcas(segmentos: list) -> str:
    """Devuelve la transcripción con una marca de tiempo delante de cada
    fragmento, p. ej.  [1:23] texto..."""
    lineas = [
        f"[{formato_tiempo(s['inicio'])}] {s['texto']}"
        for s in segmentos if s.get("texto")
    ]
    return "\n".join(lineas)


def analizar_temas(segmentos: list) -> str:
    """Analiza los temas del vídeo y en qué minuto empieza cada uno, usando
    Claude. Pensado para localizar clips. Requiere ANTHROPIC_API_KEY."""
    if not segmentos:
        raise RuntimeError("No hay marcas de tiempo para analizar los temas.")

    marcas = transcripcion_con_marcas(segmentos)
    prompt = (
        "Eres un editor de vídeo que busca clips. A continuación tienes la "
        "transcripción de un vídeo con marcas de tiempo [min:seg] al principio "
        "de cada fragmento. Identifica los distintos temas o momentos "
        "interesantes que se tratan. Para cada uno, indica:\n"
        "- La marca de tiempo de inicio (usa las marcas del texto)\n"
        "- Un título corto del tema\n"
        "- Una frase describiendo de qué trata y por qué puede ser un buen clip\n\n"
        "Devuelve una lista ordenada por tiempo, en el mismo idioma de la "
        "transcripción. Formato de cada línea:  [min:seg] Título — descripción.\n\n"
        f"Transcripción:\n{marcas}"
    )
    return _llamar_claude(prompt, max_tokens=4000)
