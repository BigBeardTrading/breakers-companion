@echo off
setlocal ENABLEDELAYEDEXPANSION

REM --- Always run from this .bat's folder ---
set "BASEDIR=%~dp0"
cd /d "%~dp0"

REM --- Logs folder ---
if not exist "logs" mkdir "logs"

REM --- If a venv exists but isn't 3.12, rebuild it ---
set "VPY=.venv\Scripts\python.exe"
if exist "%VPY%" (
  for /f "tokens=2" %%v in ('"%VPY%" -V') do set "CURPY=%%v"
  echo Found venv Python %CURPY%
  echo %CURPY% | findstr /b "3.12" >nul
  if errorlevel 1 (
    echo Recreating venv with Python 3.12...
    rmdir /s /q ".venv"
  )
)

REM --- Ensure venv exists (prefer a real Python312 if py -3.12 is absent) ---
if not exist ".venv" (
  echo Creating virtual environment with Python 3.12...
  if exist "%LocalAppData%\Programs\Python\Python312\python.exe" (
    "%LocalAppData%\Programs\Python\Python312\python.exe" -m venv ".venv" >>"logs\venv.log" 2>&1
  ) else (
    py -3.12 -m venv ".venv" >>"logs\venv.log" 2>&1
  )
  if errorlevel 1 (
    echo ^> Failed to create venv. Open logs\venv.log for details.
    notepad "logs\venv.log"
    pause
    exit /b 1
  )
)

set "VPY=.venv\Scripts\python.exe"
if not exist "%VPY%" (
  echo ^> venv Python missing. Something is off with the venv.
  pause
  exit /b 1
)

echo Using "%VPY%"
"%VPY%" -V

REM --- Requirements (safe pins) ---
if not exist "requirements.txt" (
  >"requirements.txt" echo PySide6==6.9.3
  >>"requirements.txt" echo pandas==2.2.2
  >>"requirements.txt" echo openpyxl==3.1.2
)

echo Upgrading pip...
"%VPY%" -m pip install --upgrade pip wheel >"logs\pip-upgrade.log" 2>&1

echo Installing dependencies (binary wheels only)...
"%VPY%" -m pip install --only-binary=:all: -r requirements.txt >"logs\pip-install.log" 2>&1
if errorlevel 1 (
  echo Primary install failed; trying fallback set...
  "%VPY%" -m pip install --only-binary=:all: PySide6==6.8.0.2 pandas==2.2.3 openpyxl==3.1.5 >>"logs\pip-install.log" 2>&1
  if errorlevel 1 (
    echo ^> Pip install failed. Opening logs\pip-install.log ...
    notepad "logs\pip-install.log"
    pause
    exit /b 1
  )
)

echo Launching The Breakers Companion...
"%VPY%" app.py >"logs\run.log" 2>&1
if errorlevel 1 (
  echo ^> The app exited with an error. Opening logs\run.log ...
  notepad "logs\run.log"
  pause
  exit /b 1
)
