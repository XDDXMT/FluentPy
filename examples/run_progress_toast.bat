@echo off
cd /d "%~dp0"
python progress_toast.py %*
if errorlevel 1 pause
