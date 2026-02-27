@echo off
chcp 65001 >nul
setlocal

set BASE_DIR=%~dp0
set PYTHON_EXE=%BASE_DIR%python\python.exe

title B站评论助手 Web 单文件打包

if not exist "%PYTHON_EXE%" (
    echo [ERROR] 内置 Python 未找到: "%PYTHON_EXE%"
    echo 请确认已完整解压项目后再重试。
    pause
    exit /b 1
)

cd /d "%BASE_DIR%"

echo ============================================
echo   B站评论助手 Web 单文件打包
echo ============================================
echo.

rem 检查或安装 PyInstaller
"%PYTHON_EXE%" -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
    echo [INFO] 未检测到 PyInstaller，正在尝试安装...
    "%PYTHON_EXE%" -m pip install --upgrade pip pyinstaller
    if errorlevel 1 (
        echo.
        echo [ERROR] 自动安装 PyInstaller 失败。
        echo 请手动执行以下命令后重试：
        echo.
        echo   "%PYTHON_EXE%" -m pip install pyinstaller
        echo.
        pause
        exit /b 1
    )
)

echo.
echo [*] 使用 run_web.spec 开始打包 Web 单文件 exe ...
echo.

"%PYTHON_EXE%" -m PyInstaller run_web.spec
if errorlevel 1 (
    echo.
    echo [ERROR] 打包失败，请根据上方错误信息排查后重试。
    pause
    exit /b 1
)

echo.
echo [OK] 打包完成。
echo 输出文件：
echo   "%BASE_DIR%dist\B站评论助手_Web_V3.exe"
echo.
echo 双击该 exe 即可启动 Web 控制面板，浏览器会自动打开 http://localhost:9527/panel/
echo.
pause

