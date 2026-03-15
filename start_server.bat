@echo off
REM Start the FastAPI server with uvicorn

if not exist logs mkdir logs
set LOGFILE=%~dp0logs\server.log

echo Activating virtual environment...
call venv\Scripts\activate.bat

echo Starting FastAPI server...
echo Server will run on http://127.0.0.1:8000
echo Press Ctrl+C to stop
echo Logs: %LOGFILE%
echo.

echo [%date% %time%] ========== Server starting ========== >> "%LOGFILE%"
powershell -Command "python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000 2>&1 | Tee-Object -Append -FilePath '%LOGFILE%'"

pause
