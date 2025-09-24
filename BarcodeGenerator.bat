@echo off
call env\Scripts\activate

start python app.py
timeout /t 3 >nul
start http://localhost:5000

pause
