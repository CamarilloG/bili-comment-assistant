@echo off
chcp 65001 >nul
title 安装依赖库

echo ========================================
echo Bilibili Bot v3.10 - 安装依赖库
echo ========================================
echo.

REM 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到 Python
    pause
    exit /b 1
)

echo Python 版本:
python --version
echo.

echo 正在安装依赖库...
echo.

python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo.
echo ========================================
echo 安装完成！
echo ========================================
echo.

pause
