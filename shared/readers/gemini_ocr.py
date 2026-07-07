"""Cloud OCR for scanned pages, backed by the company's Gemini API key.

This is the ONE module that talks to the internet. It is only ever called for
pages that have NO text layer (scans / photographed statements). Normal bank
portal PDFs contain selectable text and are read fully locally by PyMuPDF,
exactly like Version 1 — they never touch this file.

How it works, in plain English:
  1. The image-only page is rendered to a PNG (locally, by PyMuPDF).
  2. The PNG goes to Google's Gemini model with a transcription prompt.
  3. Gemini sends back JSON: every visible text line, top-to-bottom, plus an
     estimate of how far down the page each line sits (0-100%).
  4. We turn those lines back into positioned "word items" — the same shape
     the local reader produces — so the bank parsers don't know or care that
     the page came through the API.

Uses only Python's standard library (urllib) — no extra packages to install.
"""
import base64
import json
import time
import urllib.error
import urllib.request
from typing import Dict, List

import fitz  # PyMuPDF — used only to render the page image locally

import config
from shared.logging_setup import get_logger

log = get_logger("gemini_ocr")

_ENDPOINT = ("https://generativelanguage.googleapis.com/v1beta/models/"
             "{model}:generateContent")

_PROMPT = """You are transcribing one page of a bank client statement for an accounting tool.

Return ONLY a JSON object of this exact shape:
{"lines": [{"y": <number 0-100>, "cells": ["<text>", "<text>", ...]}, ...]}

Rules:
- Transcribe EVERY visible line of text, top to bottom. One entry per visual row.
- "cells" = the visually separate blocks of that row, left to right: a row's
  text label is one cell, and EACH printed number / column value is its OWN
  cell. A row of plain sentence text is just one cell. NEVER put two different
  column values into the same cell.
- Copy each cell character-for-character: keep thousand separators (spaces,
  commas or apostrophes), decimal points, minus signs and parentheses.
- "y" is the row's vertical position as a percentage of the page height
  (0 = top edge, 100 = bottom edge). Estimate it as accurately as you can.
- Do not translate, summarise, correct, or add anything. No markdown fences.
"""

_RENDER_DPI = 200          # PNG resolution sent to the API; 200 reads bank tables fine
_TIMEOUT_S = 120           # one page should never take longer than this
_RETRY_STATUSES = {429, 500, 503}
_RETRY_WAITS = (3, 8)      # seconds between attempts (2 retries = 3 tries total)

# Synthetic geometry for the items we hand back (PDF points).
# Small fixed character width keeps space-separated thousand groups WITHIN a
# cell close enough for the parsers to merge them back into one number
# (gap < 12 pt), while the big gap BETWEEN cells stops a merge from ever
# running across a column boundary and gluing two different values together.
_CHAR_W = 5.0
_CELL_GAP = 24.0
_LEFT_MARGIN = 36.0
_LINE_H = 9.0
_MIN_LINE_GAP = 6.0        # keep synthetic lines apart so they never merge


class GeminiOcrError(Exception):
    """Raised when the API cannot be used. The message is written into the
    Excel Flags column for the colleague to act on — keep it plain English."""


def _api_key() -> str:
    key = config.get_gemini_api_key()
    if not key:
        raise GeminiOcrError(
            "this PDF contains scanned-image pages, which are read through the "
            "Gemini API — but no API key is set. Open api_key.txt (in the tool's "
            "folder), replace the placeholder with the company's Gemini API key, "
            "save, and run again")
    return key


