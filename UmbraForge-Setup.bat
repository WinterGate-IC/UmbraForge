@echo off
setlocal
cd /d "%~dp0"
py -3 installer.py %*
if errorlevel 1 python installer.py %*
exit /b %errorlevel%
