"""Central configuration. Everything tweakable lives here, in ONE place.

Paths are all relative to this file, so the whole folder can be copied to the
Windows PC and it just works. The ONLY thing that ever goes to the internet is
a scanned-image page being sent to the Gemini API for OCR (see the API key
section below) — everything else stays on this machine.
"""
import os
from pathlib import Path

# Project root = the folder this file sits in.
ROOT = Path(__file__).resolve().parent

# The three banks. These names are used for folder names, Excel tab names,
# and the verification .docx file names. Keep them as the 3-letter codes.
BANKS = ["LGT", "BoS", "UBS"]


# --- Per-bank locations -----------------------------------------------------
def inbox_dir(bank: str) -> Path:
    """Folder where your colleague drops that bank's client statement PDFs."""
    return ROOT / "banks" / bank / "inbox"


def verification_docx(bank: str) -> Path:
    """The Word doc (one per bank) holding the screenshot snapshots to eyeball."""
    return ROOT / "banks" / bank / f"{bank}_verification.docx"


# --- Shared outputs ---------------------------------------------------------
OUTPUT_DIR = ROOT / "output"
MASTER_WORKBOOK = OUTPUT_DIR / "nav_master.xlsx"    # one workbook, 3 tabs
LOGS_DIR = ROOT / "logs"
SNAPSHOT_DIR = LOGS_DIR / "snapshots"               # PNG crops kept for reference
PROCESSED_INDEX = ROOT / "processed_index.json"     # remembers what was already done


# --- Screenshot settings ----------------------------------------------------
# Higher DPI = sharper screenshot but bigger image. 200 is a good readable default.
SNAPSHOT_DPI = 200
# Padding (in PDF points, 72 = 1 inch) added around a found value so the
# screenshot shows surrounding context, not just the bare number.
SNAPSHOT_PADDING = 45


# --- GEMINI API (Version-2 OCR for scanned pages) ----------------------------
# The key lives in api_key.txt next to this file (created by setup / first run;
# never committed to git). The GEMINI_API_KEY environment variable, if set,
# wins over the file. Only scanned/image-only pages ever use the API — normal
# bank-portal PDFs with selectable text are read locally and never uploaded.
API_KEY_FILE = ROOT / "api_key.txt"
API_KEY_PLACEHOLDER = "PASTE-YOUR-GEMINI-API-KEY-HERE"
GEMINI_MODEL = "gemini-2.5-flash"   # fast + cheap; change here if the company
                                    # standardises on a different model


def get_gemini_api_key() -> str:
    """The company's Gemini API key, or '' if none has been set yet."""
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if key:
        return key
    try:
        key = API_KEY_FILE.read_text(encoding="utf-8-sig").strip()
    except (FileNotFoundError, OSError):
        return ""
    if not key or "PASTE" in key.upper() or " " in key:
        return ""
    return key


def ensure_api_key_file() -> None:
    """Create api_key.txt with a placeholder so the colleague has a file to
    open and paste into. Never overwrites an existing file."""
    if not API_KEY_FILE.exists():
        API_KEY_FILE.write_text(API_KEY_PLACEHOLDER + "\n", encoding="utf-8")


# --- FEE LOGIC (PLACEHOLDER) -----------------------------------------------
# We agreed to define the real rule once we look at a real statement together.
# Example only: a 1% management fee on net NAV would be MGMT_FEE_RATE = 0.01.
# Leave as None and the Fee column stays blank until we set the real rule.
MGMT_FEE_RATE = None
