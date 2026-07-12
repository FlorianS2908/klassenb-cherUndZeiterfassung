@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\activate.bat" (
  echo Virtuelle Umgebung fehlt. Bitte zuerst install.bat ausfuehren.
  pause
  exit /b 1
)
set FORCE_DRY_RUN=true
echo Dry-Run-Modus aktiv
call start_tool.bat
