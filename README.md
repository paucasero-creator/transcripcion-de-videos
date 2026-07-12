# Transcriptor de vídeos de YouTube

Transcribe vídeos de YouTube a partir de su enlace y, opcionalmente, genera un
breve resumen con los puntos más importantes usando la API de Claude.

Se puede usar de tres formas:

- **Página HTML (100% en el navegador)** (`docs/index.html`): sin servidor y
  gratis. Subes o arrastras un archivo de audio/vídeo y se transcribe en tu
  propio dispositivo con Whisper (vía `transformers.js`). Se puede publicar en
  **GitHub Pages**. Limitación: **no** puede descargar el audio de un enlace de
  YouTube (el navegador no puede por CORS); para eso hace falta el servidor.
- **Interfaz web con servidor** (`app.py`): una pequeña plataforma Flask donde sí
  puedes **pegar el enlace de YouTube** y transcribirlo. Necesita un servidor.
- **Línea de comandos** (`transcriptor.py`): para usarla desde la terminal.

### ¿Qué versión elijo?

| | HTML (GitHub Pages) | Servidor (`app.py`) |
|---|---|---|
| Pegar enlace de YouTube | ❌ | ✅ |
| Subir/arrastrar un archivo | ✅ | ✅ |
| Coste | Gratis, sin servidor | Necesita hosting |
| Resumen con Claude | ❌ (expondría la clave) | ✅ |

## Página HTML en el navegador (GitHub Pages)

El archivo `docs/index.html` es autónomo. Para publicarlo gratis:

1. En GitHub: **Settings → Pages**.
2. En *Source*, elige la rama y la carpeta **/docs**.
3. Guarda. En un minuto tendrás una URL pública que funciona en móvil y ordenador.

También puedes abrirlo en local con cualquier servidor estático, por ejemplo:

```bash
python -m http.server -d docs 8080   # y abre http://localhost:8080
```

## Métodos de transcripción

- **`audio` (por defecto):** descarga el audio con `yt-dlp` y lo transcribe con
  **Whisper** (OpenAI, en local). Más preciso, funciona **aunque el vídeo no
  tenga subtítulos** y **detecta y admite muchos idiomas** automáticamente.
- **`subtitulos`:** usa los subtítulos de YouTube. Más rápido, pero de peor
  calidad y no siempre disponible.

Claude se usa únicamente para **resumir**, no para transcribir el audio.

## Instalación

```bash
pip install -r requirements.txt
```

El método de audio (Whisper) necesita **ffmpeg**:

```bash
sudo apt install ffmpeg     # Debian/Ubuntu
brew install ffmpeg         # macOS
```

Para generar resúmenes, define tu clave de Anthropic:

```bash
export ANTHROPIC_API_KEY="tu-clave-aqui"
```

## Uso: interfaz web

```bash
python app.py
```

Abre **http://localhost:5000** en el navegador. Pega el enlace, elige el método
y el idioma, marca si quieres resumen y pulsa **Transcribir**.

## Uso: línea de comandos

```bash
python transcriptor.py "https://www.youtube.com/watch?v=VIDEO_ID"
python transcriptor.py "URL" --metodo subtitulos
python transcriptor.py "URL" --idioma en
python transcriptor.py "URL" --modelo small
python transcriptor.py "URL" --resumen --guardar transcripcion.txt
```

## Desplegar en un hosting (usarlo desde cualquier sitio)

El proyecto incluye un `Procfile` listo para plataformas tipo **Render**,
**Railway** o **Fly.io**:

1. Sube este repositorio a la plataforma que elijas.
2. Configura la variable de entorno `ANTHROPIC_API_KEY` (si quieres resúmenes).
3. Asegúrate de que la imagen/entorno tenga **ffmpeg** instalado. En Render, por
   ejemplo, se puede añadir con un `apt` en el build o usando un Dockerfile.
4. La plataforma usará el `Procfile`, que arranca la web con `gunicorn`.

> **Importante sobre recursos:** Whisper consume CPU y memoria. En los planes
> gratuitos puede ir lento o quedarse sin memoria con vídeos largos o modelos
> grandes. Recomendaciones:
> - Usa el modelo `base` o `small` en servidores modestos.
> - Para vídeos largos o mucho uso, conviene un plan con más RAM/CPU (o GPU).
> - Como alternativa ligera, el método `subtitulos` no necesita Whisper ni
>   ffmpeg y funciona en cualquier plan.

## Idiomas

Con **audio**, Whisper detecta el idioma solo y admite decenas de ellos; puedes
forzarlo (`es`, `en`, `fr`, `de`, `pt`, `it`, `ca`...). Con **subtitulos** se
busca español por defecto y, si no hay, inglés u otro disponible.

## Tamaños del modelo de Whisper

| Modelo   | Velocidad | Precisión | Uso recomendado              |
|----------|-----------|-----------|------------------------------|
| `tiny`   | Muy alta  | Baja      | Pruebas rápidas              |
| `base`   | Alta      | Media     | Por defecto, buen equilibrio |
| `small`  | Media     | Buena     | Mejor calidad                |
| `medium` | Baja      | Muy buena | Transcripciones exigentes    |
| `large`  | Muy baja  | Máxima    | Máxima calidad (requiere GPU)|

## Archivos del proyecto

- `core.py` — lógica de transcripción y resumen (compartida).
- `app.py` — servidor web Flask.
- `templates/index.html` — página web.
- `transcriptor.py` — interfaz de línea de comandos.
- `Procfile` — arranque para despliegue.

## Requisitos

- Python 3.10 o superior
- `ffmpeg` (para el método de audio)
- Una clave de la API de Anthropic (solo para resúmenes)