def _call_gemini(png_bytes: bytes, key: str) -> str:
    """One page image -> Gemini -> the raw JSON text it returned."""
    body = json.dumps({
        "contents": [{"parts": [
            {"text": _PROMPT},
            {"inline_data": {"mime_type": "image/png",
                             "data": base64.b64encode(png_bytes).decode("ascii")}},
        ]}],
        "generationConfig": {"temperature": 0,
                             "response_mime_type": "application/json"},
    }).encode("utf-8")

    url = _ENDPOINT.format(model=config.GEMINI_MODEL)
    last_err = None
    for attempt in range(len(_RETRY_WAITS) + 1):
        req = urllib.request.Request(
            url, data=body,
            headers={"Content-Type": "application/json", "x-goog-api-key": key},
            method="POST")
        try:
            with urllib.request.urlopen(req, timeout=_TIMEOUT_S) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            try:
                return payload["candidates"][0]["content"]["parts"][0]["text"]
            except (KeyError, IndexError, TypeError):
                raise GeminiOcrError(
                    "the Gemini API answered but sent no text back (the page "
                    "may have been blocked by a safety filter). Try again, or "
                    "download a text-based copy of the statement")
        except urllib.error.HTTPError as e:
            detail = ""
            try:
                detail = e.read().decode("utf-8", "replace")[:300]
            except Exception:
                pass
            if e.code in (400, 401, 403):
                raise GeminiOcrError(
                    "the Gemini API rejected the key (HTTP "
                    f"{e.code}). Open api_key.txt, check the key was pasted "
                    "completely with no extra spaces, and that the company "
                    f"subscription is active. API said: {detail}")
            if e.code in _RETRY_STATUSES and attempt < len(_RETRY_WAITS):
                wait = _RETRY_WAITS[attempt]
                log.warning(f"Gemini API busy (HTTP {e.code}) — retrying in {wait}s...")
                time.sleep(wait)
                last_err = e
                continue
            raise GeminiOcrError(
                f"the Gemini API returned an error (HTTP {e.code}) even after "
                f"retrying. Wait a minute and run again. API said: {detail}")
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            if attempt < len(_RETRY_WAITS):
                wait = _RETRY_WAITS[attempt]
                log.warning(f"network problem talking to the Gemini API ({e}) — "
                            f"retrying in {wait}s...")
                time.sleep(wait)
                last_err = e
                continue
            raise GeminiOcrError(
                "could not reach the Gemini API — check the internet "
                f"connection and run again (network error: {e})")
    raise GeminiOcrError(f"the Gemini API kept failing: {last_err}")


def _parse_lines(raw: str) -> List[Dict]:
    """Gemini's JSON -> [{'y': float, 'cells': [str, ...]}, ...], defensively.
    Accepts a plain 'text' string per line too, in case the model ignores the
    cells instruction — that becomes a single cell."""
    s = raw.strip()
    if s.startswith("```"):                       # strip a stray markdown fence
        s = s.strip("`")
        s = s[s.find("{"):]
    data = json.loads(s)
    lines = []
    for i, ln in enumerate(data.get("lines") or []):
        raw_cells = ln.get("cells")
        if isinstance(raw_cells, list):
            cells = [str(c).strip() for c in raw_cells if str(c).strip()]
        else:
            cells = [str(ln.get("text") or "").strip()]
        cells = [c for c in cells if c]
        if not cells:
            continue
        try:
            y = float(ln.get("y"))
        except (TypeError, ValueError):
            y = -1.0
        lines.append({"y": y, "cells": cells, "order": i})
    # Missing/broken y estimates: spread those lines evenly in reading order.
    if lines and any(l["y"] < 0 or l["y"] > 100 for l in lines):
        for l in lines:
            l["y"] = (l["order"] + 1) * 100.0 / (len(lines) + 1)
    lines.sort(key=lambda l: (l["y"], l["order"]))
    return lines


def ocr_page_items(page, page_no: int) -> List[Dict]:
    """OCR one image-only page via the Gemini API; return word items in the
    same {'text','page','x0','y0','x1','y1'} shape the local reader emits.

    Coordinates are SYNTHESIZED from Gemini's per-line position estimates, so
    section screenshots taken from scanned pages are approximate (the crop is
    centred near the right row, not pixel-exact). Values themselves are exact.
    """
    key = _api_key()
    zoom = _RENDER_DPI / 72.0
    png = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom)).tobytes("png")
    raw = _call_gemini(png, key)
    try:
        lines = _parse_lines(raw)
    except (json.JSONDecodeError, AttributeError, TypeError) as e:
        raise GeminiOcrError(
            "the Gemini API replied in an unexpected format for page "
            f"{page_no + 1} — run again; if it keeps happening, the model name "
            f"in config.py may need updating ({e})")

    page_h = float(page.rect.height) or 842.0
    items: List[Dict] = []
    prev_y = None
    for ln in lines:
        y0 = ln["y"] / 100.0 * page_h
        if prev_y is not None and y0 < prev_y + _MIN_LINE_GAP:
            y0 = prev_y + _MIN_LINE_GAP        # never let two rows merge
        prev_y = y0
        cursor = _LEFT_MARGIN
        for cell in ln["cells"]:
            for word in cell.split():
                w = _CHAR_W * len(word)
                items.append({"text": word, "page": page_no,
                              "x0": cursor, "y0": y0,
                              "x1": cursor + w, "y1": y0 + _LINE_H})
                cursor += w + _CHAR_W          # one space between words
            cursor += _CELL_GAP                # column boundary: break merges
    return items
