@echo off
REM ===================================================================
REM  DIAGNOSE (Windows). Dumps the text the tool sees in each inbox PDF
REM  to logs\diagnose\*.txt. Run when a statement extracts wrongly, then
REM  send Warren the .txt for that statement.
REM  Tip: "diagnose.bat UBS" dumps only one bank (faster).
REM ===================================================================
cd /d "%~dp0"

if not exist ".venv\Scripts\activate.bat" (
    echo  Setup has not been run yet. Double-click setup.bat first.
    pause
    exit /b 1
)

call .venv\Scripts\activate.bat
python diagnose.py %*
pause
