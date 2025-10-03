@echo off
setlocal ENABLEDELAYEDEXPANSION
cd /d "%~dp0"

if not exist "logs" mkdir logs

REM --- read version from VERSION file (fallback 0.0.0)
set "APP_VER="
if exist "VERSION" (set /p APP_VER=<VERSION)
if "%APP_VER%"=="" set "APP_VER=0.0.0"

REM --- ensure venv and tools
if not exist ".venv\Scripts\python.exe" (
  py -3.12 -m venv .venv >"logs\venv.log" 2>&1 || (notepad logs\venv.log & exit /b 1)
)
set "VPY=.venv\Scripts\python.exe"
"%VPY%" -m pip install -U pip pyinstaller >"logs\pip-tools.log" 2>&1

REM --- choose seed (prefer data\ then sets\)
set "SEED=data\2025 Donruss Football Master Checklist.xlsx"
if not exist "%SEED%" if exist "sets\2025 Donruss Football Master Checklist.xlsx" set "SEED=sets\2025 Donruss Football Master Checklist.xlsx"
if exist "%SEED%" (set "SEEDADD=--add-data=""%SEED%;data""") else (set "SEEDADD=")

REM --- build with PyInstaller
echo Building app...
"%VPY%" -m PyInstaller --noconfirm --onedir --windowed ^
 --name "Breakers Companion" ^
 --icon "assets\BBT_BreakersCompanion.ico" ^
 --add-data="assets\bbt.png;assets" ^
 --add-data="assets\Background.png;assets" ^
 --add-data="assets\BBT_BreakersCompanion.ico;assets" ^
 --add-data="VERSION;." ^
 %SEEDADD% ^
 app.py >"logs\pyinstaller.log" 2>&1
if errorlevel 1 (echo [ERROR] PyInstaller failed & notepad logs\pyinstaller.log & exit /b 1)

set "APP_EXE=dist\Breakers Companion\Breakers Companion.exe"

REM --- sign EXE with your DEV cert (PowerShell, no SDK required)
powershell -NoProfile -ExecutionPolicy Bypass ^
 "$cert=Get-ChildItem Cert:\CurrentUser\My | ? { $_.Subject -like 'CN=Big Beard Trading (DEV)*' -and $_.EnhancedKeyUsageList -match 'Code Signing' } | sort NotAfter -desc | select -First 1; if($cert){ Set-AuthenticodeSignature -FilePath '%APP_EXE%' -Certificate $cert -TimestampServer 'http://timestamp.digicert.com' -HashAlgorithm SHA256 | Out-Host } else { 'No DEV cert; skipping EXE signing.' }"

REM --- find Inno Setup compiler
set "ISCC="
for %%A in ("%ProgramFiles%\Inno Setup 6\ISCC.exe" "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" "%LocalAppData%\Programs\Inno Setup 6\ISCC.exe") do if exist "%%~A" set "ISCC=%%~A"
if not defined ISCC (echo [ERROR] Inno Setup not found. Install it, then run again.& exit /b 1)

REM --- compile installer (version comes from VERSION file)
echo Compiling installer...
"%ISCC%" /DMyAppVersion=%APP_VER% "installer.iss" >"logs\inno.log" 2>&1
if errorlevel 1 (echo [ERROR] Inno compile failed & notepad logs\inno.log & exit /b 1)

set "SETUP_EXE=build\installer\BreakersCompanion-Setup-%APP_VER%.exe"

REM --- sign installer with DEV cert (optional)
powershell -NoProfile -ExecutionPolicy Bypass ^
 "$cert=Get-ChildItem Cert:\CurrentUser\My | ? { $_.Subject -like 'CN=Big Beard Trading (DEV)*' -and $_.EnhancedKeyUsageList -match 'Code Signing' } | sort NotAfter -desc | select -First 1; if($cert){ Set-AuthenticodeSignature -FilePath '%SETUP_EXE%' -Certificate $cert -TimestampServer 'http://timestamp.digicert.com' -HashAlgorithm SHA256 | Out-Host } else { 'No DEV cert; skipping installer signing.' }"

echo.
echo ✅ Installer ready: %SETUP_EXE%
pause
