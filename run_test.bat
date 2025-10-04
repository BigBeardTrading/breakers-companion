@echo off
set "BC_DATA_DIR=%LOCALAPPDATA%\BreakersCompanion-TEST"
if exist "dist\Breakers Companion TEST.exe" (
  start "" "dist\Breakers Companion TEST.exe"
) else (
  start "" "Breakers Companion TEST.exe"
)
