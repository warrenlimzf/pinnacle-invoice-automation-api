"""Text/number extraction helpers shared by the three bank parsers.

Handles the real-world number formats seen in the sample statements:
  - comma thousands + dot decimal     10,208,537.88   -1,109,240.85   (BoS, LGT)
  - SPACE thousands                   SGD 7 032 282                   (UBS)
  - APOSTROPHE thousands (Swiss)      1'234'567.89
  - parentheses or leading minus for negatives
"""
import re
from typing import Dict, List, Optional, Tuple

from shared.model import BBox

Y_TOL = 3.0  # points: tokens within this vertical distance are the same line

_CURRENCIES = {"SGD", "USD", "EUR", "GBP", "HKD", "CHF", "JPY", "AUD", "CNY", "CNH"}
_DATE_RE = re.compile(r"^\d{1,4}[.\-/]\d{1,2}[.\-/]\d{1,4}$")   # 31.12.2024 etc.
_NUM_START_RE = re.compile(r"^[(\-−]?\d")                  # token begins a number
_THOUSAND_GROUP_RE = re.compile(r"^\d{3}$")                     # "032", "282"


# --------------------------------------------------------------------------- #
#  Number parsing
# --------------------------------------------------------------------------- #
def parse_amount(text: str) -> Optional[float]:
    """Turn a money string into a float. Handles spaces/commas as thousand
    separators, '.' as decimal, and () or leading - as negative."""
    if text is None:
        return None
    s = text.strip()
    for cur in _CURRENCIES:
        s = s.replace(cur, "")
    s = s.replace("*", "").replace("−", "-").strip()

    neg = False
    if s.startswith("(") and s.endswith(")"):
        neg, s = True, s[1:-1]
    if s.startswith("-"):
        neg, s = True, s[1:]

    s = (s.replace(" ", "").replace(",", "").replace("+", "")
          .replace("'", "").replace("’", "").strip())
    m = re.search(r"\d+(?:\.\d+)?", s)
    if not m:
        return None
    val = float(m.group())
    return -val if neg else val


def _is_date(text: str) -> bool:
    return bool(_DATE_RE.match(text.strip()))


# --------------------------------------------------------------------------- #
#  Line grouping
# --------------------------------------------------------------------------- #
def _mk_line(page: int, tokens: List[Dict]) -> Dict:
    tokens = sorted(tokens, key=lambda t: t["x0"])
    return {
        "page": page,
        "tokens": tokens,
        "text": " ".join(t["text"] for t in tokens),
        "x0": min(t["x0"] for t in tokens),
        "y0": min(t["y0"] for t in tokens),
        "x1": max(t["x1"] for t in tokens),
        "y1": max(t["y1"] for t in tokens),
    }


def group_lines(items: List[Dict]) -> List[Dict]:
    """Group positioned word-items into reading lines (one dict per visual row)."""
    by_page: Dict[int, List[Dict]] = {}
    for it in items:
        by_page.setdefault(it["page"], []).append(it)

    lines: List[Dict] = []
    for page in sorted(by_page):
        toks = sorted(by_page[page], key=lambda t: (t["y0"], t["x0"]))
        bucket: List[Dict] = []
        base_y = None
        for t in toks:
            if base_y is None or abs(t["y0"] - base_y) <= Y_TOL:
                bucket.append(t)
                base_y = t["y0"] if base_y is None else base_y
            else:
                lines.append(_mk_line(page, bucket))
                bucket, base_y = [t], t["y0"]
        if bucket:
            lines.append(_mk_line(page, bucket))
    return lines


def line_label(line: Dict) -> str:
    """The leading text label of a line (everything before the first number)."""
    words = []
    for t in line["tokens"]:
        if _NUM_START_RE.match(t["text"]) and not _is_date(t["text"]):
            break
        words.append(t["text"])
    return " ".join(words).strip()


# --------------------------------------------------------------------------- #
#  Amount extraction within a line
# --------------------------------------------------------------------------- #
def amounts_in_line_ex(line: Dict) -> List[Tuple[float, BBox, str]]:
    """Every number on the line, left to right, as (value, bbox, printed text).

    Merges space-separated thousand groups ("7","032","282" -> 7032282) and
    skips date-like tokens. The printed text is kept because the VALUE alone
    cannot always tell a money figure from a percentage: "100.00" parses to
    100.0, which looks like a whole number. See `looks_like_percent`.
    """
    toks = line["tokens"]
    out: List[Tuple[float, BBox, str]] = []
    i = 0
    while i < len(toks):
        t = toks[i]
        if _is_date(t["text"]) or not _NUM_START_RE.match(t["text"]):
            i += 1
            continue
        group = [t]
        j = i + 1
        while (j < len(toks)
               and _THOUSAND_GROUP_RE.match(toks[j]["text"])
               and (toks[j]["x0"] - group[-1]["x1"]) < 12):
            group.append(toks[j])
            j += 1
        raw = "".join(g["text"] for g in group)
        val = parse_amount(raw)
        if val is not None:
            bbox = (min(g["x0"] for g in group), min(g["y0"] for g in group),
                    max(g["x1"] for g in group), max(g["y1"] for g in group))
            out.append((val, bbox, raw))
        i = j
    return out


def amounts_in_line(line: Dict) -> List[Tuple[float, BBox]]:
    """Return every number on the line, left to right, as (value, bbox)."""
    return [(v, b) for v, b, _raw in amounts_in_line_ex(line)]


