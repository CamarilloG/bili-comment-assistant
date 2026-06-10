@echo off
chcp 65001 >nul
title 打包 Bilibili Bot 启动器

echo ============================================
echo   打包 Bilibili Bot GUI 启动器
echo ============================================
echo.

REM 优先使用项目内嵌 Python，回退到系统 Python
if exist "%~dp0python\python.exe" (
    set PYTHON=%~dp0python\python.exe
) else (
    set PYTHON=python
)

REM 检查 PyInstaller
%PYTHON% -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] 未安装 PyInstaller
    echo 正在安装 PyInstaller...
    %PYTHON% -m pip install pyinstaller
    if errorlevel 1 (
        echo [ERROR] PyInstaller 安装失败
        pause
        exit /b 1
    )
)

REM 清理旧的构建文件
if exist "build" rmdir /s /q build
if exist "dist\BiliBotLauncher_v3.11.exe" del /f /q "dist\BiliBotLauncher_v3.11.exe"

echo [*] 正在打包启动器...
echo.

REM 使用 launcher.spec 打包
%PYTHON% -m PyInstaller launcher.spec

if errorlevel 1 (
    echo.
    echo [ERROR] 打包失败
    pause
    exit /b 1
)

echo.
echo ============================================
echo   打包完成！
echo ============================================
echo.
echo 可执行文件位置: dist\BiliBotLauncher_v3.11.exe
echo.
echo 使用说明:
echo 1. 将 BiliBotLauncher_v3.11.exe 复制到项目根目录
echo 2. 确保 python 文件夹和 app 文件夹在同一目录
echo 3. 双击 BiliBotLauncher_v3.11.exe 启动
echo.

pause
