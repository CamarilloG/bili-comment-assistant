@echo off
chcp 65001 >nul
title 打包 Bilibili Bot 启动器

echo ============================================
echo   打包 Bilibili Bot GUI 启动器
echo ============================================
echo.

REM 检查 PyInstaller
python -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] 未安装 PyInstaller
    echo 正在安装 PyInstaller...
    python -m pip install pyinstaller
    if errorlevel 1 (
        echo [ERROR] PyInstaller 安装失败
        pause
        exit /b 1
    )
)

REM 清理旧的构建文件
if exist "build" rmdir /s /q build
if exist "dist\BiliBotLauncher.exe" del /f /q "dist\BiliBotLauncher.exe"

echo [*] 正在打包启动器...
echo.

REM 使用 launcher.spec 打包
python -m PyInstaller launcher.spec

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
echo 可执行文件位置: dist\BiliBotLauncher.exe
echo.
echo 使用说明:
echo 1. 将 BiliBotLauncher.exe 复制到项目根目录
echo 2. 确保 python 文件夹和 app 文件夹在同一目录
echo 3. 双击 BiliBotLauncher.exe 启动
echo.

pause
