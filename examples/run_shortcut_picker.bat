@echo off
cd /d "%~dp0"
python shortcut_picker.py %*
if errorlevel 1 pause
