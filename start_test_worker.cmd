@echo off
setlocal EnableExtensions
cd /d "%~dp0"

title Klassenbuch-Timebutler Tool - Installieren und Testen
set PIP_NO_INDEX=
set PIP_INDEX_URL=https://pypi.org/simple
set PIP_DISABLE_PIP_VERSION_CHECK=1
set HTTP_PROXY=
set HTTPS_PROXY=
set ALL_PROXY=
set http_proxy=
set https_proxy=
set all_proxy=
set NO_PROXY=*
set no_proxy=*
set TMP=%CD%\.tools\temp
set TEMP=%CD%\.tools\temp
if not exist ".tools" mkdir ".tools"
if not exist ".tools\temp" mkdir ".tools\temp"
if not exist ".tools\logs" mkdir ".tools\logs"
set LOG_FILE=%CD%\.tools\logs\start_test_%RANDOM%_%RANDOM%.log
echo Start: %DATE% %TIME% > "%LOG_FILE%"

echo ============================================================
echo Klassenbuch-Timebutler Tool - Installieren und Testen
echo ============================================================
echo.
echo Diese Datei prueft die Installation automatisch.
echo Wenn etwas fehlt, wird es eingerichtet.
echo Danach startet das Tool im Dry-Run-Testmodus.
echo.
echo Logdatei: %LOG_FILE%
echo.

set PYTHON_CMD=python
python --version >nul 2>&1
if errorlevel 1 set PYTHON_CMD=py

%PYTHON_CMD% --version >nul 2>&1
if errorlevel 1 (
  echo [FEHLER] Python wurde nicht gefunden.
  echo Bitte Python 3.11 oder neuer installieren.
  echo Download: https://www.python.org/downloads/
  echo.
  pause
  exit /b 1
)

%PYTHON_CMD% -c "import sys; raise SystemExit(0 if sys.version_info >= (3,11) else 1)"
if errorlevel 1 (
  echo [FEHLER] Python 3.11 oder neuer ist erforderlich.
  echo.
  pause
  exit /b 1
)

set NODE_VERSION=24.18.0
set NODE_ZIP=node-v%NODE_VERSION%-win-x64.zip
set NODE_DIR=%CD%\.tools\node-v%NODE_VERSION%-win-x64
set NODE_ZIP_PATH=%CD%\.tools\%NODE_ZIP%
set NPM_CMD=npm.cmd

call "%NPM_CMD%" --version >nul 2>&1
if errorlevel 1 (
  echo [SETUP] Node.js/npm wurde nicht gefunden.
  echo [SETUP] Richte portable Node.js-Version lokal ein. Keine Admin-Rechte noetig.
  if not exist ".tools" mkdir ".tools"
  if not exist "%NODE_DIR%\node.exe" (
    echo [SETUP] Lade Node.js portable herunter...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Invoke-WebRequest -Uri 'https://nodejs.org/dist/v%NODE_VERSION%/%NODE_ZIP%' -OutFile '%NODE_ZIP_PATH%'"
    if errorlevel 1 (
      echo [FEHLER] Portable Node.js konnte nicht heruntergeladen werden.
      echo Bitte pruefe die Internetverbindung oder installiere Node.js LTS manuell:
      echo https://nodejs.org/
      echo.
      pause
      exit /b 1
    )
    echo [SETUP] Entpacke Node.js portable...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Expand-Archive -LiteralPath '%NODE_ZIP_PATH%' -DestinationPath '%CD%\.tools' -Force"
    if errorlevel 1 (
      echo [FEHLER] Portable Node.js konnte nicht entpackt werden.
      echo.
      pause
      exit /b 1
    )
  )
  set "PATH=%NODE_DIR%;%PATH%"
  set "NPM_CMD=%NODE_DIR%\npm.cmd"
  call "%NODE_DIR%\npm.cmd" --version >nul 2>&1
  if errorlevel 1 (
    echo [FEHLER] Portable Node.js wurde vorbereitet, aber npm ist nicht startbar.
    echo Erwarteter Pfad:
    echo %NODE_DIR%
    echo.
    pause
    exit /b 1
  )
  echo [OK] Portable Node.js ist bereit.
) else (
  echo [OK] Node.js/npm gefunden.
)

