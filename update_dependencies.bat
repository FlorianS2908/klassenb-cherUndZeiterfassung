@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\activate.bat" (
  echo Virtuelle Umgebung fehlt. Bitte zuerst install.bat ausfuehren.
  pause
  exit /b 1
)
call .venv\Scripts\activate.bat
pip install -r backend\requirements.txt
if errorlevel 1 goto error
python -m playwright install
if errorlevel 1 goto error
cd frontend
npm install
if errorlevel 1 goto error
echo Abhaengigkeiten aktualisiert.
pause
exit /b 0
:error
echo Aktualisierung fehlgeschlagen.
pause
exit /b 1
