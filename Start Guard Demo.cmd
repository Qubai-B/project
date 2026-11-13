@echo off
rem Double-click to start the guard demo page. Keep this file in the project folder.
rem It starts demo\live_app.py and opens http://127.0.0.1:8765 in the default browser.
title Guard demo - keep this window open while presenting
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo The Python environment ^(.venv^) was not found in this folder.
  echo Run setup.ps1 first, or move this file back into the project folder.
  pause
  exit /b 1
)
echo Starting the guard demo. The page opens in your browser.
echo Wait for the yellow "Loading the language model" notice to clear before the first upload.
echo Close this window to stop the demo.
echo.
".venv\Scripts\python.exe" demo\live_app.py --open
if errorlevel 1 pause
