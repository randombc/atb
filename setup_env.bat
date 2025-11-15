@echo off
setlocal enabledelayedexpansion

REM ============================================================
REM   Virtual environment bootstrapper for new Git project
REM   Creates .venv if missing, installs dependencies, activates
REM ============================================================

set "SCRIPT_DIR=%~dp0"
set "VENV_DIR=%SCRIPT_DIR%.venv"
set "VENV_PY=%VENV_DIR%\Scripts\python.exe"
set "REQ_FILE=%SCRIPT_DIR%requirements.txt"

echo ------------------------------------------------------------
echo  Initializing Python virtual environment (.venv)
echo ------------------------------------------------------------

REM Check if .venv exists
if not exist "%VENV_PY%" (
    echo [INFO] .venv not found. Creating new virtual environment...
    python -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )

    echo [INFO] Upgrading pip...
    "%VENV_PY%" -m pip install --upgrade pip

    REM If requirements.txt exists — install dependencies
    if exist "%REQ_FILE%" (
        echo [INFO] Installing dependencies from requirements.txt...
        "%VENV_PY%" -m pip install -r "%REQ_FILE%"
    ) else (
        echo [WARN] No requirements.txt found — skipping dependency install.
    )
) else (
    echo [INFO] .venv detected — skipping creation.
)

echo [INFO] Activating virtual environment...
call "%VENV_DIR%\Scripts\activate.bat"

echo ------------------------------------------------------------
echo  Virtual environment is active. You can now run your project.
echo ------------------------------------------------------------
