@echo off
cd /d "%~dp0.."
python examples\cards.py %*
if errorlevel 1 pause
