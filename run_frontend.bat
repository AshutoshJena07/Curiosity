@echo off
title Image Assistant Frontend (Vite Dev Server)
echo ============================================================
echo Starting Local Image Assistant Frontend (React Dev Server)...
echo ============================================================
cd /d "%~dp0frontend-react"

where node >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Node.js is not installed or not in PATH!
    echo Please install Node.js from https://nodejs.org/ to run the frontend dev server.
    pause
    exit /b 1
)

IF NOT EXIST "node_modules\vite\bin\vite.js" (
    echo [INFO] Installing frontend dependencies...
    where npm.cmd >nul 2>&1
    if %errorlevel% equ 0 (
        call npm.cmd install
    ) else if exist "C:\Program Files\nodejs\npm.cmd" (
        call "C:\Program Files\nodejs\npm.cmd" install
    ) else (
        call npm install
    )
)

echo [1/2] Freeing port 5173 if occupied...
powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort 5173 -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue; Write-Host ('Killed PID ' + $_.OwningProcess) }"

echo.
echo [2/2] Starting Vite Dev Server on http://localhost:5173
echo Proxied to backend at http://127.0.0.1:8000
echo.

node "node_modules\vite\bin\vite.js" --host 127.0.0.1 --port 5173 --open
pause
