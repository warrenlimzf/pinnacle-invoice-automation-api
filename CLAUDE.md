# Pinnacle Invoice / Fee Automation — API edition (V2) — router

**Version 2 of `../pinnacle-invoice-v1-python` (V1).** Same tool: reads bank
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
**UBS runs TWO printed layouts (2026-08-06):** classic = `Market value | Accrued interest
| Total | % GA`; 2026-06 = `% GA | Total` with a "Net Performance" table to its RIGHT on
the same rows. The money column is therefore NOT picked by position — skip any number with
a decimal point (percentage; UBS money is whole units), take the left-most survivor, and
verify `Gross + Liabilities = Net`. **This matters most HERE:** the synthetic geometry
above carries column ORDER, not true positions, so any coordinate-based rule would break
in this edition only. Lock-in: `tests/test_ubs_layouts.py` +
`test_scanned_2026_06_layout_end_to_end` (mocked Gemini, full pipeline).

## 🔒 Hard constraints (client banking data — non-negotiable)
- **Text-layer PDFs are read fully locally, never uploaded** (PyMuPDF). **Only pages
  with NO text layer** (scans) are sent to Google's Gemini API — mentor-approved, on
  the company's subscription. No other cloud parser (no MinerU etc.).
- **NEVER commit `api_key.txt`, `samples/`, inbox PDFs, or outputs** — repo is public;
  all are gitignored. Never move/delete the colleague's statement PDFs; de-dup is by
  content hash in `processed_index.json`.
- **Read tracking (2026-07-08):** files are read one at a time; already-done files are
  never re-read (so no re-paying to re-OCR a page). Records at root: `processed_index.json`
  (done) + `failed_index.json` (couldn't-read + reason); every run (re)writes
  `output/NEEDS_REUPLOAD.txt` (plain-English "remove & re-upload these", also printed to
  the window). Failed files still auto-retry. Logic in `shared/index.py`
  (`collect_unread`/`write_reupload_report`). Same in V1 (applied separately). Both gitignored.
- Builds on Mac, **runs on Windows** — keep code cross-platform (`pathlib`); `.bat`
  files are the Windows entry points. Gemini calls use stdlib `urllib` ONLY (no SDK,
  no new wheels).
- **V1 stays untouched.** Never edit `../pinnacle-invoice-v1-python` from this
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
  429-retry / mocked end-to-end scanned statement in BOTH UBS layouts (9 tests, no key
  or internet needed).
- `tests/test_ubs_layouts.py` — NEW (2026-08-06): both UBS printed layouts incl. the
  2026-06 one replayed through this edition's synthetic reader geometry. Runs anywhere.
- `docs/WHEN_THE_FORMAT_CHANGES.md` — NEW: the operator's procedure + ready-made prompt
  for having HER AI teach a parser a bank's new layout (API-edition wording).
- Snapshots from scanned pages are **approximate** (synthetic coords), exact on
  text-layer pages. Values are exact either way.

## Validation status (2026-07-07 build session; UBS layout fix 2026-08-06)
- 9/9 failure-mode tests + 4/4 UBS layout tests pass; 5/5 real supervisor samples pass
  (a 6th, the UBS June 2026 statement, is registered in `samples/expected.json` and
  verified in V1 — it needs a key to replay here), including the 3
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
