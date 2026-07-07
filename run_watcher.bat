@echo off
REM ===================================================================
REM  START THE WATCHER (Windows). Double-click to begin.
REM  Leave this window open. Drop statement PDFs into the bank inbox
REM  folders and they get processed automatically.
REM  Close the window (or press Ctrl+C) to stop.
REM ===================================================================
cd /d "%~dp0"

if not exist ".venv\Scripts\activate.bat" (
    echo  Setup has not been run yet. Double-click setup.bat first.
    pause
    exit /b 1
)

call .venv\Scripts\activate.bat
python watcher.py
pause
