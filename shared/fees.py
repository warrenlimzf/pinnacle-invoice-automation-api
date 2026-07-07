"""The 'LGT fee formula' — i.e. reconstructing Gross NAV from Net NAV + add-backs.

LGT statements show only ONE total (the Net NAV). Several line items are negative
(e.g. Credit, Derivatives). Gross NAV = Net NAV with those negatives added back:

    Gross = Net - (sum of the negative line items)
          = Net + (their absolute value)

In Excel this is written as a live FORMULA (not a hardcoded number) so your
colleague can audit it. This module computes the same value in Python purely so
the Word verification doc can display the resulting Gross number too.
"""
from typing import List, Optional

from shared.model import AddBack


def gross_from_addbacks(net_nav: Optional[float],
                        addbacks: List[AddBack]) -> Optional[float]:
    if net_nav is None:
        return None
    return round(net_nav - sum(a.value for a in addbacks), 2)
