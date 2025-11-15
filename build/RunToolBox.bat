@echo off
REM Switch to the folder where the bat is located
cd /d "%~dp0..\"

REM Open a new console window and run Python from .venv
start "" ".\.venv\Scripts\python.exe" "src\main.py" %*

REM Optional: exit the current bat (new window runs independently)
exit
