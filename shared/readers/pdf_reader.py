"""PDF reader, backed by PyMuPDF (the `fitz` module).

PyMuPDF gives us each word's text AND its exact rectangle on the page. We need
the rectangle so we can later screenshot the precise section a number came from.

OCR fallback (THE Version-2 difference): some PDFs are just pictures of a
statement (a scan, or a page someone screenshotted and re-saved). Those have NO
text layer, so PyMuPDF finds no words. Version 1 read such pages with a local
OCR engine (slow — minutes per statement). This version sends ONLY those
image-only pages to the company's Gemini API instead (seconds per page, no
heavy local install). Pages WITH a text layer — i.e. every normal statement
downloaded from a bank portal — are still read 100% locally and never leave
the machine.
"""
from pathlib import Path
from typing import Dict, List, Optional

import fitz  # PyMuPDF

from shared.logging_setup import get_logger

from .base import StatementReader
from .gemini_ocr import GeminiOcrError, ocr_page_items

log = get_logger("pdf_reader")


class PdfReadError(Exception):
    """The PDF could not be read at all. The message ends up in the Excel
    Flags column for the colleague to act on — keep it plain English."""


def no_text_hint(info: Optional[Dict]) -> str:
    """A flag suffix explaining unreadable pages, for when a parser can't find
    its overview page. Empty string if every page was read fine."""
    pages = (info or {}).get("no_text_pages") or []
    if not pages:
        return ""
    pg = ", ".join(str(p) for p in pages)
    return (f" — note: page {pg} of the PDF is a scanned image that the "
            "Gemini API could not read. Check api_key.txt holds the company "
            "key, then run again; or download a text-based copy of the statement.")


class PdfReader(StatementReader):
    def extract_text_items(self, path, info: Optional[Dict] = None) -> List[Dict]:
        """All words with their rectangles. `info`, if given, is filled with
        `no_text_pages`: 1-based pages that had no text layer AND could not be
        read via the API — so parsers can explain a missing overview page."""
        if info is None:
            info = {}
        info["no_text_pages"] = []
        items: List[Dict] = []
        api_notice_shown = False
        api_error: Optional[GeminiOcrError] = None
        doc = fitz.open(str(path))
        try:
            if doc.needs_pass and not doc.authenticate(""):
                raise PdfReadError(
                    "the PDF is password-protected. Open it in a PDF viewer "
                    "(enter the password), print/save it as a new PDF, and "
                    "drop that unlocked copy into the inbox instead")
            for page_no in range(len(doc)):
                page = doc[page_no]
                # get_text("words") -> list of (x0, y0, x1, y1, "word", block, line, word_no)
                words = page.get_text("words")
                if words:
                    for w in words:
                        items.append({
                            "text": w[4],
                            "page": page_no,
                            "x0": w[0], "y0": w[1], "x1": w[2], "y1": w[3],
                        })
                    continue
                if not api_notice_shown:
                    api_notice_shown = True
                    log.info(f"{Path(str(path)).name} has scanned-image page(s) — "
                             "reading them with the Gemini API (a few seconds "
                             "per page). Screenshots from these pages are "
                             "approximate; the numbers themselves are exact.")
                try:
                    ocr_items = ocr_page_items(page, page_no)
                except GeminiOcrError as e:
                    # A key/network problem will hit every scanned page the
                    # same way — remember it once and stop calling the API.
                    api_error = e
                    log.warning(f"page {page_no + 1} of {path}: {e}")
                    ocr_items = []
                except Exception:
                    log.exception(f"Gemini OCR failed on page {page_no + 1} of "
                                  f"{path} — treating the page as unreadable")
                    ocr_items = []
                if ocr_items:
                    log.info(f"page {page_no + 1} of {path} had no text layer — "
                             "read it through the Gemini API instead")
                    items.extend(ocr_items)
                else:
                    info["no_text_pages"].append(page_no + 1)
                    if api_error is not None:
                        # no point hammering the API for the remaining pages
                        for later in range(page_no + 1, len(doc)):
                            if not doc[later].get_text("words"):
                                info["no_text_pages"].append(later + 1)
                        break
        finally:
            doc.close()
        if not items:
            if api_error is not None:
                raise PdfReadError(str(api_error))
            raise PdfReadError(
                "no readable text found in this PDF — it looks like a scanned "
                "image that even the Gemini API could not read. Try "
                "re-downloading the original statement from the bank portal")
        return items

    def full_text(self, path) -> str:
        doc = fitz.open(str(path))
        try:
            return "\n".join(page.get_text() for page in doc)
        finally:
            doc.close()
