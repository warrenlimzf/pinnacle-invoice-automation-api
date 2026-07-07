"""Diagnostic dump — writes the text the tool actually SEES in each inbox PDF.

Use when a statement extracts wrongly (blank cells, wrong figure, FAILED row):
run this, then send Warren the .txt file for the problem statement so the parser
can be fixed against the real wording instead of guesses.

  python diagnose.py            # dump every PDF in all three inboxes
  python diagnose.py UBS        # just one bank (faster — scans OCR slowly)

Output: logs/diagnose/<bank>__<pdf name>.txt — one line of text per visual line
of the statement, page by page. These files contain client data: they stay on
this computer and are only ever shared person-to-person inside the firm.
"""
import sys

import config
from shared.extract import group_lines
from shared.logging_setup import get_logger
from shared.readers.pdf_reader import PdfReader

log = get_logger("diagnose")


def main(argv):
    banks = [b for b in argv if b in config.BANKS] or config.BANKS
    out_dir = config.LOGS_DIR / "diagnose"
    out_dir.mkdir(parents=True, exist_ok=True)
    wrote = 0
    for bank in banks:
        for pdf in sorted(config.inbox_dir(bank).glob("*.pdf")):
            out = out_dir / f"{bank}__{pdf.stem}.txt"
            log.info(f"[{bank}] dumping {pdf.name} (scanned pages OCR at ~10s/page)")
            try:
                lines = group_lines(PdfReader().extract_text_items(pdf))
            except Exception as exc:
                out.write_text(f"READ FAILED: {exc}\n", encoding="utf-8")
                log.error(f"[{bank}] {pdf.name}: READ FAILED — {exc}")
                wrote += 1
                continue
            with out.open("w", encoding="utf-8") as f:
                cur_page = None
                for ln in lines:
                    if ln["page"] != cur_page:
                        cur_page = ln["page"]
                        f.write(f"\n===== page {cur_page + 1} =====\n")
                    f.write(ln["text"] + "\n")
            log.info(f"[{bank}] wrote {out}")
            wrote += 1
    log.info(f"Done — {wrote} dump(s) in {out_dir}. Send the .txt of the "
             "problem statement(s) to Warren.")


if __name__ == "__main__":
    main(sys.argv[1:])
