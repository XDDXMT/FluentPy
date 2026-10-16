@echo off
chcp 65001 >nul
cd /d "%~dp0.."
python -B examples\date_picker.py %*
if errorlevel 1 pause
