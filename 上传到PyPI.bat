@echo off
setlocal
cd /d "%~dp0"
set "RELEASE_PYTHON=%~dp0build\pypi-tools\Scripts\python.exe"
set "PYTHONUTF8=1"
if not exist "%RELEASE_PYTHON%" (
  echo Packaging tools are missing. See docs\publishing.md.
  pause
  exit /b 1
)
if /i "%~1"=="--check" (
  "%RELEASE_PYTHON%" -X utf8 -B "%~dp0scripts\publish_pypi.py"
  if errorlevel 1 exit /b 1
  exit /b 0
)
echo Project: fluentpy-qt
echo Paste your PyPI API token at the hidden token/password prompt.
echo Do not enter your account password. Your token will not be saved.
"%RELEASE_PYTHON%" -X utf8 -B "%~dp0scripts\publish_pypi.py" --upload
if errorlevel 1 (
  echo Upload or verification did not finish. Matching files can be safely resumed.
  pause
  exit /b 1
)
pause
