@echo off
title ConvertFlow SaaS

:: Run the dedicated SaaS app - auth, quota, and billing enabled
set APP_MODE=saas

cd /d "%~dp0"
echo Starting ConvertFlow SaaS on http://localhost:8080

:: Open browser after a short delay (background)
start "" /B cmd /c "timeout /t 4 /nobreak >NUL && start http://localhost:8080"

.venv\Scripts\python.exe -m uvicorn app_saas:app --host 0.0.0.0 --port 8080
