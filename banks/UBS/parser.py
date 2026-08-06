"""UBS statement parser.

The overview page is titled "Total assets" and carries, top-centre,
    Portfolio number 546-123456-03
The suffix after the LAST dash ("-03") names WHICH portfolio table to read —
UBS bundles several portfolios (Portfolio 01, 02, 03...) into one statement,
and only the suffixed one is the client's account for our purposes.

TWO PRINTED LAYOUTS ARE SUPPORTED. UBS changed the page with the June 2026
statements; both are still in circulation, so both are read.

CLASSIC layout (validated on the March 2026 sample, 49-page statement) — the
header block carries whole-relationship totals, and the asset-class table has
four numeric columns (figures below are illustrative, not a real statement):
    Total gross assets as of 31.03.2026            USD 16 400 000
    Total net assets as of 31.03.2026              USD 11 600 000
    Portfolio 03
    Asset class      Market value  Accrued interest  Total       % GA
    Liquidity        2 800 000     1 500             2 801 500   19.30
    Gross assets    14 800 000     1 500            14 801 500  100.00
    Liabilities     -2 800 000    -1 200            -2 801 200  -18.90
    Net assets      12 000 000       300            12 000 300
The supervisor's rule is to read the MARKET VALUE column (the first money
column). The header's "Total gross/net assets" cover the WHOLE relationship
(all portfolios), so they are never used when a portfolio table exists.

2026-06 layout (validated on the June 2026 sample, 52-page statement; figures
below are illustrative) — the
whole-relationship header block is GONE, "Market value" and "Accrued interest"
are GONE, the percentage column moved to the FRONT, and a "Net Performance"
table now sits to the RIGHT of the asset-class table on the same rows:
    Portfolio 03
    Asset class                    % GA        Total  | Net Performance valued in USD
    Liquidity                     16.44    2 400 000  | Period   Performance    TWR
    Gross assets                 100.00   14 600 000  | ...
    Liabilities                  -17.81   -2 600 000  | ...
    Net assets                            12 000 000  | Starting value  ...  ...
Reading "the first number on the row" would now return the PERCENTAGE, and the
right-hand table's numbers land on the same rows, so the money column is picked
by two layout-independent facts instead of by position:
  1. UBS prints money on this page in WHOLE currency units (2 400 000) and
     percentages with two decimals (16.44, 100.00, -17.81) — so any number with
     a decimal point is a percentage and is ignored (`looks_like_percent`).
  2. The asset-class table is the LEFT-HAND one, so of the remaining numbers
     the LEFTMOST is the money figure — anything from the right-hand table sits
     further right.
Neither fact depends on page coordinates, which matters because the API version
reads scans through a model whose coordinates carry column ORDER but not true
positions. As a backstop, Gross + Liabilities = Net is verified below.
That rule reproduces the supervisor's Market value column on the classic layout
(it is the leftmost money column there too) and the Total column on the new one.
Note the "Net assets" row often has no percentage at all, and OCR can print its
bold total a few points below its label — `amounts_on_row` sweeps a small
vertical window so the label and its value are read as one row.

Numbers use SPACES as thousand separators. Some portfolios have no liabilities
and therefore no "Gross assets" row — then Gross = Net, written into Excel as a
formula (=Net cell) so the derivation is auditable.

Also extracted: account no (the full portfolio number), currency ("valued in
USD"), statement date, Liquidity, and Liabilities (which powers the same
Gross + Liabilities - Net = 0 check column as BoS). That identity is also
checked here, so a mis-read column shows up as a flag instead of a wrong number.

UBS ALSO exports ONE PDF PER PORTFOLIO (seen on the colleague's real files,
2026-07-07: e.g. `...0002`/`...0003` files for portfolios -02/-03). Those carry
the same asset-class table(s) on the overview page but with NO "Portfolio NN"
headings — and the client's own portfolio (the one the suffix names) is always
printed FIRST. So when the heading is missing, the parser reads the FIRST
table only (everything up to the first "Net assets" row, so rows are never
mixed across tables) and flags it for the eyeball check when several tables
share the page.
"""
import re
from typing import List, Optional

from shared.extract import (amounts_on_row, find_row_norm, first_amount,
                            group_lines, looks_like_percent, norm, page_of,
                            search_norm, union_bbox)
from shared.model import ClientResult, FieldHit
from shared.readers.pdf_reader import PdfReader, no_text_hint


