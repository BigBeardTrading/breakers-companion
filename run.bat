@echo off
setlocal ENABLEDELAYEDEXPANSION

REM --- Always run from this .bat's folder ---
cd /d "%~dp0"

REM --- Logs folder ---
if not exist "logs" mkdir "logs"

REM --- Desired Python major.minor for this project ---
set "PYREQ=3.11"

REM --- Paths we’ll use ---
set "VPY=.venv\Scripts\python.exe"

REM --- If a venv exists but isn't %PYREQ%, rebuild it ---
if exist "%VPY%" (
  for /f "tokens=2" %%v in ('"%VPY%" -V') do set "CURPY=%%v"
  echo Found venv Python %CURPY%
  echo %CURPY% | findstr /b "%PYREQ%" >nul
  if errorlevel 1 (
    echo Recreating venv with Python %PYREQ%...
    rmdir /s /q ".venv"
  )
)

REM --- Ensure venv exists (prefer a direct 3.11 if present, else use py -3.11) ---
if not exist ".venv" (
  echo Creating virtual environment with Python %PYREQ%...
  if exist "%LocalAppData%\Programs\Python\Python311\python.exe" (
    "%LocalAppData%\Programs\Python\Python311\python.exe" -m venv ".venv" >>"logs\venv.log" 2>&1
  ) else (
    py -3.11 -m venv ".venv" >>"logs\venv.log" 2>&1
  )
  if errorlevel 1 (
    echo ^> Failed to create venv. See logs\venv.log
    notepad "logs\venv.log"
    pause
    exit /b 1
  )
)

if not exist "%VPY%" (
  echo ^> venv python missing. Something is off with the venv.
  pause
  exit /b 1
)

echo Using "%VPY%"
"%VPY%" -V

REM --- Requirements (safe pins matching your current setup) ---
if not exist "requirements.txt" (
  >"requirements.txt" echo PySide6==6.9.3
  >>"requirements.txt" echo pandas==2.2.2
  >>"requirements.txt" echo openpyxl==3.1.2
  >>"requirements.txt" echo appdirs==1.4.4
)

echo Upgrading pip...
"%VPY%" -m pip install --upgrade pip wheel >"logs\pip-upgrade.log" 2>&1

echo Installing dependencies (binary wheels preferred)...
REM Try binary-only first for speed; if it fails, fall back to normal.
"%VPY%" -m pip install --only-binary=:all: -r requirements.txt >"logs\pip-install.log" 2>&1
if errorlevel 1 (
  echo Primary (binary-only) install failed; trying normal install...
  "%VPY%" -m pip install -r requirements.txt >>"logs\pip-install.log" 2>&1
  if errorlevel 1 (
    echo ^> Pip install failed. Opening logs\pip-install.log ...
    notepad "logs\pip-install.log"
    pause
    exit /b 1
  )
)

REM --- Ensure VERSION exists and shows 2.0.24 (non-fatal if you track it in git) ---
if not exist "VERSION" echo 2.0.24> VERSION

echo Launching Breakers Companion...
"%VPY%" app.py >"logs\run.log" 2>&1
if errorlevel 1 (
  echo ^> The app exited with an error. Opening logs\run.log ...
  notepad "logs\run.log"
  pause
  exit /b 1
)
