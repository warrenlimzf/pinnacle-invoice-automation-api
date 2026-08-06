# STATUS — API edition (V2)

## UBS changed its statement layout (2026-08-06, session 5) — fixed in BOTH versions
(applied here separately from V1, as siblings always are)
- The June 2026 UBS statements print a different "Total assets" page: `Market value` and
  `Accrued interest` columns removed, the percentage column moved to the FRONT
  (`Asset class | % GA | Total`), the whole-relationship header totals gone, and a
  "Net Performance" table now printed to the RIGHT of the asset-class table, sharing its
  rows. Symptom on the real June file: Gross = `100.0`, Liquidity = `16.44` (the
  percentages), Net = missing.
- Fix: the parser no longer counts columns. Money is identified by (a) UBS printing money
  in whole currency units and percentages with two decimals — anything with a decimal point
  is skipped (`shared/extract.looks_like_percent`) — and (b) the asset-class table being the
  LEFT-hand one, so the left-most survivor wins. No page-coordinate threshold was used, on
  purpose: the API edition's reader carries column order, not true positions, so the same
  rule has to hold through both readers. `shared/extract.amounts_on_row` re-unites a label
  with a value OCR printed a few points lower (the "Net assets" row does exactly that).
  Backstop: Gross + Liabilities = Net is verified and flagged when it fails.
- Also: overview-page detection falls back to "Net assets" (the June layout has no
  "Total gross assets" line), row labels are matched with `startswith` (the right-hand
  table's text is glued onto the row), and the first-table cut keeps a value printed just
  below its label.
- Verified: the real June 2026 statement now reads Gross / Net / Liquidity / Liabilities
  exactly as printed, with no flags, end-to-end into the Excel with a correct snapshot
  (figures in `samples/expected.json`, gitignored); the March 2026 statement still reads
  its Market value column unchanged. 6/6 samples, 5/5 (V1) and 9/9 (V2) failure-mode
  tests, 4/4 new layout tests. All committed code/docs use illustrative figures only.
- New: `tests/test_ubs_layouts.py` (both layouts + the new layout replayed through this
  edition's synthetic reader geometry), `test_scanned_2026_06_layout_end_to_end` in
  `tests/test_failure_modes.py` (the new layout through the FULL pipeline against a mocked
  Gemini response — 9/9 now), and `docs/WHEN_THE_FORMAT_CHANGES.md` — the operator-facing
  procedure and ready-made AI prompt so the colleague can handle the next change herself.

This repo is **Version 2** of `pinnacle-invoice-automation`. V1 (fully local,
RapidOCR for scans) remains the token-free option and its own repo; this edition
replaces ONLY the scanned-page OCR with the company's Gemini API. V1's full history
and live-run debug journal live in V1's `docs/STATUS.md` and in
`docs/FOR_COLLEAGUE_AI.md` here (entries 1–8).

## Built + stress-tested 2026-07-07 (V2 build session)
- Forked from V1 at commit `414c4f0` (all of V1's live-run fixes included: FAILED-row
  safety net, UBS one-PDF-per-portfolio first-table rule, diagnose.bat, apostrophe
  thousands).
- New `shared/readers/gemini_ocr.py`: image-only pages → PNG (local render) → Gemini
  `generateContent` (stdlib urllib, no SDK) → JSON rows (`y` % + `cells`) → synthetic
  positioned items → the SAME V1 parsers. Retries on 429/5xx; every failure mode maps
  to a plain-English FAILED flag.
- Key handling: `api_key.txt` (auto-created by setup/first run, gitignored; env
  `GEMINI_API_KEY` wins). `check_api.bat` = the colleague's one-click key test.
- OCR extras removed: no `requirements-ocr.txt`, vendor/ trimmed 200 MB → 31 MB,
  no Python-3.12-only constraint left (core wheels cover 3.11–3.13).
- **Stress tests, all passing:**
  - `tests/test_failure_modes.py` — 8/8: encrypted PDF, scan with no key, rejected
    key (403), network down, 429-then-retry, mocked end-to-end scanned UBS statement
    (exact figures + snapshot), plus the two V1 UBS regressions. API fully mocked —
    runs anywhere.
  - `tests/validate_samples.py` — 5/5 real supervisor samples to the cent, with the
    3 scanned pages (2×LGT, 1×UBS) replayed through the complete V2 pipeline using
    V1's RapidOCR transcripts as mocked Gemini responses.
  - Found + fixed during validation: whole-row transcripts let the space-thousands
    merge glue adjacent columns → prompt now demands per-cell output and synthesis
    inserts a wide inter-cell gap (journal entry 7).

## Open
1. **LIVE Gemini call not yet exercised** — no key on the build machine. First user:
   run `check_api.bat` (expects SUCCESS), then drop one scanned LGT statement and
   eyeball the docx. If the model name ever 404s, update `config.GEMINI_MODEL`.
2. Inherited from V1: multiple clients per PDF unsupported; `MGMT_FEE_RATE` unset.
3. Note for the eyeball step: snapshots from scanned pages are approximate crops
   (the API returns no pixel positions); text-layer snapshots remain exact.

## Deferred
- Email ingestion / more file formats — add a new reader in `shared/readers/`.
- Optional: per-page Gemini response cache keyed by (file hash, page) so `--redo`
  doesn't re-pay API calls. Skipped for now to stay 99% identical to V1.
