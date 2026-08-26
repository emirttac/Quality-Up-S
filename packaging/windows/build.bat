@echo off
setlocal EnableExtensions
cd /d "%~dp0..\.."

echo === Quality Up'S Windows build ===
echo.

if not exist ".venv\Scripts\python.exe" (
  echo Create and populate .venv first: run.bat or setup.bat
  exit /b 1
)

set "PY=.venv\Scripts\python.exe"

echo [1/3] Installing build dependencies...
"%PY%" -m pip install -r requirements-build.txt
if errorlevel 1 exit /b 1

echo [2/3] PyInstaller onedir bundle...
"%PY%" -m PyInstaller packaging\quality_ups.spec --noconfirm --clean --distpath dist --workpath build\pyinstaller
if errorlevel 1 exit /b 1

if not exist "dist\QualityUps\QualityUps.exe" (
  echo PyInstaller output missing: dist\QualityUps\QualityUps.exe
  exit /b 1
)

echo [3/3] Inno Setup installer...
set "ISCC="
if exist "%LocalAppData%\Programs\Inno Setup 6\ISCC.exe" set "ISCC=%LocalAppData%\Programs\Inno Setup 6\ISCC.exe"
if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"

if not defined ISCC (
  echo.
  echo Inno Setup 6 not found. Install from https://jrsoftware.org/isinfo.php
  echo Then compile packaging\windows\QualityUps.iss
  echo PyInstaller bundle is ready at dist\QualityUps\
  exit /b 0
)

REM 8.3 short path avoids the apostrophe in "Quality Up'S" breaking ISCC
for %%I in ("packaging\windows\QualityUps.iss") do "%ISCC%" "%%~sI"
if errorlevel 1 exit /b 1

echo.
echo Done.
echo   App:       dist\QualityUps\QualityUps.exe
echo   Installer: dist\installer\QualityUps-Setup-1.0.exe
exit /b 0
