@echo off
REM ===================================================================
REM  ONE-TIME SETUP (Windows). Double-click this once.
REM  Creates an isolated Python environment, installs the libraries,
REM  and creates api_key.txt for you to paste the Gemini API key into.
REM ===================================================================
cd /d "%~dp0"

echo.
echo Checking Python...
python --version
if errorlevel 1 (
    echo.
    echo  Python was not found. Install it first from https://www.python.org/downloads/
    echo  IMPORTANT: on the first install screen, tick "Add python.exe to PATH".
    echo.
    pause
    exit /b 1
)

echo.
echo Creating virtual environment (.venv)...
python -m venv .venv

echo.
echo Installing libraries from the bundled 'vendor' folder (no internet needed)...
call .venv\Scripts\activate.bat
python -m pip install --no-index --find-links vendor -r requirements.txt
if errorlevel 1 (
    echo.
    echo  Offline install did not complete - trying the internet as a fallback...
    echo  ^(This usually means a different Python version. Recommended: Python 3.12.^)
    python -m pip install -r requirements.txt
)

echo.
echo Creating api_key.txt (where the company's Gemini API key goes)...
if not exist "api_key.txt" echo PASTE-YOUR-GEMINI-API-KEY-HERE> api_key.txt

echo.
echo ===================================================================
echo  Setup complete. Two steps left:
echo    1. Open  api_key.txt  in Notepad, replace the placeholder with
echo       the company's Gemini API key, and save.
echo    2. Double-click  check_api.bat  to confirm the key works.
echo  Then use  run_watcher.bat  (or run_once.bat) as usual.
echo ===================================================================
pause
