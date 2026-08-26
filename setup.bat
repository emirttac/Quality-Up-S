@echo off
rem One-shot Windows setup: create .venv and install requirements.txt
setlocal EnableExtensions
cd /d "%~dp0"
call "%~dp0run.bat"
