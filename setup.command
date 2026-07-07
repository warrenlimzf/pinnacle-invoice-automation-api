#!/bin/bash
# ===================================================================
#  ONE-TIME SETUP (Mac). Double-click this once.
#  (First time, macOS may say "unidentified developer" — right-click
#   the file, choose Open, then Open again.)
# ===================================================================
cd "$(dirname "$0")" || exit 1

echo "Checking Python 3..."
if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 not found. Install it from https://www.python.org/downloads/ and re-run."
  read -r -p "Press Enter to close..."
  exit 1
fi
python3 --version

echo "Creating virtual environment (.venv)..."
python3 -m venv .venv
source .venv/bin/activate

echo "Installing libraries..."
# The bundled 'vendor' folder holds Windows wheels. On Mac we install from the
# internet (only the libraries; your client PDFs are never uploaded anywhere
# except scanned-image pages going to the Gemini API for OCR).
python -m pip install --no-index --find-links vendor -r requirements.txt \
  || python -m pip install -r requirements.txt

echo "Creating api_key.txt (where the company's Gemini API key goes)..."
[ -f api_key.txt ] || echo "PASTE-YOUR-GEMINI-API-KEY-HERE" > api_key.txt

echo ""
echo "Setup complete. Two steps left:"
echo "  1. Open api_key.txt, replace the placeholder with the company's"
echo "     Gemini API key, and save."
echo "  2. Run: .venv/bin/python check_api.py  to confirm the key works."
echo "Then double-click run_watcher.command as usual."
read -r -p "Press Enter to close..."
