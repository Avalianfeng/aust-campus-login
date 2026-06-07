@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 正在启动校园网登录脚本...
python "%~dp0AutoLogin.py" --once
pause
