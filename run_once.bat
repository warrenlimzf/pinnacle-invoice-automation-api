@echo off
REM ===================================================================
REM  RUN ONCE (Windows). Processes whatever PDFs are in the inboxes now,
REM  then closes. Use this instead of the watcher for on-demand runs.
REM ===================================================================
cd /d "%~dp0"

if not exist ".venv\Scripts\activate.bat" (
    echo  Setup has not been run yet. Double-click setup.bat first.
    pause
    exit /b 1
)

call .venv\Scripts\activate.bat
python run_all_once.py
pause
