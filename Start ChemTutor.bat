@echo off
rem Starts ChemTutor and opens it in your browser. Close this window to stop the app.
title ChemTutor (close this window to stop)
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
%PY% chemtutor.py %*
if errorlevel 1 pause
