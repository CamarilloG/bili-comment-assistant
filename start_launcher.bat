@echo off
chcp 65001 >nul
title Bilibili Bot 启动器

set PYTHON_EXE=%~dp0python\python.exe
set APP_DIR=%~dp0app

if not exist "%PYTHON_EXE%" (
    echo [ERROR] 找不到 Python 可执行文件: %PYTHON_EXE%
    echo 请检查安装目录
    pause
    exit /b 1
)

cd /d "%APP_DIR%"

echo ============================================
echo   Bilibili Bot 统一启动器
echo ============================================
echo.
echo [*] 正在启动 GUI 启动器...
echo.

"%PYTHON_EXE%" launcher_gui.py
pause
