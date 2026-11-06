@echo off
rem Turns on phone access and prints the link to open on your Android phone.
title ChemTutor phone setup
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
  echo ChemTutor needs Python 3.10 or newer. Get it at https://www.python.org/downloads/
  pause
  exit /b 1
)
%PY% chemtutor.py phone %*
echo.
pause
