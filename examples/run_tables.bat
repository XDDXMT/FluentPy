@echo off
cd /d "%~dp0"
python tables.py %*
if errorlevel 1 pause
