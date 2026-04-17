@echo off
title ConvertFlow SaaS

:: Backward-compatible SaaS launcher
call "%~dp0start_saas.bat"
exit /b %errorlevel%
