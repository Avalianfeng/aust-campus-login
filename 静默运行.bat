@echo off
chcp 65001 >nul
cd /d "%~dp0"
REM 使用 pythonw 避免弹出控制台（供手动双击或旧版任务计划调用）
pythonw "%~dp0AutoLogin.py" --once
