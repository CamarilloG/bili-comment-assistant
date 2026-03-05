@echo off
chcp 65001 >nul
title 打包 Bilibili Bot 启动器（调试版）

echo ============================================
echo   打包 Bilibili Bot GUI 启动器（调试版）
echo   带控制台窗口，便于调试
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
if exist "dist\BiliBotLauncher_v3.10_debug.exe" del /f /q "dist\BiliBotLauncher_v3.10_debug.exe"

echo [*] 正在打包调试版启动器...
echo.

REM 使用 launcher_debug.spec 打包
python -m PyInstaller launcher_debug.spec

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
echo 可执行文件位置: dist\BiliBotLauncher_v3.10_debug.exe
echo.
echo 调试版特性:
echo - 带控制台窗口，可以看到详细日志
echo - 便于排查问题和调试
echo - 文件体积与正式版相同
echo.
echo 使用说明:
echo 1. 将 BiliBotLauncher_v3.10_debug.exe 复制到项目根目录
echo 2. 确保 python 文件夹和 app 文件夹在同一目录
echo 3. 双击 BiliBotLauncher_v3.10_debug.exe 启动
echo 4. 控制台窗口会显示详细的运行日志
echo.

pause
