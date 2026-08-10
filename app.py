#!/usr/bin/env python3
"""
Interfaz web del transcriptor de vídeos de YouTube.

Ejecuta un pequeño servidor web (Flask) con una página desde la que pegar el
enlace de un vídeo y obtener la transcripción y, opcionalmente, un resumen.

Uso local:
    pip install -r requirements.txt
    python app.py
    # Abre http://localhost:5000 en el navegador

Para desplegarlo en un hosting y usarlo desde cualquier sitio, mira el README.
"""

import os

# Carga automática de las variables de un archivo .env (p. ej. ANTHROPIC_API_KEY),
# para no tener que escribir la clave cada vez.
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import shutil
import tempfile

from flask import (
    Flask, after_this_request, jsonify, render_template, request, send_file,
)

import core

app = Flask(__name__)


@app.route("/")
def inicio():
    return render_template(
        "index.html",
        modelos=core.MODELOS_WHISPER,
        hay_api_key=bool(os.environ.get("ANTHROPIC_API_KEY")),
    )


@app.route("/api/transcribir", methods=["POST"])
def api_transcribir():
    datos = request.get_json(silent=True) or {}
    url = (datos.get("url") or "").strip()
    metodo = datos.get("metodo") or "audio"
    idioma = (datos.get("idioma") or "").strip() or None
    modelo = datos.get("modelo") or "base"
    resumen = bool(datos.get("resumen"))
    traducir_a = (datos.get("traducir_a") or "").strip() or None
    # motor de traducción: 'gratis' (Google, sin clave) o 'claude' (requiere clave)
    motor_traduccion = datos.get("motor_traduccion") or "gratis"
    analizar_temas = bool(datos.get("analizar_temas"))

    if not url:
        return jsonify({"error": "Introduce un enlace de vídeo."}), 400

    try:
        transcripcion, segmentos = core.transcribir(
            url, metodo=metodo, idioma=idioma, modelo=modelo
        )
    except (ValueError, RuntimeError) as e:
        return jsonify({"error": str(e)}), 400

    respuesta = {
        "transcripcion": transcripcion,
        "marcas": core.transcripcion_con_marcas(segmentos),
    }

    # Análisis de temas con marcas de tiempo (para clips). Usa Claude.
    if analizar_temas:
        try:
            respuesta["temas"] = core.analizar_temas(segmentos)
        except RuntimeError as e:
            respuesta["aviso_temas"] = str(e)

    # Traducción opcional al idioma elegido (texto sobre el que se resume).
    texto_base = transcripcion
    if traducir_a:
        try:
            respuesta["traduccion"] = core.traducir(
                transcripcion, traducir_a, motor=motor_traduccion
            )
            texto_base = respuesta["traduccion"]
        except RuntimeError as e:
            respuesta["aviso_traduccion"] = str(e)

    if resumen:
        try:
            respuesta["resumen"] = core.generar_resumen(texto_base)
        except RuntimeError as e:
            respuesta["aviso_resumen"] = str(e)

    return jsonify(respuesta)


@app.route("/api/capitulos", methods=["POST"])
def api_capitulos():
    """Devuelve los capítulos (timestamps del autor) de un vídeo de YouTube."""
    datos = request.get_json(silent=True) or {}
    url = (datos.get("url") or "").strip()
    if not url:
        return jsonify({"error": "Introduce un enlace de vídeo."}), 400
    try:
        capitulos, titulo = core.obtener_capitulos(url)
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 400
    return jsonify({
        "titulo": titulo,
        "capitulos": core.capitulos_texto(capitulos),
        "tiene_capitulos": bool(capitulos),
    })


@app.route("/api/descargar", methods=["POST"])
def api_descargar():
    """Descarga el vídeo en máxima calidad y lo envía al navegador."""
    datos = request.get_json(silent=True) or {}
    url = (datos.get("url") or "").strip()
    calidad = datos.get("calidad") or "max"
    if not url:
        return jsonify({"error": "Introduce un enlace de vídeo."}), 400

    altura_max = None if calidad == "max" else int(calidad)
    carpeta = tempfile.mkdtemp(prefix="descarga_")

    try:
        ruta, titulo = core.descargar_video(url, carpeta, altura_max=altura_max)
    except (ValueError, RuntimeError) as e:
        shutil.rmtree(carpeta, ignore_errors=True)
        return jsonify({"error": str(e)}), 400

    @after_this_request
    def limpiar(response):
        shutil.rmtree(carpeta, ignore_errors=True)
        return response

    nombre = os.path.basename(ruta)
    return send_file(ruta, as_attachment=True, download_name=nombre)


if __name__ == "__main__":
    puerto = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=puerto, debug=False)
