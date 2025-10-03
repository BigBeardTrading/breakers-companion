@echo off
setlocal

call .venv\Scripts\activate.bat 2>NUL
IF %ERRORLEVEL% NEQ 0 (
  echo Creating venv...
  py -m venv .venv || exit /b 1
  call .venv\Scripts\activate.bat
)

pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller

REM OneFile, icon, and embed assets/data
pyinstaller ^
  --noconfirm ^
  --name "Breakers Companion" ^
  --onefile ^
  --windowed ^
  --icon "assets\BBT_BreakersCompanion.ico" ^
  --add-data="assets\bbt.png;assets" ^
  --add-data="assets\Background.png;assets" ^
  --add-data="assets\BBT_BreakersCompanion.ico;assets" ^
  --add-data="data\2025 Donruss Football Master Checklist.xlsx;data" ^
  app.py

echo.
echo Build finished. EXE at: dist\Breakers Companion.exe
pause
