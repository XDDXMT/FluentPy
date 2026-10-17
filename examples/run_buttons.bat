@echo off
cd /d "%~dp0"
python buttons.py %*
if errorlevel 1 pause
