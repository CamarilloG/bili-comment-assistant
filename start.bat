@echo off
chcp 65001 >nul
title B站评论助手 V2.2 (Web版)

set PYTHON_EXE=%~dp0python\python.exe
set APP_DIR=%~dp0app

if not exist "%PYTHON_EXE%" (
    echo [ERROR] 内置 Python 未找到: %PYTHON_EXE%
    echo 请确保解压完整。
    pause
    exit /b 1
)

cd /d "%APP_DIR%"

echo ============================================
echo   B站评论助手 V2.2 Web控制面板
echo ============================================
echo.
echo [*] 正在启动 Web 控制面板...
echo [*] 启动后请在浏览器访问: http://localhost:9527/panel/
echo.
"%PYTHON_EXE%" -m uvicorn web.app:app --host 0.0.0.0 --port 9527
pause