def parse(pdf_path) -> List[ClientResult]:
    read_info = {}
    all_lines = group_lines(PdfReader().extract_text_items(pdf_path, read_info))
    res = ClientResult(source_pdf=str(pdf_path))

    # ---- find the overview page in a multi-page statement -------------------
    # "Gross assets" only exists when the portfolio has liabilities, and the
    # 2026-06 layout dropped the "Total gross assets" header line — so fall
    # back to the one row every layout always prints, "Net assets".
    page = page_of(all_lines, "portfolio number", "gross assets")
    if page is None:
        page = page_of(all_lines, "total gross assets")
    if page is None:
        page = page_of(all_lines, "portfolio number", "net assets")
    if page is None:
        res.flags.append("Could not find the 'Total assets' overview page"
                         + no_text_hint(read_info))
        return [res]
    lines = [ln for ln in all_lines if ln["page"] == page]

    # ---- header facts: account no, portfolio suffix, currency, date ---------
    suffix: Optional[str] = None
    hit = search_norm(lines, r"portfolionumber([\d\-]+\d)")
    if hit:
        line, m = hit
        res.account_no = m.group(1)
        if "-" in res.account_no:
            suffix = res.account_no.rsplit("-", 1)[1]
    else:
        res.flags.append("Portfolio number not found in header")

    hit = (search_norm(lines, r"valuedin([a-z]{3})")
           or search_norm(lines, r"(?:valuationcurrency|referencecurrency|"
                                 r"accountcurrency):?([a-z]{3})"))
    if hit:
        res.currency = hit[1].group(1).upper()

    hit = search_norm(lines, r"assetsasof(\d{2}\.\d{2}\.\d{4})")
    if hit:
        res.statement_date = hit[1].group(1)
    else:
        hit = search_norm(lines, r"statementofassetsasof(\d{1,2})([a-z]+)(\d{4})")
        if hit:
            d, mon, y = hit[1].groups()
            res.statement_date = f"{d} {mon.capitalize()} {y}"

    # ---- locate the right "Portfolio NN" section -----------------------------
    section = _portfolio_section(lines, suffix) if suffix else None

    if section:
        _read_portfolio_table(res, section, suffix)
    else:
        # No "Portfolio NN" heading printed. In UBS's per-portfolio exports the
        # client's own portfolio is always the FIRST asset-class table on the
        # page (suffix -03 -> Portfolio 03 listed first, etc. — the suffix names
        # it but the heading isn't printed). So: read the FIRST table, i.e.
        # everything up to and including the first "Net assets" row — never mix
        # in rows from a table further down. The suffix stays in the account
        # number and the docx snapshot shows exactly what was read, so the
        # first-table assumption is checkable at a glance.
        net_rows = _net_rows(lines)
        if net_rows:
            cut = lines.index(net_rows[0]) + 1
            # Keep any line still on the SAME printed row as "Net assets" — OCR
            # can drop the bold total a few points below its label, and it must
            # not be cut off the end of the table.
            while (cut < len(lines)
                   and lines[cut]["y0"] - net_rows[0]["y0"] <= _ROW_Y_TOL):
                cut += 1
            first_table = lines[:cut]
            if len(net_rows) > 1:
                res.flags.append(
                    f"No 'Portfolio {suffix}' heading; page shows "
                    f"{len(net_rows)} asset tables — read the FIRST one "
                    f"(portfolio {suffix} is listed first on these statements). "
                    "Double-check against the snapshot in the Word doc.")
            elif suffix:
                res.flags.append(
                    f"No 'Portfolio {suffix}' section heading — read the page's "
                    "single asset-class table (one-portfolio statement)")
            _read_portfolio_table(res, first_table, suffix or "")
        else:
            if suffix:
                res.flags.append(f"'Portfolio {suffix}' table not found — "
                                 "fell back to the whole-relationship totals")
            _read_relationship_totals(res, lines)

    if res.gross_nav is None and not res.gross_is_formula:
        res.flags.append("Gross NAV not found (check the portfolio table)")
    if res.net_nav is None:
        res.flags.append("Net NAV not found (check the portfolio table)")
    return [res]


# ----------------------------------------------------------------------------
# Rows of one printed table are ~11 pt apart; OCR can offset a bold total from
# its label by ~3 pt. 6 pt reunites the two without ever reaching the next row.
_ROW_Y_TOL = 6.0

# Row labels are matched with startswith because the 2026-06 layout prints a
# second table on the SAME rows, so a row's text can read
# "Net assets   Starting value   10 514 794   12 582 141".
_ROW_LABELS = {
    "gross": ("gross assets", "total gross assets"),
    "net": ("net assets", "total net assets"),
    "liquidity": ("liquidity", "total liquidity"),
    "liabilities": ("liabilities", "total liabilities"),
}


def _row(section, key: str):
    return find_row_norm(section, *_ROW_LABELS[key], startswith=True)


def _net_rows(lines):
    """Every "Net assets" row on the page — one per portfolio table."""
    return [ln for ln in lines
            if norm(ln["text"]).startswith(("netassets", "totalnetassets"))]


def _money_on_row(section, row):
    """The money figure printed on `row`, as (value, bbox).

    Drop anything with a decimal point (on this page that is a percentage —
    UBS prints money in whole currency units) and take what is left-most,
    because the asset-class table is the left-hand one on the page. The filter
    is applied only while it still leaves something to read, so an unusual
    statement degrades to "first number on the row" rather than to nothing.

    Deliberately uses no page-geometry threshold: the API version's reader
    synthesises coordinates that carry column ORDER but not true positions, and
    this rule has to give the same answer through both readers.
    """
    cands = amounts_on_row(section, row, _ROW_Y_TOL)
    if not cands:
        return None
    cands = [c for c in cands if not looks_like_percent(c[2])] or cands
    value, box, _raw = cands[0]
    return value, box


