@echo off
cd /d "%~dp0.."
python examples\colors.py %*
if errorlevel 1 pause
