@echo off
setlocal EnableExtensions
cd /d "%~dp0"

title Klassenbuch-Timebutler Tool

echo ============================================================
echo Klassenbuch-Timebutler Tool - Start
echo ============================================================
echo.
echo Diese Datei prueft Installation und Abhaengigkeiten automatisch.
echo Zugangsdaten werden nicht in der CMD abgefragt.
echo Das Setup laeuft bei Bedarf in der Weboberflaeche.
echo.

set "PIP_DISABLE_PIP_VERSION_CHECK=1"
set "TMP=%CD%\.tools\temp"
set "TEMP=%CD%\.tools\temp"
if not exist ".tools" mkdir ".tools"
if not exist ".tools\temp" mkdir ".tools\temp"

set "PYTHON_CMD=python"
python --version >nul 2>&1
if errorlevel 1 set "PYTHON_CMD=py"

%PYTHON_CMD% --version >nul 2>&1
if errorlevel 1 (
  echo [FEHLER] Python wurde nicht gefunden.
  echo Bitte Python 3.11 oder neuer installieren.
  echo Download: https://www.python.org/downloads/
  goto error
)

%PYTHON_CMD% -c "import sys; raise SystemExit(0 if sys.version_info >= (3,11) else 1)"
if errorlevel 1 (
  echo [FEHLER] Python 3.11 oder neuer ist erforderlich.
  goto error
)
echo [OK] Python ist bereit.

if not exist ".venv\Scripts\python.exe" (
  echo [SETUP] Virtuelle Umgebung fehlt. Erstelle .venv...
  %PYTHON_CMD% -m venv .venv
  if errorlevel 1 goto error
) else (
  echo [OK] Virtuelle Umgebung gefunden.
)

call ".venv\Scripts\activate.bat"
if errorlevel 1 (
  echo [FEHLER] Die virtuelle Umgebung konnte nicht aktiviert werden.
  goto error
)

echo [SETUP] Pruefe Backend-Abhaengigkeiten...
python -c "import fastapi, uvicorn, playwright, dotenv, openai" >nul 2>&1
if errorlevel 1 (
  echo [SETUP] Installiere Backend-Abhaengigkeiten. Das kann ein paar Minuten dauern...
  python -m pip install --upgrade pip
  if errorlevel 1 goto error
  pip install -r backend\requirements.txt
  if errorlevel 1 goto error
) else (
  echo [OK] Backend-Abhaengigkeiten vorhanden.
)

echo [SETUP] Pruefe Playwright-Browser...
python -c "from pathlib import Path; import os; raise SystemExit(0 if (Path(os.environ.get('USERPROFILE','')) / 'AppData' / 'Local' / 'ms-playwright').exists() else 1)" >nul 2>&1
if errorlevel 1 (
  echo [SETUP] Installiere Playwright-Browser...
  python -m playwright install
  if errorlevel 1 goto error
) else (
  echo [OK] Playwright-Browser scheinen vorhanden zu sein.
)

set "NODE_VERSION=24.18.0"
set "NODE_ZIP=node-v%NODE_VERSION%-win-x64.zip"
set "NODE_DIR=%CD%\.tools\node-v%NODE_VERSION%-win-x64"
set "NODE_ZIP_PATH=%CD%\.tools\%NODE_ZIP%"
set "NPM_CMD=npm.cmd"

call "%NPM_CMD%" --version >nul 2>&1
if errorlevel 1 (
  echo [SETUP] Node.js/npm wurde nicht gefunden.
  echo [SETUP] Richte portable Node.js lokal ein. Keine Admin-Rechte noetig.
  if not exist "%NODE_DIR%\node.exe" (
    echo [SETUP] Lade Node.js portable herunter...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Invoke-WebRequest -Uri 'https://nodejs.org/dist/v%NODE_VERSION%/%NODE_ZIP%' -OutFile '%NODE_ZIP_PATH%'"
    if errorlevel 1 (
      echo [FEHLER] Portable Node.js konnte nicht heruntergeladen werden.
      echo Bitte Internetverbindung pruefen oder Node.js LTS manuell installieren:
      echo https://nodejs.org/
      goto error
    )
    echo [SETUP] Entpacke Node.js portable...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Expand-Archive -LiteralPath '%NODE_ZIP_PATH%' -DestinationPath '%CD%\.tools' -Force"
    if errorlevel 1 goto error
  )
  set "PATH=%NODE_DIR%;%PATH%"
  set "NPM_CMD=%NODE_DIR%\npm.cmd"
) else (
  echo [OK] Node.js/npm gefunden.
)

if exist "%NODE_DIR%\npm.cmd" (
  set "PATH=%NODE_DIR%;%PATH%"
  set "NPM_CMD=%NODE_DIR%\npm.cmd"
)

call "%NPM_CMD%" --version >nul 2>&1
if errorlevel 1 (
  echo [FEHLER] npm ist nicht startbar.
  goto error
)
echo [OK] npm ist bereit.

echo [SETUP] Pruefe Frontend-Abhaengigkeiten...
if not exist "frontend\node_modules" (
  echo [SETUP] Installiere Frontend-Abhaengigkeiten. Das kann ein paar Minuten dauern...
  cd frontend
  call "%NPM_CMD%" install
  if errorlevel 1 (
    cd ..
    goto error
  )
  cd ..
) else (
  echo [OK] Frontend-Abhaengigkeiten vorhanden.
)

if not exist ".env" (
  set "START_URL=http://localhost:5173/setup"
  echo [SETUP] Keine .env gefunden. Das Setup wird im Browser geoeffnet.
) else (
  set "START_URL=http://localhost:5173"
  echo [OK] .env gefunden.
)

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
  echo set "PATH=%NODE_DIR%;%%PATH%%"
  echo cd /d "%~dp0frontend"
  echo call "%NPM_CMD%" run dev -- --host 127.0.0.1
  echo echo.
  echo echo Frontend-Fenster bleibt zur Fehleranalyse offen.
  echo pause
) > ".tools\run_frontend_start.cmd"

echo.
echo ============================================================
echo Starte Tool
echo ============================================================
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:5173
echo Browser:  %START_URL%
echo.

start "Klassenbuch Tool Backend" cmd /k ".tools\run_backend_start.cmd"
timeout /t 3 /nobreak >nul
start "Klassenbuch Tool Frontend" cmd /k ".tools\run_frontend_start.cmd"
timeout /t 7 /nobreak >nul
start %START_URL%

echo [OK] Start wurde angestossen.
echo Wenn der Browser nicht automatisch oeffnet:
echo %START_URL%
echo.
pause
exit /b 0

:error
echo.
echo [FEHLER] Installation oder Start ist fehlgeschlagen.
echo Bitte die Meldungen oberhalb pruefen.
echo Dieses Fenster bleibt offen.
echo.
pause
exit /b 1
