@echo off
chcp 65001 >nul
title B站评论助手 V2.2 启动器

REM Auto-detect: portable embedded Python or system Python
if exist "%~dp0python\python.exe" (
    set PYTHON_EXE=%~dp0python\python.exe
    echo [*] 检测到内置 Python
) else (
    set PYTHON_EXE=python
    echo [*] 使用系统 Python
)

echo ============================================
echo   B站评论助手 V2.2 启动器
echo ============================================
echo.
echo   [1] 启动 GUI 桌面版
echo   [2] 启动 Web 控制面板 (浏览器访问)
echo   [3] 同时启动 GUI + Web
echo   [4] 仅安装依赖 (开发用)
echo   [Q] 退出
echo.
set /p choice=请选择: 

if /i "%choice%"=="1" goto gui
if /i "%choice%"=="2" goto web
if /i "%choice%"=="3" goto both
if /i "%choice%"=="4" goto deps
if /i "%choice%"=="q" goto end
echo 无效选择，请重试。
pause
goto end

:deps
echo.
echo [*] 正在安装依赖...
"%PYTHON_EXE%" -m pip install -r requirements.txt -q
"%PYTHON_EXE%" -m playwright install chromium
echo [OK] 依赖安装完成。
pause
goto end

:gui
echo.
echo [*] 正在启动 GUI 桌面版...
"%PYTHON_EXE%" gui.py
pause
goto end

:web
echo.
echo [*] 正在启动 Web 控制面板...
echo [*] 启动后请在浏览器访问: http://localhost:9527/panel/
"%PYTHON_EXE%" -m uvicorn web.app:app --host 0.0.0.0 --port 9527
pause
goto end

:both
echo.
echo [*] 正在启动 Web 控制面板 (后台)...
start "Web Panel" cmd /c ""%PYTHON_EXE%" -m uvicorn web.app:app --host 0.0.0.0 --port 9527"
timeout /t 2 >nul
echo [*] Web 面板已在后台启动: http://localhost:9527/panel/
echo.
echo [*] 正在启动 GUI 桌面版...
"%PYTHON_EXE%" gui.py
pause
goto end

:end
