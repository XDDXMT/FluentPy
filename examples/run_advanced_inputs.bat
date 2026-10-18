@echo off
cd /d "%~dp0.."
python examples\advanced_inputs.py %*
if errorlevel 1 pause
