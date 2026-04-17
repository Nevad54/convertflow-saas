@echo off
title ConvertFlow Local

:: Run the dedicated local app - no auth, no payments, no quota limits
set APP_MODE=local

:: Ollama model storage on D: drive
set OLLAMA_HOME=D:\.ollama
set OLLAMA_MODELS=D:\.ollama\models

:: Start Ollama in the background (skip if already running)
tasklist /FI "IMAGENAME eq ollama.exe" 2>NUL | find /I "ollama.exe" >NUL
if errorlevel 1 (
    echo Starting Ollama...
    start "" /B ollama serve
    timeout /t 3 /nobreak >NUL
) else (
    echo Ollama already running.
)

:: Start the web app in this window
cd /d "%~dp0"
echo Starting ConvertFlow Local on http://localhost:8080

:: Open browser after a short delay (background)
start "" /B cmd /c "timeout /t 4 /nobreak >NUL && start http://localhost:8080"

:: Run uvicorn in foreground (logs show here)
.venv\Scripts\python.exe -m uvicorn app_local:app --host 0.0.0.0 --port 8080
