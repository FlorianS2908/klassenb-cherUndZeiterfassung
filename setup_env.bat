@echo off
setlocal
cd /d "%~dp0"
echo Das Setup laeuft jetzt in der Weboberflaeche.
echo Der alte Konsolen-Assistent setup_env.py bleibt nur als Fallback erhalten.
call start_tool.bat
timeout /t 3 /nobreak >nul
start http://localhost:5173/setup
