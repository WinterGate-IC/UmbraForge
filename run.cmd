@echo off
rem Launch UmbraForge from a source checkout.
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" desktop.py %*
) else (
  python desktop.py %*
)
endlocal
