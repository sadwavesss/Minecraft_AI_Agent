@echo off
REM Start the FastAPI server with uvicorn

echo Activating virtual environment...
call venv\Scripts\activate.bat

echo Starting FastAPI server...
echo Server will run on http://127.0.0.1:8000
echo Press Ctrl+C to stop
echo.

python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000

pause
