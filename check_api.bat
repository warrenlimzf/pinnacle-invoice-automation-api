@echo off
REM ===================================================================
REM  CHECK THE API KEY (Windows). Double-click after pasting the
REM  company's Gemini API key into api_key.txt. Sends one tiny test
REM  request (no client data) and tells you if the key works.
REM ===================================================================
cd /d "%~dp0"

if not exist ".venv\Scripts\activate.bat" (
    echo  Setup has not been run yet. Double-click setup.bat first.
    pause
    exit /b 1
)

call .venv\Scripts\activate.bat
python check_api.py
pause
