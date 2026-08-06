"""UBS printed-layout regression tests — synthetic PDFs only, no client data.

Run: python tests/test_ubs_layouts.py   (any machine, no samples/ required)

UBS changed the "Total assets" overview page with the June 2026 statements.
Both layouts are still in circulation, so both must keep working:

  CLASSIC (to May 2026)     Asset class | Market value | Accrued interest | Total | % GA
  2026-06                   Asset class | % GA | Total          + a second
                            "Net Performance" table printed to the RIGHT, on
                            the same rows

The new layout breaks two old assumptions, and this file pins both fixes:
  1. "the first number on the row" is now the PERCENTAGE, not the money.
  2. the right-hand table's numbers sit on the same rows as the money column.
It also covers the two awkward details of the real June statement: the
"Net assets" row carries NO percentage, and OCR can print its bold total a few
points below its label (so label and value arrive as two text lines).

The last test replays the same page through the geometry the API version's
Gemini reader synthesises (cells laid left to right from the page margin,
positions NOT true to the page) — proof the fix does not secretly depend on
real coordinates, i.e. that it works in the API version too.
"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import fitz

from banks.UBS.parser import parse
from shared.readers import pdf_reader

# Landscape A4, like the real statement page.
PAGE = fitz.paper_rect("a4-l")

# Invented figures with the SHAPE that matters: money in whole currency units,
# percentages with two decimals, and Gross + Liabilities = Net.
LIQUIDITY = 2_400_000
GROSS = 14_600_000
LIABILITIES = -2_600_000
NET = 12_000_000


def _tmp() -> Path:
    return Path(tempfile.mkdtemp(prefix="pinnacle_ubs_layout_"))


def _write(page, x, y, text, size=8):
    page.insert_text((x, y), text, fontsize=size)


# --------------------------------------------------------------------------- #
#  2026-06 layout, drawn at true page coordinates
# --------------------------------------------------------------------------- #
def _new_layout_pdf(path: Path) -> None:
    doc = fitz.open()
    page = doc.new_page(width=PAGE.width, height=PAGE.height)

    _write(page, 40, 30, "Total assets", size=16)
    _write(page, 420, 30, "Portfolio number 546-123456-03")
    _write(page, 420, 50, "Statement of assets as of 30 June 2026")
    _write(page, 40, 55, "For your Banking relationship 546-123456 - valued in USD")

    _write(page, 40, 110, "Portfolio 03")
    # left-hand asset-class table: label, % GA (2 decimals), money (whole units)
    left = [
        (130, "Asset class", "% GA", "Total"),
        (146, "Liquidity", "16.44", "2 400 000"),
        (160, "Bonds", "28.08", "4 100 000"),
        (174, "Equities", "49.32", "7 200 000"),
        (188, "Hedge funds & private markets", "6.16", "900 000"),
        (204, "Gross assets", "100.00", "14 600 000"),
        (216, "Liabilities", "-17.81", "-2 600 000"),
    ]
    for y, label, pct, money in left:
        _write(page, 40, y, label)
        _write(page, 270, y, pct)
        _write(page, 355, y, money)
    # "Net assets" has NO percentage, and its bold total is printed 3 pt lower
    # than the label — exactly what the real scan does.
    _write(page, 40, 231, "Net assets")
    _write(page, 355, 234, "12 000 000")

    # right-hand "Net Performance" table, on the SAME rows as the money column
    right = [
        (130, "Net Performance valued in USD", "", ""),
        (146, "Period", "Performance", "TWR"),
        (160, "Current year", "500 000", "4.29%"),
        (174, "Previous year", "1 600 000", "15.63%"),
        (188, "Since 31.12.2013", "4 500 000", "84.50%"),
        (216, "Previous year", "", "Current year"),
        (231, "Starting value", "10 000 000", "11 500 000"),
        (245, "Total inflows/outflows", "400 000", "-80 000"),
        (258, "End value", "11 500 000", "12 000 000"),
    ]
    for y, a, b, c in right:
        _write(page, 422, y, a)
        if b:
            _write(page, 610, y, b)
        if c:
            _write(page, 740, y, c)

    # a second portfolio further down, so the section cut is exercised
    _write(page, 40, 290, "Portfolio 01")
    _write(page, 40, 322, "Liquidity")
    _write(page, 270, 322, "100.00")
    _write(page, 390, 322, "88")
    _write(page, 40, 338, "Net assets")
    _write(page, 270, 338, "100.00")
    _write(page, 390, 338, "88")

    doc.save(str(path))
    doc.close()


def test_new_layout_reads_the_total_column(tmp: Path) -> None:
    pdf = tmp / "ubs_2026_06.pdf"
    _new_layout_pdf(pdf)
    res = parse(pdf)[0]
    assert res.account_no == "546-123456-03", res.account_no
    assert res.currency == "USD", res.currency
    assert res.statement_date == "30 June 2026", res.statement_date
    assert res.liquidity == LIQUIDITY, res.liquidity
    assert res.gross_nav == GROSS, res.gross_nav
    assert res.liabilities == LIABILITIES, res.liabilities
    assert res.net_nav == NET, res.net_nav
    assert res.gross_nav + res.liabilities == res.net_nav
    assert not res.flags, res.flags
    print("PASS  UBS 2026-06 layout -> Total column read, percentages ignored")


def test_new_layout_picks_the_named_portfolio(tmp: Path) -> None:
    """Portfolio 01 is the second table on the same page and has no liabilities:
    its Net assets row must be read, and Gross must fall back to a formula."""
    pdf = tmp / "ubs_2026_06_p01.pdf"
    _new_layout_pdf(pdf)
    doc = fitz.open(str(pdf))                    # re-label the header to -01
    page = doc[0]
    for rect in page.search_for("546-123456-03"):
        page.add_redact_annot(rect, "546-123456-01", fontsize=8)
    page.apply_redactions()
    swapped = tmp / "ubs_2026_06_p01_final.pdf"
    doc.save(str(swapped))
    doc.close()

    res = parse(swapped)[0]
    assert res.account_no == "546-123456-01", res.account_no
    assert res.net_nav == 88, res.net_nav
    assert res.liquidity == 88, res.liquidity
    assert res.gross_is_formula, "Gross should be a =Net formula here"
    print("PASS  UBS 2026-06 layout -> right portfolio table selected")


# --------------------------------------------------------------------------- #
#  Classic layout must not regress
# --------------------------------------------------------------------------- #
def test_classic_layout_still_reads_market_value(tmp: Path) -> None:
    pdf = tmp / "ubs_classic.pdf"
    doc = fitz.open()
    page = doc.new_page(width=PAGE.width, height=PAGE.height)
    _write(page, 40, 30, "Total assets", size=16)
    _write(page, 420, 30, "Portfolio number 546-123456-03")
    _write(page, 40, 55, "Banking relationship 546-123456 - Valued in USD")
    _write(page, 40, 105, "Total gross assets as of 31.03.2026")
    _write(page, 430, 105, "USD 16 400 000")
    _write(page, 40, 118, "Total net assets as of 31.03.2026")
    _write(page, 430, 118, "USD 11 600 000")
    _write(page, 40, 150, "Portfolio 03")
    rows = [
        (172, "Asset class", "Market value", "Accrued interest", "Total", "% GA"),
        (182, "Liquidity", "2 800 000", "1 500", "2 801 500", "19.29"),
        (193, "Bonds", "4 600 000", "", "4 600 000", "30.93"),
        (227, "Gross assets", "14 800 000", "1 500", "14 801 500", "100.00"),
        (238, "Liabilities", "-2 800 000", "-1 200", "-2 801 200", "-18.96"),
        (250, "Net assets", "12 000 000", "300", "12 000 300", ""),
    ]
    for y, label, mv, ai, total, pct in rows:
        _write(page, 40, y, label)
        _write(page, 280, y, mv)
        if ai:
            _write(page, 370, y, ai)
        _write(page, 432, y, total)
        if pct:
            _write(page, 500, y, pct)
    doc.save(str(pdf))
    doc.close()

    res = parse(pdf)[0]
    # the supervisor's rule: the Market value column, NOT Total, NOT the
    # whole-relationship header block
    assert res.gross_nav == 14_800_000, res.gross_nav
    assert res.net_nav == 12_000_000, res.net_nav
    assert res.liquidity == 2_800_000, res.liquidity
    assert res.liabilities == -2_800_000, res.liabilities
    print("PASS  UBS classic layout -> Market value column unchanged")


# --------------------------------------------------------------------------- #
#  The same new-layout page as the API version's reader hands it over
# --------------------------------------------------------------------------- #
# Mirrors shared/readers/gemini_ocr.py: cells are laid out left to right from
# the page margin at a fixed character width, so x positions carry column ORDER
# but not true page geometry, and one visual row = one transcribed line.
_CHAR_W, _CELL_GAP, _LEFT_MARGIN, _LINE_H = 5.0, 24.0, 36.0, 9.0

_GEMINI_ROWS = [
    ["Total assets", "Portfolio number 546-123456-03"],
    ["Statement of assets as of 30 June 2026"],
    ["For your Banking relationship 546-123456 - valued in USD"],
    ["Portfolio 03"],
    ["Asset class", "% GA", "Total", "Net Performance valued in USD"],
    ["Liquidity", "16.44", "2 400 000", "Period", "Performance", "TWR"],
    ["Bonds", "28.08", "4 100 000", "Current year", "500 000", "4.29%"],
    ["Equities", "49.32", "7 200 000", "Previous year", "1 600 000", "15.63%"],
    ["Hedge funds & private markets", "6.16", "900 000", "Since 31.12.2013",
     "4 500 000", "84.50%"],
    ["Gross assets", "100.00", "14 600 000"],
    ["Liabilities", "-17.81", "-2 600 000", "Previous year", "Current year"],
    ["Net assets", "12 000 000", "Starting value", "10 000 000", "11 500 000"],
    ["Total inflows/outflows", "400 000", "-80 000"],
    ["End value", "11 500 000", "12 000 000"],
    ["Portfolio 01"],
    ["Asset class", "% NA", "Total", "Net Performance valued in USD"],
    ["Liquidity", "100.00", "88", "Period", "Performance", "TWR"],
    ["Net assets", "100.00", "88", "Current year", "-1", "-1.12%"],
]


def _gemini_items(_self, path, info=None):
    if info is not None:
        info["no_text_pages"] = []
    items = []
    for row, cells in enumerate(_GEMINI_ROWS):
        y0 = 60.0 + row * 12.0
        cursor = _LEFT_MARGIN
        for cell in cells:
            for word in cell.split():
                w = _CHAR_W * len(word)
                items.append({"text": word, "page": 0, "x0": cursor, "y0": y0,
                              "x1": cursor + w, "y1": y0 + _LINE_H})
                cursor += w + _CHAR_W
            cursor += _CELL_GAP
    return items


def test_new_layout_through_api_reader_geometry(tmp: Path) -> None:
    original = pdf_reader.PdfReader.extract_text_items
    pdf_reader.PdfReader.extract_text_items = _gemini_items
    try:
        res = parse(tmp / "does_not_matter.pdf")[0]
    finally:
        pdf_reader.PdfReader.extract_text_items = original

    assert res.account_no == "546-123456-03", res.account_no
    assert res.currency == "USD", res.currency
    assert res.liquidity == LIQUIDITY, res.liquidity
    assert res.gross_nav == GROSS, res.gross_nav
    assert res.liabilities == LIABILITIES, res.liabilities
    assert res.net_nav == NET, res.net_nav
    assert not res.flags, res.flags
    print("PASS  UBS 2026-06 layout -> correct through API-reader geometry too")


def main() -> None:
    failures = 0
    for test in (test_new_layout_reads_the_total_column,
                 test_new_layout_picks_the_named_portfolio,
                 test_classic_layout_still_reads_market_value,
                 test_new_layout_through_api_reader_geometry):
        try:
            test(_tmp())
        except Exception as exc:
            failures += 1
            print(f"FAIL  {test.__name__}: {type(exc).__name__}: {exc}")
    if failures:
        sys.exit(f"{failures} UBS layout test(s) failed")
    print("All UBS layout tests passed.")


if __name__ == "__main__":
    main()
