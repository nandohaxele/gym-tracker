@echo off
REM Start the FastAPI backend using the venv's Python.
REM Avoids the common pitfalls on Windows:
REM   - wrong working directory (must be backend\)
REM   - using the global uvicorn / global Python instead of the venv
REM   - WinError 10013 caused by an orphan uvicorn still holding port 8000
REM
REM Run from anywhere by double-clicking, or:  cmd /c start.bat

setlocal

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] .venv not found in %CD%. Create it with:
    echo     python -m venv .venv
    echo     .venv\Scripts\python.exe -m pip install -r requirements.txt
    exit /b 1
)

echo Killing any orphan process listening on port 8000...
for /f "tokens=5" %%P in ('netstat -ano ^| findstr ":8000 " ^| findstr "LISTENING"') do (
    echo   killing PID %%P
    taskkill /F /PID %%P >nul 2>&1
)

echo Starting uvicorn from %CD% using .venv...
".venv\Scripts\python.exe" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

endlocal
