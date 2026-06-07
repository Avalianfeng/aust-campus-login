@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 启动守护模式（每 5 分钟检测，窗口需保持打开）...
python "%~dp0AutoLogin.py" --watch
pause
