@echo off
cd /d "%~dp0"
set PYTHONUTF8=1
".pdf-service-venv\Scripts\python.exe" "scripts\share_cloudflare.py" stop
pause
