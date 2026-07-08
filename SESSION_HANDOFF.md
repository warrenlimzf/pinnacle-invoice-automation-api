# Session handoff — read-tracking + NEEDS_REUPLOAD report, then README restyle (both repos)

> Persistent resume file. Paste into a fresh session (or auto-load via a SessionStart hook).
> Delta only — project overview, roles, and decisions live in CLAUDE.md & docs (auto-loaded).

**Role:** Warren's agent maintaining the API edition (V2) of the bank-NAV tool. V1
(`../pinnacle-invoice-automation`) is the fully-local sibling. This session, at Warren's
explicit request, changes were applied to BOTH repos separately (siblings, not linked).

## Status — updated 2026-07-08
- **Read tracking shipped to both repos** (see CLAUDE.md §Hard-constraints "Read tracking"):
  new `mark_failed`/`clear_failed`/`collect_unread`/`write_reupload_report` in
  `shared/index.py`; `mark_processed` now clears the failed record. `config.py` gained
  `FAILED_INDEX` + `NEEDS_REUPLOAD_REPORT`. `run_all_once.py` + `watcher.py` record the
  failure reason, regenerate `output/NEEDS_REUPLOAD.txt` every run, and print the not-read
  list. `.gitignore` adds `failed_index.json` + `output/NEEDS_REUPLOAD.txt`.
- Design (Warren chose both recommended options): failed files still **auto-retry** AND get a
  visible record; report lives as a human `.txt` + console + machine JSON. Already-done files
  are never re-read (the token/API saver already existed via `already_processed`).
- **Verified:** V2 8/8 failure-mode tests pass, V1 5/5 pass, all 8 edited files compile, plus a
  live end-to-end smoke test (fail→recorded w/ reason→listed in NEEDS_REUPLOAD.txt→success
  clears it), which cleaned up its own temp artifacts.
- **READMEs rewritten** in Warren's claude-web-design house style (emoji headers, linked
  shields badges, 30-sec table, TOC, is/isn't lists, tables). All facts preserved. Badge URLs
  verified 200. See memory `readme-house-style`.
- All changes committed + pushed to both public GitHub repos (feature commit + README commit each).

## Next actions
1. Nothing required from this session's work — it's shipped and verified.
2. Carry-over (unchanged, waiting on Warren): **live Gemini shakedown** once a company key
   exists — `check_api.bat` → SUCCESS, then one scanned LGT statement end-to-end, eyeball the
   docx. The live Gemini call has still never run (no key on this machine). See CLAUDE.md.

## Running state
- Background processes: none
- Dev servers / ports: none
- Worktrees / branches: both repos on `main`, clean, pushed

## Open items
- Live Gemini call never exercised (no key here) — carry-over from build session.
- V1's own open items still stand (colleague's re-run on latest ZIP; fee rule) — see V1 CLAUDE.md §Open.

## Pick up here
Work is shipped and green. If Warren returns with a company Gemini key, run the live
shakedown (item 2). Otherwise await his next request.
