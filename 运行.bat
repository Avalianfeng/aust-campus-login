@echo off
chcp 65001 >nul
echo 正在启动校园网登录脚本...
python "%~dp0AutoLogin.py"
pause
