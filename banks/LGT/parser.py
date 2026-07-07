"""LGT statement parser.

Real layout (validated against the March 2026 samples, 23–28 page statements).
The overview page is headed "Statement of assets as of DD.MM.YYYY" and its
"Asset allocation overview" table carries everything we need, in the
"Amount in USD" column (the first number on each row — the columns to the
right are percentages):

    Asset allocation/currency   Amount in USD    USD      CHF   ...  % of portfolio
    Liquidity                       95,000.00    48.67 %  ...
    Credit                      -1,100,000.00    ...            <- negative line item
    Short-term investments           6,500.00
    Bonds                        1,500,000.00
    Equities                     3,700,000.00
    Hedge funds                    433,000.00
    Derivatives                    -95,000.00    ...            <- negative line item
    Total                        4,500,000.00    ...            <- this is NET NAV

LGT shows only the Net NAV (the Total). Gross NAV = the Total with every
negative line item added back (a negative of -1,100,000.00 means +1,100,000.00
gets added back), so Gross >= Net always. That derivation is written into the
Excel as a live FORMULA so it can be audited. Clients with no negative rows
simply get Gross = Net (also as a formula).

Header facts: "Client number: 6001234.001" (account no),
"Reference currency: USD", and the statement date from the page heading.
"""
from typing import List

from shared.extract import (amounts_in_line, find_line_norm_contains,
                            find_row_norm, first_amount, group_lines,
                            line_label, page_of, search_norm, union_bbox)
from shared.fees import gross_from_addbacks
from shared.model import AddBack, ClientResult, FieldHit
from shared.readers.pdf_reader import PdfReader, no_text_hint


def parse(pdf_path) -> List[ClientResult]:
    read_info = {}
    all_lines = group_lines(PdfReader().extract_text_items(pdf_path, read_info))
    res = ClientResult(source_pdf=str(pdf_path), gross_is_formula=True)

    # ---- find the overview page in a multi-page statement -------------------
    page = page_of(all_lines, "asset allocation overview")
    if page is None:
        page = page_of(all_lines, "asset allocation", "total")
    if page is None:
        res.flags.append("Could not find the 'Asset allocation overview' page"
                         + no_text_hint(read_info))
        return [res]
    lines = [ln for ln in all_lines if ln["page"] == page]

    # ---- header facts --------------------------------------------------------
    hit = search_norm(all_lines, r"clientnumber:?([\d.]*\d)")
    if hit:
        res.account_no = hit[1].group(1)
    else:
        res.flags.append("Client number not found in header")

    hit = search_norm(all_lines, r"referencecurrency:?([a-z]{3})")
    if hit:
        res.currency = hit[1].group(1).upper()

    hit = search_norm(all_lines, r"statementofassetsasof(\d{2}\.\d{2}\.\d{4})")
    if hit:
        res.statement_date = hit[1].group(1)

    # ---- the allocation table ------------------------------------------------
    header_line = find_line_norm_contains(lines, "asset allocation/currency",
                                          "amount in")
    total_line = find_row_norm(lines, "Total")
    if total_line:
        amt = first_amount(total_line)
        if amt:
            res.net_nav = amt[0]

    item_boxes = []
    if total_line and header_line:
        top_y, bot_y = header_line["y1"], total_line["y0"]
        for ln in lines:
            if not (top_y < ln["y0"] < bot_y):
                continue
            amts = amounts_in_line(ln)
            if not amts:
                continue
            value, box = amts[0]
            label = line_label(ln)
            if not label:            # the bare percentages row above Total
                continue
            item_boxes.append((ln["x0"], ln["y0"], box[2], box[3]))
            if value < 0:            # a negative line item -> add it back
                res.addbacks.append(AddBack(label=label, value=value))
            if "liquidity" in label.lower().replace(" ", ""):
                res.liquidity = value

        # Screenshot the WHOLE allocation table so she can eyeball all add-backs.
        table_box = union_bbox(
            (header_line["x0"], header_line["y0"], header_line["x1"], header_line["y1"]),
            (total_line["x0"], total_line["y0"], total_line["x1"], total_line["y1"]),
            *item_boxes,
        )
        res.hits.append(FieldHit("Net NAV (Total) & add-back items",
                                 res.net_nav, page, table_box))

    res.gross_nav = gross_from_addbacks(res.net_nav, res.addbacks)  # for docx display

    if res.net_nav is None:
        res.flags.append("Net NAV not found (expected a 'Total' row)")
    if not res.addbacks:
        res.flags.append("No negative line items — Gross equals Net (by formula)")
    return [res]
