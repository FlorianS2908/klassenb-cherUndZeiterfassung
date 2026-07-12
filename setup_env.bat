@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\activate.bat" (
  echo Virtuelle Umgebung fehlt. Bitte zuerst install.bat ausfuehren.
  pause
  exit /b 1
)
call .venv\Scripts\activate.bat
python setup_env.py
if errorlevel 1 (
  echo Setup fehlgeschlagen.
  pause
  exit /b 1
)
pause
