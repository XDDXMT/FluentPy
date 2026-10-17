@echo off
cd /d "%~dp0"
python drop.py %*
if errorlevel 1 pause
