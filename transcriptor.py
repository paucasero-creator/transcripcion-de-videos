#!/usr/bin/env python3
"""
Transcriptor de vídeos de YouTube.

Extrae la transcripción completa de un vídeo de YouTube a partir de su enlace
y, opcionalmente, genera un breve resumen con los puntos más importantes
usando la API de Claude (Anthropic).

Uso:
    python transcriptor.py "https://www.youtube.com/watch?v=VIDEO_ID"
    python transcriptor.py "https://youtu.be/VIDEO_ID" --resumen
    python transcriptor.py "URL" --resumen --guardar transcripcion.txt

Requisitos:
    pip install -r requirements.txt

Para el resumen es necesario definir la variable de entorno ANTHROPIC_API_KEY.
"""

import argparse
import os
import re
import sys

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    NoTranscriptFound,
    TranscriptsDisabled,
    VideoUnavailable,
)

# Idiomas preferidos para la transcripción, en orden de prioridad.
IDIOMAS_PREFERIDOS = ["es", "es-ES", "es-419", "en"]

MODELO_CLAUDE = "claude-opus-4-8"


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

    # Si el usuario pasa directamente el ID de 11 caracteres.
    if re.fullmatch(r"[0-9A-Za-z_-]{11}", url):
        return url

    raise ValueError(f"No se ha podido extraer el ID del vídeo de: {url}")


def obtener_transcripcion(video_id: str) -> str:
    """Obtiene la transcripción completa del vídeo en el mejor idioma disponible."""
    try:
        lista = YouTubeTranscriptApi.list_transcripts(video_id)
    except TranscriptsDisabled:
        raise RuntimeError(
            "Este vídeo tiene las transcripciones/subtítulos desactivados."
        )
    except VideoUnavailable:
        raise RuntimeError("El vídeo no está disponible.")

    transcript = None

    # 1. Intentar con los idiomas preferidos (manuales o automáticos).
    try:
        transcript = lista.find_transcript(IDIOMAS_PREFERIDOS)
    except NoTranscriptFound:
        # 2. Coger cualquier transcripción disponible.
        for t in lista:
            transcript = t
            break

    if transcript is None:
        raise RuntimeError("No se ha encontrado ninguna transcripción para el vídeo.")

    datos = transcript.fetch()
    texto = " ".join(fragmento["text"].strip() for fragmento in datos)
    # Limpiar espacios y saltos de línea sobrantes.
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto


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
        "A continuación tienes la transcripción completa de un vídeo de YouTube. "
        "Redacta un resumen breve y claro en español que recoja las ideas y los "
        "puntos más importantes. Empieza con un párrafo de resumen general y "
        "después incluye una lista con los puntos clave.\n\n"
        f"Transcripción:\n{texto}"
    )

    with client.messages.stream(
        model=MODELO_CLAUDE,
        max_tokens=1500,
        thinking={"type": "adaptive"},
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        mensaje = stream.get_final_message()

    # Extraer solo el texto (ignorando bloques de pensamiento).
    partes = [
        bloque.text for bloque in mensaje.content if bloque.type == "text"
    ]
    return "\n".join(partes).strip()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Transcribe vídeos de YouTube a partir de su enlace."
    )
    parser.add_argument("url", help="Enlace del vídeo de YouTube (o su ID).")
    parser.add_argument(
        "--resumen",
        action="store_true",
        help="Genera además un breve resumen con lo más importante (usa Claude).",
    )
    parser.add_argument(
        "--guardar",
        metavar="ARCHIVO",
        help="Guarda la transcripción (y el resumen) en el archivo indicado.",
    )
    args = parser.parse_args()

    try:
        video_id = extraer_id_video(args.url)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    print(f"Obteniendo la transcripción del vídeo {video_id}...", file=sys.stderr)

    try:
        transcripcion = obtener_transcripcion(video_id)
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    salida = ["=== TRANSCRIPCIÓN ===", "", transcripcion]

    if args.resumen:
        print("Generando el resumen con Claude...", file=sys.stderr)
        try:
            resumen = generar_resumen(transcripcion)
            salida += ["", "=== RESUMEN ===", "", resumen]
        except RuntimeError as e:
            print(f"Aviso: no se ha podido generar el resumen: {e}", file=sys.stderr)

    texto_final = "\n".join(salida)
    print(texto_final)

    if args.guardar:
        with open(args.guardar, "w", encoding="utf-8") as f:
            f.write(texto_final + "\n")
        print(f"\nGuardado en: {args.guardar}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
