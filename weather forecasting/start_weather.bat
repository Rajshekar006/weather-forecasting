@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>&1
if errorlevel 1 (
  echo Python was not found. Install Python from https://www.python.org/downloads/
  pause
  exit /b 1
)

echo Installing dependencies...
py -m pip install -r requirements.txt -q

echo.
echo Starting Weather Forecast at http://127.0.0.1:5050
echo Keep this window open to keep the server running.
echo.

start "" "http://127.0.0.1:5050"
py server.py --open

pause
