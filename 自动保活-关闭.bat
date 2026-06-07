@echo off
cd /d "%~dp0"
python -c "import sys; sys.path.insert(0, r'%~dp0'); from AutoLogin import disable_keepalive; ok, msg = disable_keepalive(); print(msg)"
pause
