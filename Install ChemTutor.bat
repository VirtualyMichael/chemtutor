@echo off
rem ChemTutor installer: double-click this file. It finds Python, checks the AI tutor, and makes a Desktop shortcut.
setlocal
cd /d "%~dp0"
set "PY="
where py >nul 2>nul
if not errorlevel 1 (
  py -3 -c "import sys;sys.exit(0 if sys.version_info>=(3,10) else 1)" >nul 2>nul
  if not errorlevel 1 set "PY=py -3"
)
if not defined PY (
  where python >nul 2>nul
  if not errorlevel 1 (
    python -c "import sys;sys.exit(0 if sys.version_info>=(3,10) else 1)" >nul 2>nul
    if not errorlevel 1 set "PY=python"
  )
)
if not defined PY (
  echo.
  echo ChemTutor needs Python 3.10 or newer, and it was not found on this computer.
  echo Opening the download page. During install, tick "Add python.exe to PATH",
  echo then double-click "Install ChemTutor.bat" again.
  echo.
  start "" "https://www.python.org/downloads/"
  pause
  exit /b 1
)
%PY% setup.py %*
echo.
pause
