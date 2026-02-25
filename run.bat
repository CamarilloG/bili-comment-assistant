@echo off
chcp 65001 >nul
setlocal

REM 便携包根目录（本 bat 所在目录）
set "PACK_ROOT=%~dp0"
if "%PACK_ROOT:~-1%"=="\" set "PACK_ROOT=%PACK_ROOT:~0,-1%"

set "PYTHON_EXE=%PACK_ROOT%\python\python.exe"
set "APP_DIR=%PACK_ROOT%\app"

if not exist "%PYTHON_EXE%" (
    echo [ERROR] Python not found: %PYTHON_EXE%
    pause
    exit /b 1
)

cd /d "%APP_DIR%"
if errorlevel 1 (
    echo [ERROR] App dir not found: %APP_DIR%
    pause
    exit /b 1
)

echo Starting Web Panel at http://localhost:9527/panel/
start "" "http://localhost:9527/panel/"
"%PYTHON_EXE%" -c "from web.app import start_web_server; start_web_server(port=9527)"
pause
