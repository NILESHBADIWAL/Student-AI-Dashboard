@echo off
setlocal
cd /d "%~dp0"

set "PYTHON_EXE=.venv\Scripts\python.exe"
if not exist "%PYTHON_EXE%" (
    if exist "venv\Scripts\python.exe" (
        set "PYTHON_EXE=venv\Scripts\python.exe"
    ) else (
    echo The project virtual environment was not found.
    echo From this folder, run:
    echo   python -m venv .venv
    echo   .venv\Scripts\python.exe -m pip install -r backend\requirements.txt
    pause
    exit /b 1
    )
)

powershell.exe -NoProfile -Command "try { $health = Invoke-RestMethod -Uri 'http://127.0.0.1:8000/health' -TimeoutSec 2; $page = Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:8000/' -TimeoutSec 2; if ($health.status -eq 'ok' -and $page.StatusCode -eq 200 -and $page.Content.Contains('id=\"chatBox\"')) { exit 0 } } catch { }; exit 1"
if not errorlevel 1 (
    echo Dashboard is already running. Opening http://localhost:8000/
    start "" "http://localhost:8000/"
    exit /b 0
)

echo Starting the Student AI Dashboard...
echo When the server is ready, open http://localhost:8000/
echo Keep this window open while using the dashboard.
echo Press Ctrl+C to stop the server.
echo.

"%PYTHON_EXE%" -m uvicorn api:app --app-dir backend --host 127.0.0.1 --port 8000
pause
