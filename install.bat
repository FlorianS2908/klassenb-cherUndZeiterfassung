@echo off
setlocal
cd /d "%~dp0"
set PYTHON_CMD=python
python --version >nul 2>&1
if errorlevel 1 set PYTHON_CMD=py
%PYTHON_CMD% --version >nul 2>&1
if errorlevel 1 (
  echo Python wurde nicht gefunden. Bitte Python 3.11 oder neuer installieren.
  pause
  exit /b 1
)
%PYTHON_CMD% -c "import sys; raise SystemExit(0 if sys.version_info >= (3,11) else 1)"
if errorlevel 1 (
  echo Python 3.11 oder neuer ist erforderlich.
  pause
  exit /b 1
)
%PYTHON_CMD% -m venv .venv
if errorlevel 1 goto error
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r backend\requirements.txt
if errorlevel 1 goto error
python -m playwright install
if errorlevel 1 goto error
set "NPM_CMD=npm"
set "PORTABLE_NODE_DIR="
for /d %%D in ("%CD%\.tools\node-v*-win-x64") do set "PORTABLE_NODE_DIR=%%~fD"
npm --version >nul 2>&1
if errorlevel 1 (
  if defined PORTABLE_NODE_DIR (
    set "PATH=%PORTABLE_NODE_DIR%;%PATH%"
    set "NPM_CMD=%PORTABLE_NODE_DIR%\npm.cmd"
  ) else (
    echo Node.js/npm wurde nicht gefunden. Bitte Node.js installieren oder start_test.cmd zum automatischen Einrichten nutzen.
    pause
    exit /b 1
  )
)
cd frontend
call "%NPM_CMD%" install
if errorlevel 1 goto error
cd ..
echo Installation abgeschlossen.
echo Das Tool kann mit start_tool.bat gestartet werden.
echo Falls noch keine .env existiert, oeffnet sich das Setup automatisch im Browser.
pause
exit /b 0
:error
echo Installation fehlgeschlagen. Bitte die obige Fehlermeldung pruefen.
pause
exit /b 1
