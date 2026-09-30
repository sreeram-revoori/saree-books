#!/bin/bash
# Double-click to start (Mac). First run installs what's needed (needs internet once).
cd "$(dirname "$0")"
if ! .venv/bin/python -c "import streamlit" 2>/dev/null; then
  rm -rf .venv
  echo "First-time setup, please wait..."
  python3 -m venv .venv && .venv/bin/pip install -q -r requirements.txt || { echo "Setup failed. Is Python 3 installed?"; read; exit 1; }
fi
.venv/bin/python -m streamlit run app.py --server.headless=false --browser.gatherUsageStats=false
