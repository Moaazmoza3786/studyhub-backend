@echo off
echo ========================================
echo    Study Hub Backend Server
echo ========================================
echo.

cd /d "%~dp0"

echo Starting Flask server...
echo Server will run on: http://localhost:5000
echo.
echo Press Ctrl+C to stop the server
echo ========================================
echo.


:: Install dependencies if needed
pip install -r requirements.txt > nul 2>&1

echo Starting Flask server (main.py)...
python main.py

pause
