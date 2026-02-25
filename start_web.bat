@echo off
chcp 65001 >nul
setlocal

REM 脚本所在目录为项目根
set "ROOT=%~dp0"
set "PYTHON_EXE=%ROOT%python\python.exe"
set "APP_DIR=%ROOT%app"

REM 无便携 Python 时使用系统 Python（开发环境）
if not exist "%PYTHON_EXE%" (
    set "PYTHON_EXE=py"
    set "APP_DIR=%ROOT%"
    where py >nul 2>&1
    if errorlevel 1 (
        set "PYTHON_EXE=python"
        where python >nul 2>&1
    )
    if errorlevel 1 (
        echo [ERROR] Python not found. Install Python and add to PATH.
        pause
        exit /b 1
    )
    REM 开发模式：若当前目录没有 web，则用上级或 gjm，确保能 import web
    if not exist "%APP_DIR%web\" (
        if exist "%ROOT%..\web\" set "APP_DIR=%ROOT%.."
        else if exist "%ROOT%..\gjm\web\" set "APP_DIR=%ROOT%..\gjm"
    )
    echo [INFO] Dev mode, APP_DIR=%APP_DIR%
)

cd /d "%APP_DIR%"
if errorlevel 1 (
    echo [ERROR] App dir not found: %APP_DIR%
    pause
    exit /b 1
)

echo ============================================
echo   BiliBot Vue Web Panel
echo   http://127.0.0.1:9527/panel/
echo ============================================
echo.
echo Starting server... Browser will open in 3 seconds.
echo Press Ctrl+C to stop.
echo.

REM 约 3 秒后在默认浏览器打开 Vue 面板（后台执行，不阻塞）
start /b cmd /c "ping 127.0.0.1 -n 4 >nul && start http://127.0.0.1:9527/panel/"

"%PYTHON_EXE%" -c "from web.app import start_web_server; start_web_server(port=9527)"
pause
