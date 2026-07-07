"""Remembers which PDFs were already processed, so nothing is done twice.

We key on the file's CONTENT (a SHA-1 hash), not its name. That means:
- the watcher's catch-up at startup skips files already done (no needless redo)
- dropping a CORRECTED version (different content) -> processed again
- deliberately re-dropping a file into an inbox (delete it, copy it back) DOES
  re-process it -> the watcher treats a fresh drop as "redo this" (see watcher.py),
  and `run_all_once.py --redo` forces a full rebuild. Re-doing is safe: it just
  overwrites that file's existing row in the Excel.

IMPORTANT: this never moves or deletes your colleague's statement PDFs. The
originals always stay exactly where she put them.
"""
import hashlib
import json
from datetime import datetime
from pathlib import Path

import config


def file_hash(path) -> str:
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _load() -> dict:
    if config.PROCESSED_INDEX.exists():
        try:
            return json.loads(config.PROCESSED_INDEX.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


def already_processed(path) -> bool:
    return file_hash(path) in _load()


def mark_processed(path) -> None:
    data = _load()
    data[file_hash(path)] = {
        "file": Path(path).name,
        "processed_at": datetime.now().isoformat(timespec="seconds"),
    }
    config.PROCESSED_INDEX.write_text(json.dumps(data, indent=2), encoding="utf-8")
