@echo off
chcp 65001 >nul
title 打包 Bilibili Bot 启动器（调试版 v3.8）

echo ============================================
echo   打包 Bilibili Bot GUI 启动器（调试版）
echo   带控制台窗口，方便查看错误信息
echo   版本: v3.8
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
if exist "dist\BiliBotLauncher_v3.8_debug.exe" del /f /q "dist\BiliBotLauncher_v3.8_debug.exe"

echo [*] 正在打包启动器（调试版）...
echo.

REM 使用 launcher_debug.spec 打包
python -m PyInstaller launcher_debug.spec --clean

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
echo 可执行文件位置: dist\BiliBotLauncher_v3.8_debug.exe
echo.
echo 注意: 这是调试版本，带有控制台窗口
echo 可以看到详细的错误信息
echo 版本: v3.8
echo.

pause
