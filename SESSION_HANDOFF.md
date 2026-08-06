# Session handoff — UBS June 2026 layout fix (applied to both repos)

> Persistent resume file. Paste into a fresh session (or auto-load via a SessionStart hook).
> Delta only — project overview, roles, and decisions live in CLAUDE.md & docs (auto-loaded).

**Role:** Warren's agent maintaining the API edition (V2) of the bank-NAV tool. Both editions
now sit under one parent folder, `~/Claude-Code/pinnacle-invoice-automation/` → this repo
(`pinnacle-invoice-v2-api`) + `../pinnacle-invoice-v1-python` (fully local, recommended). The
parent is a plain container, not a repo. This session's changes were applied to BOTH repos
separately (siblings, not linked).

## Status — updated 2026-08-06
- **UBS changed its printed layout with the June 2026 statements; fixed in both repos.** The
  rule and its rationale live in CLAUDE.md (the UBS paragraph) and `docs/FOR_COLLEAGUE_AI.md`
  journal entry 8.
- **Why this mattered most in THIS edition:** the obvious fix — pick the money column by its
  x-position on the page — was written, tested, and then deliberately REMOVED. It passed in V1
  and would have failed here, because `gemini_ocr` synthesises coordinates that carry column
  ORDER, not true page positions. The shipped rule is geometry-free (skip anything with a
  decimal point; take the left-most survivor). Keep any future parser rule geometry-free for
  the same reason.
- The fix arrived by copying V1's `shared/extract.py` + `banks/UBS/parser.py` + the new
  `tests/test_ubs_layouts.py` verbatim (the files were byte-identical between repos before and
  after), then adding V2-only test coverage here.
- **New tests:** `tests/test_ubs_layouts.py` (4, runs anywhere) and
  `test_scanned_2026_06_layout_end_to_end` + `UBS_2026_06_LINES` in
  `tests/test_failure_modes.py` — the new layout through the FULL pipeline against a mocked
  Gemini response. Failure-mode suite is 9/9 now.
- `samples/` gained the June 2026 UBS statement + its expected values (gitignored). Note
  `tests/validate_samples.py` still needs a real Gemini key here for the scanned samples —
  it stops with a clear message without one; that is expected, not a regression. The June
  file's figures were verified in V1.
- **New doc:** `docs/WHEN_THE_FORMAT_CHANGES.md` — the colleague's self-serve procedure plus a
  copy-paste prompt for her own AI. The V2 copy differs from V1's: it states the Gemini-API
  exception to the "nothing leaves the machine" rule, warns the AI that this reader has no
  true coordinates, and tells it to extend the mocked Gemini rows too.
- All committed code and docs use **illustrative figures only** — real NAVs were scrubbed
  before committing (repo is public).
- Committed + pushed: `aa7d711` on `main`, public GitHub `warrenlimzf/pinnacle-invoice-automation-api`.
- Stale sibling paths fixed in CLAUDE.md (`../pinnacle-invoice-automation` →
  `../pinnacle-invoice-v1-python`).

## Next actions
1. Nothing required from this session's work — shipped, tested, pushed.
2. Carry-over (unchanged, waiting on Warren): **live Gemini shakedown** once a company key
   exists — `check_api.bat` → SUCCESS, then one scanned statement end-to-end, eyeball the docx.
   The live Gemini call has still never run (`api_key.txt` is the placeholder).

## Running state
- Background processes: none
- Dev servers / ports: none
- Worktrees / branches: on `main`, clean, pushed

## Open items
- Live Gemini call never exercised (no key here) — carry-over from the build session. This is
  now slightly more pointed: the UBS fix is proven here only through mocked responses and the
  synthetic-geometry test, never through a real API transcription of the new layout.
- **Data-handling question raised for Warren, not answered:** `docs/WHEN_THE_FORMAT_CHANGES.md`
  tells the colleague to paste a `diagnose.bat` dump (real client figures) into an AI
  assistant "your firm has approved for client data" — whether Pinnacle has approved one is
  undecided.
- V1's open items still stand (colleague's next run; fee rule) — see V1 CLAUDE.md §Open.

## Pick up here
Work is shipped and green (4/4 layout tests, 9/9 failure-mode tests). If Warren returns with a
company Gemini key, run the live shakedown and confirm the real API transcribes the 2026-06
UBS layout the way the mock does. When touching shared logic, apply it to
`../pinnacle-invoice-v1-python` too — the repos are not linked.
