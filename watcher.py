"""Folder watcher — the automatic trigger.

Keep this running (double-click run_watcher.bat on Windows). It watches the three
inbox folders. The moment a PDF appears in one, it processes it for that bank.

It also processes any PDFs already sitting in the inboxes when it starts, so
nothing is missed if files were dropped while it was off.

Stop it with Ctrl+C (or just close the window).
"""
import time
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

import config
from shared.index import already_processed, mark_processed
from shared.logging_setup import get_logger
from shared.process import process_pdf

log = get_logger("watcher")


def _wait_until_stable(path: Path, tries: int = 20, interval: float = 0.5) -> bool:
    """Wait until the file size stops changing, i.e. the copy/download finished."""
    last = -1
    for _ in range(tries):
        try:
            size = path.stat().st_size
        except FileNotFoundError:
            return False
        if size == last and size > 0:
            return True
        last = size
        time.sleep(interval)
    return True


def handle(bank: str, path: Path, force: bool = False) -> None:
    """Process one PDF.

    force=True means "re-do this even if we've seen it before" — used when a file
    is freshly dropped into an inbox (a brand-new file, OR the colleague deleted a
    PDF and copied it back in to re-do a row she removed from the Excel by mistake).
    Re-processing is safe: it just overwrites that file's existing row in the Excel.

    force=False (catch-up at startup, or routine file-modified events) respects the
    processed-index so we don't needlessly redo the same files on every restart.
    """
    path = Path(path)
    if path.suffix.lower() != ".pdf":
        return
    if not _wait_until_stable(path):
        return
    if not force and already_processed(path):
        log.info(f"[{bank}] skip (already processed): {path.name}")
        return
    try:
        log.info(f"[{bank}] processing {path.name}")
        results = process_pdf(bank, path)
        if any(r.failed for r in results):
            # leave it un-marked so it is retried automatically next time
            log.error(f"[{bank}] {path.name} could not be read — see the "
                      "Flags column in the Excel for what to do")
            return
        mark_processed(path)
        log.info(f"[{bank}] done: {path.name}")
    except PermissionError:
        log.error(f"[{bank}] Excel/Word file is open — close {config.MASTER_WORKBOOK.name} "
                  f"(and the {bank} .docx) and re-drop the PDF.")
    except Exception:
        log.exception(f"[{bank}] FAILED: {path.name}")


class BankHandler(FileSystemEventHandler):
    def __init__(self, bank: str):
        self.bank = bank

    def on_created(self, event):
        # A newly-dropped (or re-dropped) file: always (re)process it.
        if not event.is_directory:
            handle(self.bank, Path(event.src_path), force=True)

    def on_modified(self, event):
        # Routine touch/modify: respect the index so we don't redo on every event.
        if not event.is_directory:
            handle(self.bank, Path(event.src_path))


def main():
    config.ensure_api_key_file()   # so there's always a file to paste the key into
    observer = Observer()
    for bank in config.BANKS:
        inbox = config.inbox_dir(bank)
        inbox.mkdir(parents=True, exist_ok=True)
        observer.schedule(BankHandler(bank), str(inbox), recursive=False)
        log.info(f"Watching: {inbox}")

    # catch up on anything already waiting
    for bank in config.BANKS:
        for pdf in sorted(config.inbox_dir(bank).glob("*.pdf")):
            handle(bank, pdf)

    observer.start()
    log.info("Watcher running. Drop statement PDFs into the bank inbox folders. "
             "Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log.info("Stopping watcher...")
        observer.stop()
    observer.join()


if __name__ == "__main__":
    main()
