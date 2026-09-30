@echo off
REM Double-click to start (Windows). First run installs what's needed (needs internet once).
cd /d "%~dp0"
.venv\Scripts\python -c "import streamlit" 2>NUL
if errorlevel 1 (
  if exist .venv rmdir /s /q .venv
  echo First-time setup, please wait...
  python -m venv .venv || (echo Setup failed. Please install Python from python.org & pause & exit /b 1)
  .venv\Scripts\pip install -q -r requirements.txt
)
.venv\Scripts\python -m streamlit run app.py --browser.gatherUsageStats=false
