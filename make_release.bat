@echo off
setlocal ENABLEDELAYEDEXPANSION
cd /d "%~dp0"

REM ---- read version from VERSION (fallback 0.0.0) ----
set "APP_VER="
if exist "VERSION" (set /p APP_VER=<VERSION)
if "%APP_VER%"=="" set "APP_VER=0.0.0"

REM ---- ensure release folder ----
set "REL=release\%APP_VER%"
if not exist "release" mkdir "release"
if exist "%REL%" rmdir /s /q "%REL%"
mkdir "%REL%"

REM ---- pick up artifacts if they exist ----
set "SETUP=build\installer\BreakersCompanion-Setup-%APP_VER%.exe"
set "ONEFILE=dist\Breakers Companion.exe"
set "ONEDIR_EXE=dist\Breakers Companion\Breakers Companion.exe"

if exist "%SETUP%" copy /y "%SETUP%" "%REL%" >nul
if exist "%ONEFILE%" copy /y "%ONEFILE%" "%REL%\Breakers Companion (one-file).exe" >nul
if exist "%ONEDIR_EXE%" copy /y "%ONEDIR_EXE%" "%REL%\Breakers Companion (onedir main).exe" >nul

copy /y "VERSION" "%REL%" >nul

REM ---- tiny release notes ----
(
  echo Breakers Companion %APP_VER%
  echo ----------------------------
  echo Contents:
  if exist "%REL%\Breakers Companion (one-file).exe" echo - Breakers Companion (one-file).exe
  if exist "%REL%\Breakers Companion (onedir main).exe" echo - Breakers Companion (onedir main).exe
  if exist "%REL%\BreakersCompanion-Setup-%APP_VER%.exe" echo - BreakersCompanion-Setup-%APP_VER%.exe (recommended)
  echo.
  echo Verify checksums in SHA256SUMS.txt
) > "%REL%\README-RELEASE.txt"

REM ---- generate SHA256 checksums ----
powershell -NoProfile -ExecutionPolicy Bypass ^
 "Get-ChildItem -Path '%REL%' -Filter *.exe | Get-FileHash -Algorithm SHA256 | ForEach-Object { '{0}  {1}' -f $_.Hash, (Split-Path $_.Path -Leaf) } | Set-Content -Path '%REL%\SHA256SUMS.txt'"

REM ---- zip it ----
set "ZIP=release\BreakersCompanion-v%APP_VER%-windows.zip"
powershell -NoProfile -ExecutionPolicy Bypass ^
 "Compress-Archive -Path '%REL%\*' -DestinationPath '%ZIP%' -Force"

echo.
echo ✅ Release bundle ready:
echo   %REL%
echo   %ZIP%
start "" explorer.exe "release"
pause
