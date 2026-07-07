#!/bin/bash
# ===================================================================
#  START THE WATCHER (Mac). Double-click to begin. Leave the window open.
#  Drop statement PDFs into the bank inbox folders; they process
#  automatically. Press Ctrl+C (or close the window) to stop.
# ===================================================================
cd "$(dirname "$0")" || exit 1

if [ ! -f ".venv/bin/activate" ]; then
  echo "Setup has not been run yet. Double-click setup.command first."
  read -r -p "Press Enter to close..."
  exit 1
fi

source .venv/bin/activate
python watcher.py
read -r -p "Press Enter to close..."
