"""Takes a screenshot of a SECTION of a PDF page, fully offline (PyMuPDF).

Given the page and the rectangle where a number was found, render just that
region (plus a little padding) to a PNG. This is the visual that gets pasted
into the Word doc so a human can eyeball it against the Excel.
"""
from pathlib import Path

import fitz  # PyMuPDF

import config


def snapshot_region(pdf_path, page_no: int, bbox, out_png,
                    dpi: int = None, padding: float = None) -> Path:
    """Render region `bbox` (x0,y0,x1,y1 in PDF points) of `page_no` to `out_png`."""
    dpi = config.SNAPSHOT_DPI if dpi is None else dpi
    padding = config.SNAPSHOT_PADDING if padding is None else padding

    doc = fitz.open(str(pdf_path))
    try:
        page = doc[page_no]
        rect = fitz.Rect(*bbox)
        # pad around the value for context, then clip to the page bounds
        rect = fitz.Rect(rect.x0 - padding, rect.y0 - padding,
                         rect.x1 + padding, rect.y1 + padding)
        rect = rect & page.rect

        zoom = dpi / 72.0
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), clip=rect)

        out_png = Path(out_png)
        out_png.parent.mkdir(parents=True, exist_ok=True)
        pix.save(str(out_png))
        return out_png
    finally:
        doc.close()
