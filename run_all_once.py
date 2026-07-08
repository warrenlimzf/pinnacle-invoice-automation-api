"""Manual fallback: process every PDF currently in the inbox folders, once, then exit.

Use this when you'd rather run on demand than leave the watcher running, or to
re-run a batch. Already-processed files (same content) are skipped automatically.

  python run_all_once.py            # process all three banks
  python run_all_once.py LGT        # process only one bank
  python run_all_once.py --redo     # re-do EVERYTHING, even already-processed
  python run_all_once.py LGT --redo # re-do just one bank

Use --redo if you deleted rows in the Excel by mistake and want them rebuilt
from the PDFs still sitting in the inbox folders.
"""
import sys

import config
from shared.index import (already_processed, mark_processed, mark_failed,
                          write_reupload_report)
from shared.logging_setup import get_logger
from shared.process import process_pdf

log = get_logger("run_all_once")


def main(argv):
    config.ensure_api_key_file()   # so there's always a file to paste the key into
    redo = "--redo" in argv
    banks = [b for b in argv if b in config.BANKS] or config.BANKS
    done = 0
    failed = 0
    for bank in banks:
        for pdf in sorted(config.inbox_dir(bank).glob("*.pdf")):
            if not redo and already_processed(pdf):
                log.info(f"[{bank}] skip (already processed): {pdf.name}")
                continue
            try:
                log.info(f"[{bank}] processing {pdf.name}")
                results = process_pdf(bank, pdf)
                if any(r.failed for r in results):
                    # record why + leave it un-marked so it is retried next run
                    reason = _failure_reason(results)
                    mark_failed(pdf, reason)
                    failed += 1
                    log.error(f"[{bank}] {pdf.name} could not be read — {reason}")
                else:
                    mark_processed(pdf)   # also clears any earlier failure record
                    done += 1
            except PermissionError:
                mark_failed(pdf, "the Excel or Word output was open, so nothing "
                                 "could be written — close it and run again")
                failed += 1
                log.error(f"[{bank}] Close the Excel/Word file first, then re-run. ({pdf.name})")
            except Exception as exc:
                mark_failed(pdf, f"unexpected error ({type(exc).__name__}: {exc})")
                failed += 1
                log.exception(f"[{bank}] FAILED: {pdf.name}")

    # regenerate the plain-English "which files still need attention" report
    unread = write_reupload_report(config.BANKS)
    log.info(f"Done. {done} file(s) read and written; {failed} could not be read this run.")
    if unread:
        log.warning(f"{len(unread)} file(s) are NOT in the Excel. What to remove and "
                    f"re-upload is written in: {config.NEEDS_REUPLOAD_REPORT}")
        for u in unread:
            log.warning(f"   NOT READ  [{u['bank']}]  {u['file']}  —  {u['reason']}")


def _failure_reason(results) -> str:
    """The plainest available explanation from a failed file's flags."""
    flags = [f for r in results if getattr(r, "failed", False) for f in r.flags]
    return "; ".join(flags) if flags else "could not be read"


if __name__ == "__main__":
    main(sys.argv[1:])
