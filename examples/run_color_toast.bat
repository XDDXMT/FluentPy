@echo off
cd /d "%~dp0.."
python examples\color_toast.py %*
if errorlevel 1 pause
