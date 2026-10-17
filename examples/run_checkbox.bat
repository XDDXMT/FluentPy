@echo off
cd /d "%~dp0"
python checkbox.py %*
if errorlevel 1 pause
