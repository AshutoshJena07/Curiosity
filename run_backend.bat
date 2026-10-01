@echo off
title Image Assistant Backend
echo ============================================================
echo Starting Local Image Assistant Backend Server...
echo ============================================================
cd /d "%~dp0"

echo [1/2] Freeing port 8000 if occupied...
powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue; Write-Host ('Killed PID ' + $_.OwningProcess) }"
powershell -NoProfile -Command "Get-Process -Name 'uvicorn','python' -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like '*uvicorn*' -or $_.CommandLine -like '*api:app*' } | Stop-Process -Force -ErrorAction SilentlyContinue"
echo Waiting for port to clear...
timeout /t 3 /nobreak >nul

IF EXIST "%USERPROFILE%\.venv\Scripts\activate.bat" (
    call "%USERPROFILE%\.venv\Scripts\activate.bat"
) ELSE IF EXIST ".venv\Scripts\activate.bat" (
    call ".venv\Scripts\activate.bat"
) ELSE IF EXIST "venv\Scripts\activate.bat" (
    call "venv\Scripts\activate.bat"
)

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Python is not found in PATH!
    echo Please install Python 3.10+ and check "Add Python to PATH".
    echo.
    pause
    exit /b 1
)

echo.
echo [2/2] Backend starting at http://127.0.0.1:8000
echo Press Ctrl+C to stop.
echo.
python -m uvicorn src.image_analytics.api:app --host 127.0.0.1 --port 8000 --reload --reload-dir src
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Backend failed to start. See error above.
    echo.
)
pause
