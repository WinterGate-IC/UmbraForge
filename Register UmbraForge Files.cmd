@echo off
rem Associate .umbra with UmbraForge for this Windows user (no admin needed).
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0register_file_types.ps1"
if errorlevel 1 (
    echo.
    echo Could not register the file type.
    pause
)
endlocal
