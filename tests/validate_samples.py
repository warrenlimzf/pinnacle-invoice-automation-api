"""Validate the three bank parsers against the real sample statements.

Everything sensitive stays LOCAL: the sample PDFs live in samples/raw/ and the
expected figures (real account numbers and NAVs, transcribed manually from the
supervisor's green-boxed guide copies in samples/guide/) live in
samples/expected.json. The whole samples/ folder is gitignored because the
GitHub repo is public — this script itself contains no client data.

On a machine without samples/ (e.g. a fresh clone) it says so and exits cleanly.

Run:  python tests/validate_samples.py

expected.json format — one entry per PDF in samples/raw/:
{
  "LGT XXXXXXX March 2026.pdf": {
    "bank": "LGT",                    // LGT | BoS | UBS
    "account_no": "1234567.001",
    "currency": "USD",
    "statement_date": "31.03.2026",
    "gross_nav": 1234567.89,
    "net_nav": 1234567.89,
    "liquidity": 12345.67,            // optional
    "liabilities": -1234.56,          // optional (BoS)
    "addbacks": 2                     // optional (LGT: count of negative rows)
  }, ...
}
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

SAMPLES = ROOT / "samples" / "raw"
EXPECTED_FILE = ROOT / "samples" / "expected.json"


def close(a, b):
    if a is None or b is None:
        return a is b
    return abs(a - b) < 0.005


def main() -> int:
    if not SAMPLES.is_dir() or not EXPECTED_FILE.exists():
        print("samples/raw/ or samples/expected.json not found — "
              "nothing to validate on this machine.")
        return 0
    expected = json.loads(EXPECTED_FILE.read_text(encoding="utf-8"))

    import importlib
    failures = 0
    for fname, exp in expected.items():
        pdf = SAMPLES / fname
        if not pdf.exists():
            print(f"SKIP  {fname} (file missing)")
            continue
        parser = importlib.import_module(f"banks.{exp['bank']}.parser")
        res = parser.parse(pdf)[0]

        problems = []
        for field in ("account_no", "currency", "statement_date"):
            if field in exp and getattr(res, field) != exp[field]:
                problems.append(f"{field}: got {getattr(res, field)!r}, "
                                f"want {exp[field]!r}")
        for field in ("gross_nav", "net_nav", "liquidity", "liabilities"):
            if field in exp and not close(getattr(res, field), exp[field]):
                problems.append(f"{field}: got {getattr(res, field)!r}, "
                                f"want {exp[field]!r}")
        if "addbacks" in exp and len(res.addbacks) != exp["addbacks"]:
            problems.append(f"addbacks: got {len(res.addbacks)}, "
                            f"want {exp['addbacks']}")

        if problems:
            failures += 1
            print(f"FAIL  {fname}")
            for p in problems:
                print(f"      - {p}")
            if res.flags:
                print(f"      flags: {'; '.join(res.flags)}")
        else:
            print(f"OK    {fname}  gross={res.gross_nav:,.2f} "
                  f"net={res.net_nav:,.2f}")

    print("\nAll good." if not failures else f"\n{failures} file(s) failed.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
