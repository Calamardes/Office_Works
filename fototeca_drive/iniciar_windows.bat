@echo off
REM Doble clic para abrir la app. La primera vez instala lo necesario.
cd /d "%~dp0"
if not exist .venv (
  py -3 -m venv .venv || python -m venv .venv
  .venv\Scripts\python -m pip install -r requirements.txt
)
.venv\Scripts\python -m fototeca_drive
pause
