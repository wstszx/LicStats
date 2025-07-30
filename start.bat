@echo off
echo Starting License Monitor Dashboard...
echo.

cd /d "%~dp0backend"

echo Installing dependencies...
pip install -r requirements.txt

echo.
echo Starting Flask server...
echo Dashboard will be available at: http://localhost:5000
echo.

python app.py

pause