@echo on
setlocal ENABLEEXTENSIONS ENABLEDELAYEDEXPANSION
title Breakers Companion - Build (core)

REM Always run relative to this script
pushd "%~dp0"

REM 0) Sanity: Python launcher present
WHERE py >NUL 2>&1 || (echo [ERROR] Python launcher "py" not found & pause & exit /b 1)
py -V

REM 1) Activate/create venv
call .venv\Scripts\activate.bat 2>NUL
IF %ERRORLEVEL% NEQ 0 (
  echo [INFO] Creating venv
  py -m venv .venv || (echo [ERROR] Failed to create venv & pause & exit /b 1)
  call .venv\Scripts\activate.bat || (echo [ERROR] Failed to activate venv & pause & exit /b 1)
)

REM 2) Deps
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller

REM 3) Version bump via PowerShell script file (robust)
if not exist build mkdir build
powershell -NoProfile -ExecutionPolicy Bypass -File ".\scripts\bump_version.ps1" -Path "Version" -Default "2.0.24-test.1" > build\version.txt
IF ERRORLEVEL 1 (echo [ERROR] Version bump failed & type build\version.txt & pause & popd & exit /b 1)
set /p VERSION=<build\version.txt
echo [INFO] Version %VERSION%

REM 4) Ensure folders exist
if not exist assets mkdir assets
if not exist data   mkdir data
if not exist sets   mkdir sets
if not exist "app.py" (echo [ERROR] Missing app.py & pause & popd & exit /b 1)

REM 5) Clean logs
del /q build\pyi-stdout.log 2>nul
del /q build\pyi-stderr.log 2>nul

REM 6) Build (prefer .spec; fallback to CLI). Log everything.
if exist "Breakers Companion.spec" (
  echo [INFO] Building from spec
  py -m PyInstaller --noconfirm --clean "Breakers Companion.spec" 1> build\pyi-stdout.log 2> build\pyi-stderr.log
) else (
  echo [INFO] Building with CLI flags
  py -m PyInstaller ^
    --noconfirm ^
    --name "Breakers Companion" ^
    --onefile ^
    --windowed ^
    --icon "assets\BBT_BreakersCompanion.ico" ^
    --add-data "Version;." ^
    --add-data "assets;assets" ^
    --add-data "data;data" ^
    --add-data "sets;sets" ^
    app.py 1> build\pyi-stdout.log 2> build\pyi-stderr.log
)

IF ERRORLEVEL 1 (
  echo.
  echo [ERROR] PyInstaller failed. Tail of stderr:
  powershell -NoProfile -Command "Get-Content -Tail 80 'build\pyi-stderr.log'"
  echo.
  echo [INFO] Logs: build\pyi-stdout.log  build\pyi-stderr.log
  pause
  popd
  exit /b 1
)

if not exist "dist\Breakers Companion.exe" (
  echo [ERROR] Build says OK but EXE missing. Check logs in build
  pause
  popd
  exit /b 1
)

echo.
echo [OK] Build finished: dist\Breakers Companion.exe

REM 7) Run EXE and wait so this window stays open until app closes
start "" /wait ".\dist\Breakers Companion.exe"

echo.
echo [DONE] App exited. Press any key to close this window.
pause
popd
