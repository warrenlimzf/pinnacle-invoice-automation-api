"""UBS statement parser.

Real layout (validated against the March 2026 sample, 49-page statement):

The overview page is titled "Total assets" and carries, top-right,
    Portfolio number 546-123456-03
The suffix after the LAST dash ("-03") names WHICH portfolio table to read —
UBS bundles several portfolios (Portfolio 01, 02, 03...) into one statement,
and only the suffixed one is the client's account for our purposes. The header
block's "Total gross/net assets" figures cover the WHOLE banking relationship
(all portfolios), so they must NOT be used when a portfolio table exists.

Inside the right "Portfolio NN" section, we take the MARKET VALUE column
(first number on the row), per the supervisor's guide:
    Asset class      Market value   Accrued interest   Total      % GA
    Liquidity        2 866 000      1 500              2 867 500  19.29
    ...
    Gross assets     14 500 000     1 500              14 501 500 100.00
    Liabilities      -2 450 000     ...
    Net assets       12 050 000     288                12 051 788

Numbers use SPACES as thousand separators. Some portfolios have no
liabilities and therefore no "Gross assets" row — then Gross = Net, written
into Excel as a formula (=Net cell) so the derivation is auditable.

Also extracted: account no (the full portfolio number), currency
("Valued in USD"), statement date, Liquidity, and Liabilities (which powers the
same Gross + Liabilities - Net = 0 check column as BoS).

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

from shared.extract import (find_row_norm, find_rows_norm, first_amount,
                            group_lines, norm, page_of, search_norm, union_bbox)
from shared.model import ClientResult, FieldHit
from shared.readers.pdf_reader import PdfReader, no_text_hint


def parse(pdf_path) -> List[ClientResult]:
    read_info = {}
    all_lines = group_lines(PdfReader().extract_text_items(pdf_path, read_info))
    res = ClientResult(source_pdf=str(pdf_path))

    # ---- find the overview page in a multi-page statement -------------------
    page = page_of(all_lines, "portfolio number", "gross assets")
    if page is None:
        page = page_of(all_lines, "total gross assets")
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
        net_rows = find_rows_norm(lines, "net assets", "total net assets")
        if net_rows:
            first_table = lines[:lines.index(net_rows[0]) + 1]
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

    gross_line = find_row_norm(section, "gross assets", "total gross assets")
    net_line = find_row_norm(section, "net assets", "total net assets")
    liq_line = find_row_norm(section, "liquidity", "total liquidity")
    liab_line = find_row_norm(section, "liabilities", "total liabilities")

    boxes = []
    if gross_line:
        amt = first_amount(gross_line)           # Market value column
        if amt:
            res.gross_nav, box = amt
            boxes.append((gross_line["x0"], gross_line["y0"], box[2], box[3]))
    if net_line:
        amt = first_amount(net_line)
        if amt:
            res.net_nav, box = amt
            boxes.append((net_line["x0"], net_line["y0"], box[2], box[3]))
    if liq_line:
        amt = first_amount(liq_line)
        if amt:
            res.liquidity, box = amt
            boxes.append((liq_line["x0"], liq_line["y0"], box[2], box[3]))
    if liab_line:
        amt = first_amount(liab_line)
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

    if boxes:
        head = section[0]
        table_box = union_bbox(
            (head["x0"], head["y0"], head["x1"], head["y1"]), *boxes)
        res.hits.append(FieldHit(f"{table_name} table (Market value column)",
                                 res.gross_nav, page, table_box))


def _read_relationship_totals(res: ClientResult, lines) -> None:
    """Fallback for single-portfolio statements: the header block's
    'Total gross assets as of ...  USD 16 441 813' lines."""
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
