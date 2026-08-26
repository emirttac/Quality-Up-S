@echo off
setlocal EnableExtensions
cd /d "%~dp0"

rem Prefer the Windows py launcher, then python on PATH.
set "BOOTSTRAP="
where py >nul 2>nul && set "BOOTSTRAP=py -3"
if not defined BOOTSTRAP (
  where python >nul 2>nul && set "BOOTSTRAP=python"
)
if not defined BOOTSTRAP (
  echo Quality Up'S needs Python 3.10+ with Tcl/Tk.
  echo Install from https://www.python.org/downloads/ ^(check "tcl/tk" and "Add python.exe to PATH"^).
  echo.
  pause
  exit /b 1
)

set "PY=%~dp0.venv\Scripts\python.exe"
set "NEED_SETUP=0"

if not exist "%PY%" set "NEED_SETUP=1"
if "%NEED_SETUP%"=="0" (
  "%PY%" -c "import numpy" >nul 2>nul
  if errorlevel 1 set "NEED_SETUP=1"
)

if "%NEED_SETUP%"=="1" (
  echo Setting up Quality Up'S environment...
  if not exist "%PY%" (
    echo Creating virtual environment...
    %BOOTSTRAP% -m venv "%~dp0.venv"
    if errorlevel 1 (
      echo Failed to create .venv
      pause
      exit /b 1
    )
  )
  echo Installing dependencies from requirements.txt...
  "%PY%" -m pip install --upgrade pip
  if errorlevel 1 (
    echo pip upgrade failed.
    pause
    exit /b 1
  )
  "%PY%" -m pip install -r "%~dp0requirements.txt"
  if errorlevel 1 (
    echo Dependency install failed.
    pause
    exit /b 1
  )
  "%PY%" -c "import numpy" >nul 2>nul
  if errorlevel 1 (
    echo numpy is still missing after install. Check the errors above.
    pause
    exit /b 1
  )
  echo Setup complete.
  echo.
)

"%PY%" "%~dp0main.py"
set "status=%ERRORLEVEL%"
if not "%status%"=="0" (
  echo.
  echo Quality Up'S closed with an error ^(%status%^).
  pause
)
exit /b %status%
