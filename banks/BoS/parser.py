"""Bank of Singapore (BoS) statement parser.

Real layout (validated against the January & March 2026 samples). The
"Overview / Portfolio Distribution" page carries two tables; the FIRST number
on a row is the current-month value (the second is last month's):

    Assets                      31 Mar 2026 (USD)    %     28 Feb 2026 (USD)   %
    Investment Assets                30,000.00     100.00    (1,500.00)      100.00
    ...breakdown rows...
    Liabilities
    Overdrafts                     (115,000.00)    100.00   (116,000.00)     100.00
    Total Net Asset Value *         (85,000.00)              (119,000.00)

  - Gross NAV  = the "Investment Assets" row.
  - Net NAV    = the "Total Net Asset Value" row.
  - Negative numbers print in PARENTHESES — a client can be overdrawn, so the
    Net NAV itself can be negative (the March sample is).
  - Liabilities (the Overdrafts row) are captured too, purely as an audit
    check: Gross + Liabilities should equal Net. The Excel writes that check
    as a formula. Statements with no liabilities have no such section and
    Gross == Net.

Header facts: "Portfolio No.(Val.Ccy)" -> "1000123456-1 (USD)" gives both the
account number and the currency; "Statement Date" -> "31 March 2026".
"""
import re
from typing import List

from shared.extract import (find_row_norm, first_amount, group_lines,
                            page_of, search_norm)
from shared.model import ClientResult, FieldHit
from shared.readers.pdf_reader import PdfReader, no_text_hint

_MONTHS = ("january", "february", "march", "april", "may", "june", "july",
           "august", "september", "october", "november", "december")


def parse(pdf_path) -> List[ClientResult]:
    read_info = {}
    all_lines = group_lines(PdfReader().extract_text_items(pdf_path, read_info))
    res = ClientResult(source_pdf=str(pdf_path))

    # ---- find the overview page in a multi-page statement -------------------
    page = page_of(all_lines, "investment assets", "total net asset value")
    if page is None:
        page = page_of(all_lines, "assets", "total net asset value")
    if page is None:
        res.flags.append("Could not find the 'Portfolio Distribution' overview "
                         "page" + no_text_hint(read_info))
        return [res]
    lines = [ln for ln in all_lines if ln["page"] == page]

    # ---- header facts: account no + currency, statement date ----------------
    # Matched on the RAW text (with spaces): the statement date sits right
    # before the portfolio number on the same header row, and stripping
    # whitespace would glue "...2026" onto "1000123456-1".
    acct_rx = re.compile(r"\b(\d{6,}-\d+)\s*\(([A-Za-z]{3})\)")
    for ln in lines:
        m = acct_rx.search(ln["text"])
        if m:
            res.account_no = m.group(1)
            res.currency = m.group(2).upper()
            break
    else:
        res.flags.append("Portfolio No. not found in header")

    months = "|".join(_MONTHS)
    hit = search_norm(lines, r"(\d{1,2})(" + months + r")(\d{4})")
    if hit:
        d, mon, y = hit[1].groups()
        res.statement_date = f"{d} {mon.capitalize()} {y}"

    # ---- the two tables ------------------------------------------------------
    # Gross: "Investment Assets" row ("Assets" on older layouts).
    gross_line = (find_row_norm(lines, "investment assets")
                  or find_row_norm(lines, "assets"))
    # Net: the "Total Net Asset Value" row (may be negative, in parentheses).
    net_line = find_row_norm(lines, "total net asset value", startswith=True)
    # Liabilities: the "Overdrafts" row, when the client has any.
    liab_line = find_row_norm(lines, "overdrafts")

    if gross_line:
        amt = first_amount(gross_line)       # first number = current month
        if amt:
            res.gross_nav, box = amt
            res.hits.append(FieldHit("Gross NAV (Investment Assets)", res.gross_nav,
                                     gross_line["page"],
                                     (gross_line["x0"], gross_line["y0"], box[2], box[3])))
    if net_line:
        amt = first_amount(net_line)
        if amt:
            res.net_nav, box = amt
            res.hits.append(FieldHit("Net NAV (Total Net Asset Value)", res.net_nav,
                                     net_line["page"],
                                     (net_line["x0"], net_line["y0"], box[2], box[3])))
    if liab_line:
        amt = first_amount(liab_line)
        if amt:
            res.liabilities, box = amt
            res.hits.append(FieldHit("Liabilities (Overdrafts)", res.liabilities,
                                     liab_line["page"],
                                     (liab_line["x0"], liab_line["y0"], box[2], box[3])))

    # sanity note when the audit identity doesn't hold
    if None not in (res.gross_nav, res.net_nav) and res.liabilities is not None:
        if abs((res.gross_nav + res.liabilities) - res.net_nav) > 0.01:
            res.flags.append("Check failed: Investment Assets + Liabilities "
                             "does not equal Total Net Asset Value — verify manually")

    if res.gross_nav is None:
        res.flags.append("Gross NAV not found (expected an 'Investment Assets' row)")
    if res.net_nav is None:
        res.flags.append("Net NAV not found (expected 'Total Net Asset Value')")
    return [res]
