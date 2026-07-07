# Pinnacle Invoice / Fee Automation — API edition (V2) — router

**Version 2 of `../pinnacle-invoice-automation` (V1).** Same tool: reads bank
client-statement **PDFs** (multi-page), finds the overview page, pulls **Date +
Account No + Currency + Gross NAV + Net NAV + Liquidity**, writes them to a master
Excel (3 tabs, finance-formatted), and screenshots the PDF section each number came
from into a per-bank Word doc for human eyeball verification.

**THE one difference from V1:** scanned/image-only pages are read through the
company's **Gemini API** (`shared/readers/gemini_ocr.py`) instead of local RapidOCR.
Key lives in `api_key.txt` (gitignored; env `GEMINI_API_KEY` wins), model in
`config.GEMINI_MODEL`. Gemini returns per-row JSON (`y` % + `cells` = one cell per
column value); synthetic geometry rebuilds positioned items — wide `_CELL_GAP` stops
space-thousands merges gluing adjacent columns (that bug WAS hit in validation).
Everything else — the 3 bank parsers, Excel/docx writers, watcher — is V1 verbatim.
Bank rules (UBS portfolio tables + first-table rule, BoS labels/parens, LGT add-backs):
see V1's CLAUDE.md or docs/RULEBOOK.md; they apply unchanged here.

## 🔒 Hard constraints (client banking data — non-negotiable)
- **Text-layer PDFs are read fully locally, never uploaded** (PyMuPDF). **Only pages
  with NO text layer** (scans) are sent to Google's Gemini API — mentor-approved, on
  the company's subscription. No other cloud parser (no MinerU etc.).
- **NEVER commit `api_key.txt`, `samples/`, inbox PDFs, or outputs** — repo is public;
  all are gitignored. Never move/delete the colleague's statement PDFs; de-dup is by
  content hash in `processed_index.json`.
- Builds on Mac, **runs on Windows** — keep code cross-platform (`pathlib`); `.bat`
  files are the Windows entry points. Gemini calls use stdlib `urllib` ONLY (no SDK,
  no new wheels).
- **V1 stays untouched.** Never edit `../pinnacle-invoice-automation` from this
  project; fixes to shared logic must be applied to each repo separately (they are
  siblings, not linked).

## Layout deltas vs V1 (only what changed)
- `shared/readers/gemini_ocr.py` — NEW: the API OCR module (prompt, retries 429/5xx,
  plain-English `GeminiOcrError`s that land in the Excel Flags column).
- `shared/readers/pdf_reader.py` — OCR fallback now calls gemini_ocr; on a key/network
  error it stops hammering the API for remaining pages.
- `config.py` — `API_KEY_FILE`, `get_gemini_api_key()`, `ensure_api_key_file()`,
  `GEMINI_MODEL`. Entry points call `ensure_api_key_file()` at start.
- `check_api.py` / `check_api.bat` — NEW: one tiny live test call, plain diagnosis.
- `requirements-ocr.txt` GONE; vendor/ holds only the 4 core libs' wheels (31 MB).
- `tests/test_failure_modes.py` — reworked: no-key / rejected-key / network-down /
  429-retry / mocked end-to-end scanned statement (8 tests, no key or internet needed).
- Snapshots from scanned pages are **approximate** (synthetic coords), exact on
  text-layer pages. Values are exact either way.

## Validation status (2026-07-07, build session)
- 8/8 failure-mode tests pass; 5/5 real supervisor samples pass, including the 3
  scanned pages (2×LGT, 1×UBS) replayed through the full V2 pipeline with V1's
  RapidOCR transcripts served as mocked Gemini responses.
- **NOT yet done: a live Gemini call** — no key on this machine. First user runs
  `check_api.bat`, then drops one scanned LGT statement and eyeballs the docx.

## Run (dev)
`.venv` exists (Mac, Py 3.9): `.venv/bin/python tests/test_failure_modes.py` (anywhere)
and `.venv/bin/python tests/validate_samples.py` (needs local `samples/`; scanned
samples need a real key — or the mock harness from the build session).
GitHub: public repo `warrenlimzf/pinnacle-invoice-automation-api`; colleague uses
Code → Download ZIP, then `setup.bat`, paste key, `check_api.bat`.
