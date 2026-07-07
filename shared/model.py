"""Small data containers passed between parser, Excel writer and docx writer.

Uses typing.Optional (not `X | None`) so it runs on Python 3.9+ as well as newer.
"""
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

BBox = Tuple[float, float, float, float]  # (x0, y0, x1, y1) in PDF points


@dataclass
class FieldHit:
    """A value plus exactly where it sits on the PDF, so we can screenshot it."""
    label: str                  # e.g. "Gross NAV", "Net NAV", "Allocation table"
    value: Optional[float]
    page: int                   # 0-based page index
    bbox: BBox


@dataclass
class AddBack:
    """An LGT negative line item (e.g. Credit, Derivatives) added back to get Gross."""
    label: str
    value: float                # kept with its real sign as printed (negative)


@dataclass
class ClientResult:
    """Everything extracted from one statement PDF (one client / one account)."""
    account_no: Optional[str] = None        # read off the statement header
    currency: Optional[str] = None          # e.g. "USD"
    statement_date: Optional[str] = None    # as printed, e.g. "31.03.2026"
    gross_nav: Optional[float] = None
    net_nav: Optional[float] = None
    liquidity: Optional[float] = None       # LGT + UBS (BoS doesn't show one)
    liabilities: Optional[float] = None     # BoS only — for the audit check column
    addbacks: List[AddBack] = field(default_factory=list)   # LGT only
    gross_is_formula: bool = False          # LGT: Gross is an Excel formula
    hits: List[FieldHit] = field(default_factory=list)      # for screenshots
    flags: List[str] = field(default_factory=list)          # data-quality notes
    source_pdf: str = ""
    failed: bool = False    # parse crashed — row shows FAILED; retry next run
