@echo off
chcp 65001 >nul
title 任务启动诊断

echo ========================================
echo 任务启动诊断工具
echo ========================================
echo.

echo [步骤 1] 测试浏览器启动
echo.
python test_browser_launch.py
if errorlevel 1 (
    echo.
    echo 浏览器启动测试失败，请先解决浏览器问题
    pause
    exit /b 1
)

echo.
echo ========================================
echo.

echo [步骤 2] 启动服务（如果未启动）
echo.
echo 请确保服务正在运行
echo 如果未启动，请在另一个终端运行: start_test.bat
echo.
pause

echo.
echo ========================================
echo.

echo [步骤 3] 测试任务启动 API
echo.
python test_task_start.py

echo.
echo ========================================
echo.

echo [步骤 4] 查看日志
echo.
echo 正在打开日志文件...
echo.

if exist "用户数据\logs\bili_bot_2026-03-04.log" (
    notepad "用户数据\logs\bili_bot_2026-03-04.log"
) else (
    echo 日志文件不存在
)

pause
