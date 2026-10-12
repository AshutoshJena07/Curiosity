@echo off
title Curiosity AI Backend & Live Dashboard
echo ============================================================
echo Starting Curiosity AI Backend + Real-Time Evaluation Dashboard...
echo ============================================================
cd /d "%~dp0"

echo [1/3] Freeing port 8000 if occupied...
powershell -NoProfile -Command "try { (Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue).OwningProcess | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue } } catch {}"
timeout /t 2 /nobreak >nul

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

echo [2/3] Launching Real-Time Evaluation Dashboard & Browser UI...
start "Curiosity Live Evaluation Dashboard" powershell -NoProfile -WindowStyle Normal -Command "Start-Sleep -Seconds 2; & python scripts/live_dashboard_gui.py"
powershell -NoProfile -Command "Start-Sleep -Seconds 3; Start-Process 'http://127.0.0.1:8000'"

echo.
echo [3/3] Backend running at http://127.0.0.1:8000
echo Frontend UI: http://127.0.0.1:8000/
echo Real-time Web Dashboard: http://127.0.0.1:8000/dashboard
echo Press Ctrl+C to stop.
echo.
python -m uvicorn src.image_analytics.api:app --host 127.0.0.1 --port 8000 --reload --reload-dir src
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Backend failed to start. See error above.
    echo.
)
pause
