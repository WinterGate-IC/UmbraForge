@echo off
rem Double-click launcher. Starts UmbraForge without leaving a console open.
setlocal
cd /d "%~dp0"

if exist ".venv\Scripts\pythonw.exe" goto venv
if exist ".venv\Scripts\python.exe" goto venvconsole
where pythonw >nul 2>nul
if not errorlevel 1 goto system
python desktop.py %*
goto end

:venv
start "" ".venv\Scripts\pythonw.exe" "UmbraForge.pyw" %*
goto end

:venvconsole
start "" ".venv\Scripts\python.exe" "UmbraForge.pyw" %*
goto end

:system
start "" pythonw "UmbraForge.pyw" %*

:end
endlocal