if exist "%NODE_DIR%\npm.cmd" (
  set "PATH=%NODE_DIR%;%PATH%"
  set "NPM_CMD=%NODE_DIR%\npm.cmd"
)

echo [SETUP] npm ist bereit.

if not exist ".venv\Scripts\python.exe" (
  echo [SETUP] Virtuelle Umgebung fehlt. Erstelle .venv...
  %PYTHON_CMD% -m venv .venv
  if errorlevel 1 goto error
) else (
  echo [OK] Virtuelle Umgebung gefunden.
)

call .venv\Scripts\activate.bat
if errorlevel 1 (
  echo [FEHLER] Die virtuelle Umgebung konnte nicht aktiviert werden.
  echo.
  pause
  exit /b 1
)

echo [SETUP] Pruefe Backend-Abhaengigkeiten...
python -c "import fastapi, uvicorn, playwright, dotenv, openai" >nul 2>&1
if errorlevel 1 (
  echo [SETUP] Installiere Backend-Abhaengigkeiten. Das kann ein paar Minuten dauern...
  python -m pip install --index-url https://pypi.org/simple --upgrade pip
  if errorlevel 1 goto error
  pip install --index-url https://pypi.org/simple -r backend\requirements.txt
  if errorlevel 1 goto error
) else (
  echo [OK] Backend-Abhaengigkeiten vorhanden.
)

echo [SETUP] Pruefe Playwright-Browser...
if not exist "%USERPROFILE%\AppData\Local\ms-playwright" (
  echo [SETUP] Installiere Playwright-Browser...
  python -m playwright install
  if errorlevel 1 goto error
) else (
  echo [OK] Playwright-Browser scheinen vorhanden zu sein.
)

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
  echo.
  echo [SETUP] Keine .env gefunden. Setup-Assistent wird gestartet.
  echo Zugangsdaten werden verdeckt abgefragt und nicht angezeigt.
  echo.
  python setup_env.py
  if errorlevel 1 goto error
) else (
  echo [OK] .env gefunden.
)

set FORCE_DRY_RUN=true
set VITE_API_BASE_URL=http://localhost:8000

echo.
echo ============================================================
echo Starte Tool im Dry-Run-Testmodus
echo ============================================================
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:5173
echo.
echo Es werden keine finalen Aktionen ausgefuehrt.
echo.

if not exist ".tools" mkdir ".tools"

(
  echo @echo off
  echo cd /d "%~dp0backend"
  echo ..\.venv\Scripts\python.exe -m app.main
  echo echo.
  echo echo Backend-Fenster bleibt zur Fehleranalyse offen.
  echo pause
) > ".tools\run_backend_test.cmd"

(
  echo @echo off
  echo set "PATH=%NODE_DIR%;%%PATH%%"
  echo cd /d "%~dp0frontend"
  echo call "%NPM_CMD%" run dev -- --host 127.0.0.1
  echo echo.
  echo echo Frontend-Fenster bleibt zur Fehleranalyse offen.
  echo pause
) > ".tools\run_frontend_test.cmd"

start "Klassenbuch Tool Backend TEST" cmd /k ".tools\run_backend_test.cmd"
timeout /t 3 /nobreak >nul
start "Klassenbuch Tool Frontend TEST" cmd /k ".tools\run_frontend_test.cmd"

timeout /t 7 /nobreak >nul
start http://localhost:5173

echo.
echo [OK] Teststart wurde angestossen.
echo Wenn der Browser nicht automatisch oeffnet:
echo http://localhost:5173
echo.
pause
exit /b 0

:error
echo.
echo [FEHLER] Installation oder Start ist fehlgeschlagen.
echo Bitte die Meldungen oberhalb pruefen.
echo Details stehen in:
echo %LOG_FILE%
echo.
pause
exit /b 1
