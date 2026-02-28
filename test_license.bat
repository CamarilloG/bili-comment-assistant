@echo off
chcp 65001 >nul
cd app
..\python\python.exe run_web.py
pause
