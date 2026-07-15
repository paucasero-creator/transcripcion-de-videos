@echo off
REM Arranca el transcriptor en tu ordenador (Windows).
REM La primera vez instala lo necesario; luego solo arranca la web.

echo ============================================
echo   Transcriptor de YouTube - arranque local
echo ============================================
echo.

REM Comprobar que Python esta instalado.
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] No se ha encontrado Python.
    echo Instalalo desde https://www.python.org/downloads/
    echo Recuerda marcar "Add Python to PATH" durante la instalacion.
    pause
    exit /b 1
)

REM Crear entorno virtual la primera vez.
if not exist ".venv" (
    echo Creando entorno virtual...
    python -m venv .venv
)

REM Activar entorno e instalar dependencias.
call .venv\Scripts\activate.bat
echo Instalando dependencias (solo la primera vez tarda)...
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

echo.
echo ============================================
echo   Abriendo http://localhost:5000 en tu navegador
echo   (Para parar el servidor: cierra esta ventana)
echo ============================================
echo.

REM Abrir el navegador y arrancar el servidor.
start http://localhost:5000
python app.py
