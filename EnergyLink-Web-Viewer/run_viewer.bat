@echo off
call C:\Users\cbroo\venv\energynet\Scripts\activate.bat
cd /d "%~dp0"
python app.py %*
