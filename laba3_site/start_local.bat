@echo off
setlocal
set PYTHONDONTWRITEBYTECODE=1
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" manage.py runserver 127.0.0.1:8000
) else (
  echo Install dependencies using the instructions in README.md.
  pause
)
