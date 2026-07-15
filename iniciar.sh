#!/usr/bin/env bash
# Arranca el transcriptor en tu ordenador (Mac / Linux).
# La primera vez instala lo necesario; luego solo arranca la web.

set -e
cd "$(dirname "$0")"

echo "============================================"
echo "  Transcriptor de YouTube - arranque local"
echo "============================================"
echo

# Comprobar que Python esta instalado.
if ! command -v python3 >/dev/null 2>&1; then
    echo "[ERROR] No se ha encontrado Python 3."
    echo "Instalalo desde https://www.python.org/downloads/ o con tu gestor de paquetes."
    exit 1
fi

# Comprobar ffmpeg (necesario para el audio).
if ! command -v ffmpeg >/dev/null 2>&1; then
    echo "[AVISO] No se ha encontrado ffmpeg (necesario para transcribir audio)."
    echo "  macOS:  brew install ffmpeg"
    echo "  Ubuntu: sudo apt install ffmpeg"
    echo
fi

# Crear entorno virtual la primera vez.
if [ ! -d ".venv" ]; then
    echo "Creando entorno virtual..."
    python3 -m venv .venv
fi

# Activar entorno e instalar dependencias.
source .venv/bin/activate
echo "Instalando dependencias (solo la primera vez tarda)..."
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

echo
echo "============================================"
echo "  Abriendo http://localhost:5000 en tu navegador"
echo "  (Para parar el servidor: pulsa Ctrl+C)"
echo "============================================"
echo

# Abrir el navegador (segun el sistema) y arrancar el servidor.
( sleep 2; (open http://localhost:5000 2>/dev/null || xdg-open http://localhost:5000 2>/dev/null) ) &
python app.py
