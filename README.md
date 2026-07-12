# Transcriptor de vídeos de YouTube

Aplicación de línea de comandos que **transcribe vídeos de YouTube a partir de su
enlace** y, opcionalmente, genera un **breve resumen con los puntos más
importantes** usando la API de Claude (Anthropic).

## Cómo funciona

1. Le pasas un enlace de YouTube.
2. La aplicación descarga la transcripción completa del vídeo usando los
   subtítulos de YouTube (`youtube-transcript-api`).
3. Si lo pides con `--resumen`, envía la transcripción a Claude para obtener un
   resumen con lo más importante.

> **Nota:** la transcripción se obtiene de los subtítulos de YouTube (manuales o
> automáticos). Si un vídeo tiene los subtítulos desactivados, no se podrá
> transcribir con este método. Claude se usa únicamente para resumir el texto,
> no para transcribir el audio.

## Instalación

```bash
pip install -r requirements.txt
```

Para poder generar resúmenes, define tu clave de la API de Anthropic:

```bash
export ANTHROPIC_API_KEY="tu-clave-aqui"
```

## Uso

Transcribir un vídeo:

```bash
python transcriptor.py "https://www.youtube.com/watch?v=VIDEO_ID"
```

Transcribir y generar un resumen:

```bash
python transcriptor.py "https://youtu.be/VIDEO_ID" --resumen
```

Guardar el resultado en un archivo:

```bash
python transcriptor.py "URL" --resumen --guardar transcripcion.txt
```

## Idiomas

Por defecto se buscan subtítulos en español (`es`) y, si no existen, en inglés
(`en`) o cualquier otro idioma disponible. Puedes ajustar el orden en la lista
`IDIOMAS_PREFERIDOS` dentro de `transcriptor.py`.

## Requisitos

- Python 3.8 o superior
- Conexión a Internet
- Una clave de la API de Anthropic (solo para la opción de resumen)
