@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Ejecuta INSTALAR_WINDOWS.cmd primero.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" configure_integrations.py
pause
