@echo off
cd /d "%~dp0.."
python examples\toast.py
if errorlevel 1 pause
