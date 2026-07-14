@echo off
setlocal EnableExtensions
cd /d "%~dp0"

title Klassenbuch-Timebutler Tool - Starter

echo ============================================================
echo Klassenbuch-Timebutler Tool - Starter
echo ============================================================
echo.
echo Dieser Wrapper bleibt immer offen, auch wenn beim Start ein Fehler passiert.
echo.

if not exist "%~dp0start_test_worker.cmd" (
  echo [FEHLER] start_test_worker.cmd wurde nicht gefunden.
  echo Erwartet im Ordner:
  echo %~dp0
  echo.
  pause
  exit /b 1
)

call "%~dp0start_test_worker.cmd"
set EXIT_CODE=%ERRORLEVEL%

echo.
echo ============================================================
echo Starter beendet mit Exit-Code %EXIT_CODE%
echo ============================================================
echo.
echo Wenn etwas nicht funktioniert hat, pruefe diese Datei:
echo %~dp0.tools\logs
echo.
pause
exit /b %EXIT_CODE%
