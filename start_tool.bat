@echo off
setlocal
cd /d "%~dp0"
set PYTHON_CMD=python
python --version >nul 2>&1
if errorlevel 1 set PYTHON_CMD=py
%PYTHON_CMD% --version >nul 2>&1
if errorlevel 1 (
  echo Python wurde nicht gefunden.
  pause
  exit /b 1
)
if not exist ".venv\Scripts\activate.bat" (
  echo Virtuelle Umgebung fehlt. Bitte zuerst install.bat ausfuehren.
  pause
  exit /b 1
)
call .venv\Scripts\activate.bat
if not exist ".env" echo Keine .env gefunden. Das Setup wird im Browser geoeffnet.
start "Klassenbuch Backend" cmd /k "cd /d %~dp0backend && ..\.venv\Scripts\python.exe -m app.main"
start "Klassenbuch Frontend" cmd /k "cd /d %~dp0frontend && npm run dev -- --host 127.0.0.1"
timeout /t 5 /nobreak >nul
if exist ".env" (
  start http://localhost:5173
) else (
  start http://localhost:5173/setup
)
echo Backend: http://localhost:8000
echo Frontend: http://localhost:5173
