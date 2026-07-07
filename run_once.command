#!/bin/bash
# ===================================================================
#  RUN ONCE (Mac). Processes whatever PDFs are in the inboxes now, then stops.
# ===================================================================
cd "$(dirname "$0")" || exit 1

if [ ! -f ".venv/bin/activate" ]; then
  echo "Setup has not been run yet. Double-click setup.command first."
  read -r -p "Press Enter to close..."
  exit 1
fi

source .venv/bin/activate
python run_all_once.py
read -r -p "Press Enter to close..."
