@echo off
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\setup.ps1" %*
if errorlevel 1 (
  echo Setup failed. Check the message and .local-data\setup logs.
  pause
  exit /b 1
)
