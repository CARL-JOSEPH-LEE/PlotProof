@echo off
setlocal
cd /d "%~dp0"
set PYTHONUTF8=1
if not exist .venv\Scripts\pythonw.exe (
  python -m venv .venv
  if errorlevel 1 goto failed
  .venv\Scripts\python.exe -m pip install -e .
  if errorlevel 1 goto failed
)
start "" .venv\Scripts\pythonw.exe -m plotproof.desktop.app
exit /b 0
:failed
echo Could not prepare PlotProof. Install Python 3.10 or newer, or use the packaged Windows download.
pause
exit /b 1
