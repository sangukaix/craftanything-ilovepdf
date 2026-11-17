@echo off
cd /d "%~dp0"
".pdf-service-venv\Scripts\python.exe" "scripts\start_pdf_tools.py"
if errorlevel 1 pause
