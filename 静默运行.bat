@echo off
chcp 65001 >nul
cd /d "%~dp0"
python "%~dp0AutoLogin.py" --once >> "%~dp0logs\task.log" 2>&1
