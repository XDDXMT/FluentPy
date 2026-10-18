@echo off
cd /d "%~dp0\.."
python -X utf8 -B examples/info_bar.py
if errorlevel 1 pause