def _money_column_name(section) -> str:
    """What the money column is called on this statement — for the Word doc."""
    header = find_row_norm(section, "asset class", startswith=True)
    if header and "marketvalue" in norm(header["text"]):
        return "Market value column"
    return "Total column"


def _portfolio_section(lines, suffix: str):
    """The lines between the 'Portfolio <suffix>' header and the next
    'Portfolio NN' header (or the performance row that closes the section)."""
    want = norm(f"portfolio{suffix}")
    other = re.compile(r"^portfolio\d{1,2}")
    start = None
    for i, ln in enumerate(lines):
        first = norm(ln["text"])
        if first.startswith(want) and not first.startswith("portfolionumber"):
            start = i
            break
    if start is None:
        return None
    end = len(lines)
    for j in range(start + 1, len(lines)):
        t = norm(lines[j]["text"])
        if other.match(t) and not t.startswith(want):
            end = j
            break
        if "cumulativenetperformance" in t:
            end = j + 1   # include it so the snapshot shows the section bottom
            break
    return lines[start:end]


def _read_portfolio_table(res: ClientResult, section, suffix: str) -> None:
    page = section[0]["page"]

    gross_line = _row(section, "gross")
    net_line = _row(section, "net")
    liq_line = _row(section, "liquidity")
    liab_line = _row(section, "liabilities")

    boxes = []
    if gross_line:
        amt = _money_on_row(section, gross_line)
        if amt:
            res.gross_nav, box = amt
            boxes.append((gross_line["x0"], gross_line["y0"], box[2], box[3]))
    if net_line:
        amt = _money_on_row(section, net_line)
        if amt:
            res.net_nav, box = amt
            boxes.append((net_line["x0"], net_line["y0"], box[2], box[3]))
    if liq_line:
        amt = _money_on_row(section, liq_line)
        if amt:
            res.liquidity, box = amt
            boxes.append((liq_line["x0"], liq_line["y0"], box[2], box[3]))
    if liab_line:
        amt = _money_on_row(section, liab_line)
        if amt:
            # enables the same Gross + Liabilities - Net = 0 check column as BoS
            res.liabilities, box = amt
            boxes.append((liab_line["x0"], liab_line["y0"], box[2], box[3]))

    table_name = f"Portfolio {suffix}" if suffix else "The portfolio"

    # No liabilities in this portfolio -> UBS prints no 'Gross assets' row.
    # Gross = Net, and we write that as an Excel formula so it's auditable.
    if res.gross_nav is None and res.net_nav is not None and gross_line is None:
        res.gross_is_formula = True
        res.gross_nav = res.net_nav          # for the docx display
        res.flags.append(f"{table_name} shows no 'Gross assets' row "
                         "(no liabilities) — Gross set equal to Net by formula")

    # UBS's own arithmetic: Gross + Liabilities = Net. If that does not hold,
    # a column was read wrongly (the surest sign the printed layout changed
    # again) — say so loudly rather than write a plausible-looking wrong number.
    if (res.gross_nav is not None and res.net_nav is not None
            and res.liabilities is not None and not res.gross_is_formula):
        if abs(res.gross_nav + res.liabilities - res.net_nav) > 1.0:
            res.flags.append(
                f"{table_name}: Gross {res.gross_nav:,.0f} + Liabilities "
                f"{res.liabilities:,.0f} does not equal Net {res.net_nav:,.0f} "
                "— the statement layout may have changed. Check the snapshot "
                "in the Word doc, and run diagnose.bat UBS if it is wrong.")

    if boxes:
        head = section[0]
        table_box = union_bbox(
            (head["x0"], head["y0"], head["x1"], head["y1"]), *boxes)
        res.hits.append(FieldHit(
            f"{table_name} table ({_money_column_name(section)})",
            res.gross_nav, page, table_box))


def _read_relationship_totals(res: ClientResult, lines) -> None:
    """Fallback for single-portfolio statements: the header block's
    'Total gross assets as of ...  USD 16 400 000' lines."""
    gross = search_norm(lines, r"totalgrossassetsasof")
    net = search_norm(lines, r"totalnetassetsasof")
    if gross:
        amt = first_amount(gross[0])
        if amt:
            res.gross_nav, box = amt
            res.hits.append(FieldHit("Total gross assets (whole relationship)",
                                     res.gross_nav, gross[0]["page"],
                                     (gross[0]["x0"], gross[0]["y0"], box[2], box[3])))
    if net:
        amt = first_amount(net[0])
        if amt:
            res.net_nav, box = amt
            res.hits.append(FieldHit("Total net assets (whole relationship)",
                                     res.net_nav, net[0]["page"],
                                     (net[0]["x0"], net[0]["y0"], box[2], box[3])))
