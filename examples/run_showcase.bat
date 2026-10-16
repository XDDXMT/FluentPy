@echo off
cd /d "%~dp0"
python showcase.py %*
if errorlevel 1 pause
