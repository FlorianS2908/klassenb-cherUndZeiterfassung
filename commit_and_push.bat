@echo off
setlocal
cd /d "%~dp0"
set COMMIT_MESSAGE=%~1
if "%COMMIT_MESSAGE%"=="" set COMMIT_MESSAGE=Update Klassenbuch und Timebutler Tool
if exist ".venv\Scripts\activate.bat" call .venv\Scripts\activate.bat
set PYTHON_CMD=python
python --version >nul 2>&1
if errorlevel 1 set PYTHON_CMD=py
%PYTHON_CMD% scripts\check_before_commit.py
if errorlevel 1 (
  echo Commit abgebrochen: Sicherheitspruefung fehlgeschlagen.
  pause
  exit /b 1
)
git rev-parse --is-inside-work-tree >nul 2>&1
if errorlevel 1 (
  git init
  if errorlevel 1 goto error
)
git remote get-url origin >nul 2>&1
if errorlevel 1 (
  git remote add origin https://github.com/FlorianS2908/klassenb-cherUndZeiterfassung.git
) else (
  git remote set-url origin https://github.com/FlorianS2908/klassenb-cherUndZeiterfassung.git
)
git branch -M main
git status
git add .
if errorlevel 1 goto error
git status
%PYTHON_CMD% scripts\check_before_commit.py
if errorlevel 1 (
  echo Commit abgebrochen: Sicherheitspruefung nach Staging fehlgeschlagen.
  pause
  exit /b 1
)
git commit -m "%COMMIT_MESSAGE%"
if errorlevel 1 goto error
git push -u origin main
if errorlevel 1 (
  echo Push nach main fehlgeschlagen. Falls main geschuetzt ist, Feature-Branch verwenden.
  git checkout -b feature/initial-klassenbuch-timebutler-tool
  git push -u origin feature/initial-klassenbuch-timebutler-tool
  if errorlevel 1 (
    echo GitHub-Authentifizierung fehlt oder Push-Rechte fehlen. Bitte Git Credential Manager, GitHub Desktop oder GitHub CLI einrichten.
    pause
    exit /b 1
  )
  echo Bitte Pull Request von feature/initial-klassenbuch-timebutler-tool nach main erstellen.
)
echo Commit und Push abgeschlossen.
pause
exit /b 0
:error
echo Git-Aktion fehlgeschlagen.
pause
exit /b 1
