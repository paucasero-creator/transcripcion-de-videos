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

from flask import Flask, jsonify, render_template, request

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

    if not url:
        return jsonify({"error": "Introduce un enlace de YouTube."}), 400

    try:
        transcripcion = core.transcribir(
            url, metodo=metodo, idioma=idioma, modelo=modelo
        )
    except (ValueError, RuntimeError) as e:
        return jsonify({"error": str(e)}), 400

    respuesta = {"transcripcion": transcripcion}

    if resumen:
        try:
            respuesta["resumen"] = core.generar_resumen(transcripcion)
        except RuntimeError as e:
            respuesta["aviso_resumen"] = str(e)

    return jsonify(respuesta)


if __name__ == "__main__":
    puerto = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=puerto, debug=False)
