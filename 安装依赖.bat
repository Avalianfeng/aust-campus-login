@echo off
cd /d "%~dp0"
echo Creating virtual environment .venv ...
python -m venv .venv
if errorlevel 1 (
    echo Failed to create venv. Is Python installed?
    pause
    exit /b 1
)
echo Installing dependencies ...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
    echo Failed to install dependencies.
    pause
    exit /b 1
)
echo Done. Select .venv\Scripts\python.exe as the interpreter in your IDE.
pause
