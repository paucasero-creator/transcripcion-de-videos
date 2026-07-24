@echo off
REM Arranca el transcriptor en tu ordenador con un doble clic.
title Transcriptor de videos
cd /d "%~dp0"

echo ============================================
echo   Transcriptor de videos - arranque local
echo ============================================
echo.

REM --- Comprobar Python ---
python --version >nul 2>&1
if errorlevel 1 goto sin_python

REM --- Aviso si falta ffmpeg ---
ffmpeg -version >nul 2>&1
if errorlevel 1 echo [AVISO] No se encuentra ffmpeg. Para el audio, instala con: winget install ffmpeg
echo.

REM --- Crear entorno virtual la primera vez ---
if not exist ".venv\Scripts\activate.bat" (
    echo Creando entorno virtual la primera vez...
    python -m venv .venv
)

REM --- Activar entorno e instalar dependencias ---
call ".venv\Scripts\activate.bat"
echo Comprobando dependencias. La primera vez tarda unos minutos...
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements.txt

echo.
echo ============================================
echo   Iniciando. Se abrira el navegador solo.
echo   Para PARAR: cierra esta ventana.
echo ============================================
echo.

REM --- Abrir el navegador tras unos segundos ---
start "" cmd /c "timeout /t 4 >nul & start http://localhost:5000"

REM --- Arrancar el servidor ---
python app.py

echo.
echo El servidor se ha detenido.
pause
goto fin

:sin_python
echo [ERROR] No se ha encontrado Python.
echo Instalalo desde https://www.python.org/downloads/
echo IMPORTANTE: marca "Add Python to PATH" al instalar.
echo.
pause

:fin
