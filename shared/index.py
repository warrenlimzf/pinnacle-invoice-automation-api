"""Remembers which PDFs were already read, and which ones still need attention,
so nothing is done twice and nothing is ever silently lost.

We key on the file's CONTENT (a SHA-1 hash), not its name. That means:
- the watcher's catch-up at startup skips files already done (no needless redo)
- dropping a CORRECTED version (different content) -> processed again
- deliberately re-dropping a file into an inbox (delete it, copy it back) DOES
  re-process it -> the watcher treats a fresh drop as "redo this" (see watcher.py),
  and `run_all_once.py --redo` forces a full rebuild. Re-doing is safe: it just
  overwrites that file's existing row in the Excel.

TWO records live next to config.py:
- processed_index.json : files that were read AND written to the Excel ("done").
- failed_index.json    : files that could NOT be read yet, WITH the reason.
A file only ever sits in one of the two — succeeding clears it from the failed
record, failing adds it there. `write_reupload_report()` turns that failed record
into a plain-English `output/NEEDS_REUPLOAD.txt` the colleague can open to see, at
a glance, exactly which files were not read and what to do about them.

Because files are read ONE AT A TIME and a done file is remembered, the tool never
re-reads what it has already written — that is what keeps repeat runs fast (and, in
the API edition, what stops paying to re-OCR a scanned page it already read).

IMPORTANT: this never moves or deletes your colleague's statement PDFs. The
originals always stay exactly where she put them.
"""
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import List

import config


def file_hash(path) -> str:
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _read_json(path) -> dict:
    if Path(path).exists():
        try:
            return json.loads(Path(path).read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


def _write_json(path, data: dict) -> None:
    Path(path).write_text(json.dumps(data, indent=2), encoding="utf-8")


# --- the "already done" record ----------------------------------------------
def already_processed(path) -> bool:
    return file_hash(path) in _read_json(config.PROCESSED_INDEX)


def mark_processed(path) -> None:
    data = _read_json(config.PROCESSED_INDEX)
    data[file_hash(path)] = {
        "file": Path(path).name,
        "processed_at": datetime.now().isoformat(timespec="seconds"),
    }
    _write_json(config.PROCESSED_INDEX, data)
    # a file that finally reads clean is no longer "needs attention"
    clear_failed(path)


# --- the "still needs attention" record -------------------------------------
def mark_failed(path, reason: str) -> None:
    """Record that this file could not be read, and why. Keyed by content, so a
    re-dropped identical file keeps the same entry, while a corrected copy (new
    content) that reads clean simply never appears here."""
    data = _read_json(config.FAILED_INDEX)
    data[file_hash(path)] = {
        "file": Path(path).name,
        "failed_at": datetime.now().isoformat(timespec="seconds"),
        "reason": reason,
    }
    _write_json(config.FAILED_INDEX, data)


def clear_failed(path) -> None:
    data = _read_json(config.FAILED_INDEX)
    if data.pop(file_hash(path), None) is not None:
        _write_json(config.FAILED_INDEX, data)


def collect_unread(banks) -> List[dict]:
    """Every PDF still sitting in an inbox that is NOT in the processed record —
    i.e. the files that have not been written to the Excel. Reasons come from the
    failed record when we have one. This is computed from the LIVE folders, so a
    file removed from the inbox drops off the list automatically, and a corrected
    file that now reads clean never lingers here."""
    processed = _read_json(config.PROCESSED_INDEX)
    failed = _read_json(config.FAILED_INDEX)
    unread: List[dict] = []
    for bank in banks:
        for pdf in sorted(config.inbox_dir(bank).glob("*.pdf")):
            h = file_hash(pdf)
            if h in processed:
                continue
            reason = (failed.get(h) or {}).get(
                "reason", "not read yet — will be retried on the next run")
            unread.append({"bank": bank, "file": pdf.name, "reason": reason})
    return unread


def write_reupload_report(banks) -> List[dict]:
    """(Re)write output/NEEDS_REUPLOAD.txt from the current inbox state and return
    the list of unread files (empty if everything has been read)."""
    unread = collect_unread(banks)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if not unread:
        _write_report(
            "PINNACLE NAV AUTOMATION — read status\n"
            f"Generated: {now}\n\n"
            "All files in the inbox folders have been read and written to the "
            "Excel.\nThere is nothing to remove or re-upload.\n")
        return unread

    lines = [
        "PINNACLE NAV AUTOMATION — FILES THAT STILL NEED ATTENTION",
        f"Generated: {now}",
        "",
        f"{len(unread)} file(s) in the inbox folders were NOT read, so they are "
        "MISSING from the Excel:",
        "",
    ]
    for u in unread:
        lines.append(f"  [{u['bank']}]  {u['file']}")
        lines.append(f"          why: {u['reason']}")
        lines.append("")
    lines += [
        "WHAT TO DO  (one file at a time):",
        "  1. Open that bank's inbox folder and REMOVE the file(s) listed above.",
        "  2. Fix the cause — e.g. re-download a normal (text-based) copy of the",
        "     statement from the bank portal, close the Excel/Word if it was open,",
        "     or sort out the API key if the reason above mentions it.",
        "  3. Drop the corrected file back into the SAME bank inbox folder.",
        "",
        "The tool reads files ONE AT A TIME and remembers which are already done,",
        "so re-dropping a file only re-reads THAT one file — every row already in",
        "the Excel is left untouched, and files already read are never re-read.",
        "",
    ]
    _write_report("\n".join(lines))
    return unread


def _write_report(text: str) -> None:
    config.NEEDS_REUPLOAD_REPORT.write_text(text, encoding="utf-8")
