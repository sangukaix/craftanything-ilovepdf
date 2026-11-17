@echo off
cd /d "%~dp0"
set PYTHONUTF8=1
".pdf-service-venv\Scripts\python.exe" "scripts\run_checks.py"
exit /b %errorlevel%
