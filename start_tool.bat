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
set "NPM_CMD=npm"
set "PORTABLE_NODE_DIR="
for /d %%D in ("%CD%\.tools\node-v*-win-x64") do set "PORTABLE_NODE_DIR=%%~fD"
npm --version >nul 2>&1
if errorlevel 1 (
  if defined PORTABLE_NODE_DIR (
    set "PATH=%PORTABLE_NODE_DIR%;%PATH%"
    set "NPM_CMD=%PORTABLE_NODE_DIR%\npm.cmd"
  ) else (
    echo Node.js/npm wurde nicht gefunden.
    echo Bitte install.bat oder start_test.cmd ausfuehren, damit Node.js eingerichtet wird.
    pause
    exit /b 1
  )
)
if not exist ".env" echo Keine .env gefunden. Das Setup wird im Browser geoeffnet.
if not exist ".tools" mkdir ".tools"
(
  echo @echo off
  echo cd /d "%~dp0backend"
  echo ..\.venv\Scripts\python.exe -m app.main
  echo echo.
  echo echo Backend-Fenster bleibt zur Fehleranalyse offen.
  echo pause
) > ".tools\run_backend_start.cmd"
(
  echo @echo off
  echo set "PATH=%PORTABLE_NODE_DIR%;%%PATH%%"
  echo cd /d "%~dp0frontend"
  echo call "%NPM_CMD%" run dev -- --host 127.0.0.1
  echo echo.
  echo echo Frontend-Fenster bleibt zur Fehleranalyse offen.
  echo pause
) > ".tools\run_frontend_start.cmd"
start "Klassenbuch Backend" cmd /k ".tools\run_backend_start.cmd"
start "Klassenbuch Frontend" cmd /k ".tools\run_frontend_start.cmd"
timeout /t 5 /nobreak >nul
if exist ".env" (
  start http://localhost:5173
) else (
  start http://localhost:5173/setup
)
echo Backend: http://localhost:8000
echo Frontend: http://localhost:5173
