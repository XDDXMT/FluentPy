@echo off
cd /d "%~dp0.."
python examples\expandable_cards.py %*
if errorlevel 1 pause
