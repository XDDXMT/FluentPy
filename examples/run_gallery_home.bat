@echo off
cd /d "%~dp0.."
python examples\gallery_home.py %*
if errorlevel 1 pause