def looks_like_percent(raw: str) -> bool:
    """True when a printed number is a percentage rather than a money amount.

    Used by the UBS parser, whose asset-class table prints money in WHOLE
    currency units (2 400 000) and percentages with two decimals (16.44,
    100.00, -17.81). Value alone is not enough — 100.00 parses to 100.0, which
    is indistinguishable from a whole number — so this reads the printed text.
    """
    if "%" in raw:
        return True
    return bool(re.search(r"\d[.,]\d", raw.replace(" ", "").replace("'", "")))


def amounts_on_row(lines: List[Dict], row: Dict,
                   y_tol: float = 6.0) -> List[Tuple[float, BBox, str]]:
    """Every number printed on the same VISUAL row as `row`, left to right.

    Line grouping buckets tokens by their top edge, and OCR sometimes places a
    bold total a few points lower than the label it belongs to — so the printed
    row "Net assets ....... 12 000 000" can arrive as two separate lines. This
    sweeps a small vertical window around the row instead of trusting the one
    grouped line, then re-sorts everything left to right.
    """
    out: List[Tuple[float, BBox, str]] = []
    for line in lines:
        if abs(line["y0"] - row["y0"]) > y_tol:
            continue
        out.extend(amounts_in_line_ex(line))
    out.sort(key=lambda a: a[1][0])
    return out


def first_amount(line: Dict) -> Optional[Tuple[float, BBox]]:
    amts = amounts_in_line(line)
    return amts[0] if amts else None


def amount_after_currency(line: Dict) -> Optional[Tuple[float, BBox]]:
    """For UBS-style 'label ... SGD 7 032 282': the amount after the currency code."""
    toks = line["tokens"]
    cur_idx = next((k for k, t in enumerate(toks)
                    if t["text"].upper() in _CURRENCIES), None)
    if cur_idx is None:
        return first_amount(line)
    sub = _mk_line(line["page"], toks[cur_idx + 1:])
    return first_amount(sub)


# --------------------------------------------------------------------------- #
#  Normalized matching (OCR-safe)
#
#  OCR often glues words together ("Netassets", "Portfolionumber546-123456-03"),
#  so every label comparison here strips ALL whitespace and lowercases both
#  sides. "Net assets" and "Netassets" then match the same needle "netassets".
# --------------------------------------------------------------------------- #
def norm(text: str) -> str:
    return re.sub(r"\s+", "", (text or "").lower())


def page_of(lines: List[Dict], *anchors: str) -> Optional[int]:
    """First page whose combined text contains ALL the anchor needles
    (whitespace-insensitive). This is how a multi-page statement is narrowed
    down to the one overview page that carries the NAV figures."""
    pages: Dict[int, List[str]] = {}
    for ln in lines:
        pages.setdefault(ln["page"], []).append(ln["text"])
    wanted = [norm(a) for a in anchors]
    for page in sorted(pages):
        blob = norm("".join(pages[page]))
        if all(w in blob for w in wanted):
            return page
    return None


def find_row_norm(lines: List[Dict], *labels: str,
                  startswith: bool = False) -> Optional[Dict]:
    """First line whose leading label (text before the first number) equals —
    or, with startswith=True, begins with — one of `labels`, ignoring case,
    whitespace, ':' and '*'."""
    wanted = [norm(l) for l in labels]
    for line in lines:
        lab = norm(line_label(line)).strip(":*")
        if not lab:
            continue
        for w in wanted:
            if lab == w or (startswith and lab.startswith(w)):
                return line
    return None


def find_rows_norm(lines: List[Dict], *labels: str) -> List[Dict]:
    """EVERY line whose leading label equals one of `labels` (normalized).
    Lets a parser check a match is unambiguous before trusting it."""
    wanted = [norm(l) for l in labels]
    return [line for line in lines
            if norm(line_label(line)).strip(":*") in wanted]


def find_line_norm_contains(lines: List[Dict], *needles: str) -> Optional[Dict]:
    """First line whose full text contains one of `needles`, whitespace-insensitive."""
    low = [norm(n) for n in needles]
    for line in lines:
        blob = norm(line["text"])
        if any(n in blob for n in low):
            return line
    return None


def search_norm(lines: List[Dict], pattern: str) -> Optional[Tuple[Dict, "re.Match"]]:
    """Regex-search each line's whitespace-stripped lowercase text.
    Returns (line, match) for the first hit."""
    rx = re.compile(pattern)
    for line in lines:
        m = rx.search(norm(line["text"]))
        if m:
            return line, m
    return None


# --------------------------------------------------------------------------- #
#  Line finders
# --------------------------------------------------------------------------- #
def find_line_label_eq(lines: List[Dict], *labels: str) -> Optional[Dict]:
    """First line whose leading label equals one of `labels` (case-insensitive)."""
    wanted = {l.lower() for l in labels}
    for line in lines:
        if line_label(line).lower().strip(" :*") in wanted:
            return line
    return None


def find_line_text_contains(lines: List[Dict], *needles: str) -> Optional[Dict]:
    """First line whose full text contains one of `needles` (case-insensitive)."""
    low = [n.lower() for n in needles]
    for line in lines:
        text = line["text"].lower()
        if any(n in text for n in low):
            return line
    return None


def union_bbox(*boxes: BBox) -> BBox:
    boxes = [b for b in boxes if b]
    return (min(b[0] for b in boxes), min(b[1] for b in boxes),
            max(b[2] for b in boxes), max(b[3] for b in boxes))
