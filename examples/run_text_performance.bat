@echo off
cd /d "%~dp0"
python text_performance.py %*
if errorlevel 1 pause
