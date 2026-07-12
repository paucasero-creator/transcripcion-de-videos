# Transcriptor de vídeos de YouTube

Aplicación de línea de comandos que **transcribe vídeos de YouTube a partir de su
enlace** y, opcionalmente, genera un **breve resumen con los puntos más
importantes** usando la API de Claude (Anthropic).

## Métodos de transcripción

La aplicación tiene dos formas de transcribir:

- **`audio` (por defecto):** descarga el audio del vídeo con `yt-dlp` y lo
  transcribe con **Whisper** (OpenAI), un modelo que se ejecuta **en local**.
  Es más preciso, funciona **aunque el vídeo no tenga subtítulos** y **detecta y
  admite muchos idiomas** automáticamente.
- **`subtitulos`:** usa los subtítulos de YouTube. Es más rápido, pero a menudo
  de peor calidad y no siempre está disponible.

> Claude se usa únicamente para **resumir** el texto, no para transcribir el
> audio.

## Instalación

```bash
pip install -r requirements.txt
```

El método de audio (Whisper) necesita **ffmpeg** instalado en el sistema:

```bash
# Debian/Ubuntu
sudo apt install ffmpeg
# macOS (Homebrew)
brew install ffmpeg
```

Para poder generar resúmenes, define tu clave de la API de Anthropic:

```bash
export ANTHROPIC_API_KEY="tu-clave-aqui"
```

## Uso

Transcribir un vídeo (desde el audio, por defecto):

```bash
python transcriptor.py "https://www.youtube.com/watch?v=VIDEO_ID"
```

Usar los subtítulos de YouTube en vez del audio:

```bash
python transcriptor.py "URL" --metodo subtitulos
```

Forzar un idioma concreto (si no, se detecta solo):

```bash
python transcriptor.py "URL" --idioma en
```

Elegir el tamaño del modelo de Whisper (más grande = más preciso, más lento):

```bash
python transcriptor.py "URL" --modelo small
```

Transcribir, resumir y guardar en un archivo:

```bash
python transcriptor.py "URL" --resumen --guardar transcripcion.txt
```

## Idiomas

- Con el método **audio**, Whisper **detecta el idioma automáticamente** y admite
  decenas de idiomas. Puedes forzarlo con `--idioma` (p. ej. `es`, `en`, `fr`,
  `de`, `pt`, `it`...).
- Con el método **subtitulos**, se buscan por defecto subtítulos en español y,
  si no existen, en inglés o cualquier otro idioma disponible. También puedes
  indicar el idioma con `--idioma`.

## Tamaños del modelo de Whisper

| Modelo   | Velocidad | Precisión | Uso recomendado                 |
|----------|-----------|-----------|---------------------------------|
| `tiny`   | Muy alta  | Baja      | Pruebas rápidas                 |
| `base`   | Alta      | Media     | Por defecto, buen equilibrio    |
| `small`  | Media     | Buena     | Mejor calidad                   |
| `medium` | Baja      | Muy buena | Transcripciones exigentes       |
| `large`  | Muy baja  | Máxima    | Máxima calidad (requiere GPU)   |

## Requisitos

- Python 3.10 o superior
- `ffmpeg` (para el método de audio)
- Conexión a Internet
- Una clave de la API de Anthropic (solo para la opción de resumen)
