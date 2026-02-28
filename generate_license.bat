@echo off
chcp 65001 >nul
title License 生成工具

echo ============================================
echo   B站评论助手 - License 生成工具
echo ============================================
echo.

:menu
echo 请选择操作:
echo   1. 生成密钥对
echo   2. 生成永久授权 License
echo   3. 生成时间限制 License
echo   4. 退出
echo.
set /p choice=请输入选项 (1-4):

if "%choice%"=="1" goto keygen
if "%choice%"=="2" goto generate_permanent
if "%choice%"=="3" goto generate_trial
if "%choice%"=="4" goto end
echo 无效选项，请重新选择
echo.
goto menu

:keygen
echo.
echo [生成密钥对]
echo.
python tools\license_generator.py keygen -o keys
echo.
pause
goto menu

:generate_permanent
echo.
echo [生成永久授权 License]
echo.
set /p user=请输入用户标识 (邮箱或昵称):
set /p type=请输入授权类型 (默认: 标准版):
if "%type%"=="" set type=标准版
set /p notes=请输入备注信息 (可选):
set /p output=请输入输出文件名 (默认: license.lic):
if "%output%"=="" set output=license.lic

echo.
echo 正在生成...
python tools\license_generator.py generate -k keys\private_key.pem -u "%user%" -t "%type%" -n "%notes%" -o "%output%"
echo.
pause
goto menu

:generate_trial
echo.
echo [生成时间限制 License]
echo.
set /p user=请输入用户标识 (邮箱或昵称):
set /p days=请输入有效天数:
set /p type=请输入授权类型 (默认: 试用版):
if "%type%"=="" set type=试用版
set /p notes=请输入备注信息 (可选):
set /p output=请输入输出文件名 (默认: license_trial.lic):
if "%output%"=="" set output=license_trial.lic

echo.
echo 正在生成...
python tools\license_generator.py generate -k keys\private_key.pem -u "%user%" -t "%type%" -d %days% -n "%notes%" -o "%output%"
echo.
pause
goto menu

:end
echo.
echo 感谢使用！
timeout /t 2 >nul
