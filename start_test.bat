@echo off
chcp 65001 >nul
title Bilibili Bot v3.10 - 本地测试启动

echo ========================================
echo Bilibili Bot v3.10 本地测试启动
echo ========================================
echo.

REM 检查 Python 是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到 Python，请先安装 Python 3.11+
    pause
    exit /b 1
)

echo Python 版本:
python --version
echo.

REM 启动开发服务（自动安装依赖）
python start_dev.py

pause
