@echo off
set PYTHON_EXE=C:\Users\qsqsq\python-sdk\python3.11.11\python.exe

echo Using Python: "%PYTHON_EXE%"

echo Installing dependencies...
"%PYTHON_EXE%" -m pip install -r requirements.txt
"%PYTHON_EXE%" -m pip install ttkbootstrap

echo Starting GUI...
"%PYTHON_EXE%" gui.py

pause
