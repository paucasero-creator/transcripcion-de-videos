# Imagen para desplegar el transcriptor (servidor web) en Render u otro hosting.
FROM python:3.11-slim

# ffmpeg es necesario para el método de audio (Whisper / yt-dlp).
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Instalar dependencias primero (mejor aprovechamiento de la caché de Docker).
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto del proyecto.
COPY . .

# Precargar el modelo 'base' de Whisper en la imagen para que el primer arranque
# no tarde en descargarlo. Cámbialo o quítalo si prefieres otro tamaño.
RUN python -c "import whisper; whisper.load_model('base')"

# Render (y otros) inyectan el puerto en la variable PORT.
ENV PORT=10000
EXPOSE 10000

# Timeout alto porque transcribir vídeos largos puede tardar.
CMD ["sh", "-c", "gunicorn app:app --bind 0.0.0.0:${PORT} --timeout 600 --workers 1"]
