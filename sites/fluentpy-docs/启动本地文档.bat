@echo off
setlocal
cd /d "%~dp0"
echo FluentPy docs: http://127.0.0.1:8767/#/introduction
echo LAN access: http://YOUR-LAN-IP:8767/#/introduction
echo Keep this window open while using the documentation.
python -B -m http.server 8767 --bind 0.0.0.0 --directory dist
pause
