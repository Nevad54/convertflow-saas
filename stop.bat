@echo off
title ConvertFlow - Stopping

echo Stopping ConvertFlow...

:: Stop uvicorn (Python web app)
taskkill /F /FI "WINDOWTITLE eq ConvertFlow" >NUL 2>&1

:: Stop any Python process running uvicorn on port 8080
for /f "tokens=5" %%a in ('netstat -aon ^| find ":8080"') do (
    taskkill /F /PID %%a >NUL 2>&1
)

:: Stop Ollama
taskkill /F /IM ollama.exe >NUL 2>&1

echo Done. ConvertFlow and Ollama are stopped.
timeout /t 2 /nobreak >NUL
