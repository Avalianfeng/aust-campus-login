@echo off
cd /d "%~dp0"
python -c "import sys; sys.path.insert(0, r'%~dp0'); from AutoLogin import enable_keepalive; ok, msg = enable_keepalive(); print(msg)"
pause
