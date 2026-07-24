@echo off
REM Arranca el transcriptor en tu ordenador (Windows) con un doble clic.
REM La primera vez instala todo lo necesario; luego solo arranca la web.
title Transcriptor de videos
cd /d "%~dp0"

echo ============================================
echo   Transcriptor de videos - arranque local
echo ============================================
echo.

REM Comprobar que Python esta instalado.
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] No se ha encontrado Python.
    echo Instalalo desde https://www.python.org/downloads/
    echo Recuerda marcar "Add Python to PATH" durante la instalacion.
    echo.
    pause
    exit /b 1
)

REM Comprobar ffmpeg (necesario para el audio).
ffmpeg -version >nul 2>&1
if errorlevel 1 (
    echo [AVISO] No se ha encontrado ffmpeg (necesario para transcribir audio).
    echo Instalalo abriendo PowerShell y ejecutando:  winget install ffmpeg
    echo (luego cierra y vuelve a abrir esta ventana)
    echo.
)

REM Crear entorno virtual la primera vez.
if not exist ".venv" (
    echo Creando entorno virtual (solo la primera vez)...
    python -m venv .venv
)

REM Activar entorno e instalar dependencias.
call ".venv\Scripts\activate.bat"
echo Comprobando dependencias (la primera vez tarda unos minutos)...
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements.txt

echo.
echo ============================================
echo   Iniciando... se abrira el navegador solo.
echo   Para PARAR: cierra esta ventana.
echo ============================================
echo.

REM Abrir el navegador tras un pequeno margen para que el servidor arranque.
start "" cmd /c "timeout /t 4 >nul & start http://localhost:5000"

REM Arrancar el servidor (se queda corriendo aqui).
python app.py

echo.
echo El servidor se ha detenido.
pause
