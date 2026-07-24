#!/usr/bin/env python3
"""
Transcriptor de vídeos de YouTube (línea de comandos).

Uso:
    python transcriptor.py "https://www.youtube.com/watch?v=VIDEO_ID"
    python transcriptor.py "URL" --metodo subtitulos
    python transcriptor.py "URL" --idioma en
    python transcriptor.py "URL" --modelo small
    python transcriptor.py "URL" --resumen --guardar transcripcion.txt

La lógica está en core.py; este archivo solo es la interfaz de línea de comandos.
Para la interfaz web, ejecuta: python app.py
"""

import argparse
import sys

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import core


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Transcribe vídeos de YouTube a partir de su enlace."
    )
    parser.add_argument("url", help="Enlace del vídeo de YouTube (o su ID).")
    parser.add_argument(
        "--metodo",
        choices=["audio", "subtitulos"],
        default="audio",
        help="Método de transcripción: 'audio' (Whisper, por defecto y más "
        "preciso) o 'subtitulos' (más rápido).",
    )
    parser.add_argument(
        "--idioma",
        metavar="COD",
        help="Código del idioma (p. ej. es, en, fr, de). Si se omite, se "
        "detecta automáticamente.",
    )
    parser.add_argument(
        "--modelo",
        choices=core.MODELOS_WHISPER,
        default="base",
        help="Tamaño del modelo de Whisper (solo para --metodo audio). Por "
        "defecto: base.",
    )
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
        transcripcion = core.transcribir(
            args.url, metodo=args.metodo, idioma=args.idioma, modelo=args.modelo
        )
    except (ValueError, RuntimeError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    salida = ["=== TRANSCRIPCIÓN ===", "", transcripcion]

    if args.resumen:
        print("Generando el resumen con Claude...", file=sys.stderr)
        try:
            resumen = core.generar_resumen(transcripcion)
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
