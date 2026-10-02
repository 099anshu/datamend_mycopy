#!/bin/bash
set -e
command -v brew >/dev/null || /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
brew list python@3.11 >/dev/null 2>&1 || brew install python@3.11
python3.11 -m venv .venv && source .venv/bin/activate
pip install --upgrade pip && pip install -r requirements.txt
echo "Ready. Next: source .venv/bin/activate && streamlit run app.py"
