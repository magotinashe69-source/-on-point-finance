@echo off
REM ============================================================
REM  On Point Finance - desktop launcher
REM  Double-click this file to start the app.
REM ============================================================

REM Work from the folder this file lives in.
cd /d "%~dp0"

REM Activate the virtual environment.
call ".venv\Scripts\activate.bat"

REM Open the app in the default web browser.
start "" "http://127.0.0.1:5000"

REM Start the production server. Keep this window open while using the app.
python run_prod.py

REM If the server stops or cannot start, keep the window open so the
REM message can be read.
echo.
echo The app has stopped. You can close this window.
pause
