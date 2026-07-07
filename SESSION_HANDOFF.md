# Session handoff — V2 (API edition) built, stress-tested, pushed

> Persistent resume file. Paste into a fresh session (or auto-load via a SessionStart hook).
> Delta only — project overview, roles, and decisions live in CLAUDE.md & docs (auto-loaded).

**Role:** Warren's agent maintaining the API edition (V2) of the bank-NAV tool. V1
(`../pinnacle-invoice-automation`) is the fully-local version and MUST stay untouched;
this sibling repo swaps only the scanned-page OCR for the company's Gemini API
(mentor's request — company subscription covers the cost).

## Status — 2026-07-07 (V2 build session)
- Forked from V1 `414c4f0`; the ONE functional change is `shared/readers/gemini_ocr.py`
  (+ key plumbing in `config.py`, `check_api.py/.bat`, slimmed vendor/, reworked
  failure-mode tests). See CLAUDE.md "Layout deltas" for the full list.
- **Stress tests all green:** 8/8 failure modes (API mocked), 5/5 real samples incl.
  all 3 scanned pages replayed through the full V2 pipeline (V1 RapidOCR transcripts
  served as mock Gemini responses). Column-glue bug found + fixed during validation
  (cells prompt + `_CELL_GAP`; journal entry 7 in docs/FOR_COLLEAGUE_AI.md).
- Pushed to public GitHub `warrenlimzf/pinnacle-invoice-automation-api`.

## Next actions (queue — wait for Warren)
1. **Live shakedown once a company key exists:** `check_api.bat` → SUCCESS, then one
   scanned LGT statement end-to-end and eyeball the docx. Until then the live Gemini
   call has never been exercised (no key on this machine).
2. If the model name 404s at the company: change `config.GEMINI_MODEL`.
3. V1 open items still stand over there (colleague's re-run on `fa6a820`, fee rule).

## Gotchas for the next session
- Never edit V1 from here; apply shared-logic fixes to each repo separately.
- `api_key.txt` is gitignored and auto-created; never commit or print a key.
- Scanned-page snapshots are approximate by design (synthetic coords) — don't "fix".
- Mock-validation harness lives in the session scratchpad (not committed): dump V1
  RapidOCR transcripts → serve as fake Gemini via `gemini_ocr._call_gemini` patch.
