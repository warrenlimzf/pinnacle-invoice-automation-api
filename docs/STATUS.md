# STATUS — API edition (V2)

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
