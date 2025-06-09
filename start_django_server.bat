@echo off
echo Starting Django server...
cd /d "%~dp0\python_dist"
python run_app.py
pause 