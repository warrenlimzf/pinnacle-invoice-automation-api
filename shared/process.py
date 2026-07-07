"""The glue: process ONE statement PDF end-to-end for a given bank.

  parse -> write Excel row -> screenshot each value's section -> paste into docx

Called by both the watcher and the manual 'run once' script.
"""
import importlib
from pathlib import Path
from typing import List

import config
from shared.docx_writer import append_verification
from shared.excel_writer import write_result
from shared.logging_setup import get_logger
from shared.model import ClientResult
from shared.readers.pdf_reader import PdfReadError
from shared.snapshot import snapshot_region

log = get_logger("process")


def _bank_parser(bank: str):
    return importlib.import_module(f"banks.{bank}.parser")


def process_pdf(bank: str, pdf_path) -> List[ClientResult]:
    pdf_path = Path(pdf_path)
    # A parser crash must never leave the Excel silently empty — write a FAILED
    # row instead, so the colleague sees the file AND the reason in one place.
    try:
        results: List[ClientResult] = _bank_parser(bank).parse(pdf_path)
    except Exception as exc:
        log.exception(f"[{bank}] failed to read {pdf_path.name}")
        reason = (str(exc) if isinstance(exc, PdfReadError)
                  else f"unexpected error ({type(exc).__name__}: {exc})")
        res = ClientResult(source_pdf=str(pdf_path), failed=True)
        res.flags.append(f"FAILED — {reason}. Fix that, then simply run again — "
                         "failed files are retried automatically.")
        results = [res]
    snap_dir = config.SNAPSHOT_DIR / bank

    for res in results:
        images = []
        for hit in res.hits:
            safe = "".join(c if c.isalnum() else "_" for c in hit.label)[:30]
            png = snap_dir / f"{pdf_path.stem}__{safe}.png"
            try:
                snapshot_region(pdf_path, hit.page, hit.bbox, png)
                images.append((hit, png))
            except Exception:
                log.exception(f"[{bank}] screenshot failed for {hit.label}")

        page = (res.hits[0].page + 1) if res.hits else ""
        write_result(config.MASTER_WORKBOOK, bank, config.BANKS, res, page)
        append_verification(config.verification_docx(bank), res, images, pdf_path)

        flag_note = f"  FLAGS: {'; '.join(res.flags)}" if res.flags else ""
        log.info(f"[{bank}] {pdf_path.name}: gross={res.gross_nav} net={res.net_nav} "
                 f"addbacks={len(res.addbacks)}{flag_note}")

    return results
