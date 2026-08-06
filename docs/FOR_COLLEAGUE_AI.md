# AI orientation — start here if you are an AI assistant

You (Claude, Gemini, ChatGPT/Codex, Copilot, …) have been opened inside the
**pinnacle-invoice-automation-api** folder — the **API edition (Version 2)** of
pinnacle-invoice-automation. This file tells you what this project is, what
to read in what order, the rules you must never break, and — most importantly — the
**debug journal of issues already solved**, so you never re-debug or re-break them.

## What this project is

A Windows tool for a finance operator. She drops private-bank client
statement PDFs (LGT, Bank of Singapore = "BoS", UBS) into per-bank inbox folders;
the tool extracts Statement Date / Account No / Currency / Gross NAV / Net NAV /
Liquidity into `output/nav_master.xlsx` (one tab per bank) and saves a screenshot of
the exact PDF spot each figure came from into `banks/<bank>/<bank>_verification.docx`.
She eyeballs draft vs screenshots, then copies columns **A:F as values** into her own
master file. The tool is the draft; she is the final check.

**The Version-2 difference:** statements with a text layer are read fully locally,
like Version 1. Pages that are scanned images are read through the company's
**Gemini API** (key pasted once into `api_key.txt`, verified with `check_api.bat`)
instead of the old slow local OCR. That is the ONLY functional difference.

## Read in this order

1. **`README.md`** (repo root) — setup, daily use, the mechanism, troubleshooting table.
2. **`HANDOFF.md`** (repo root) — the operator's day-to-day crib sheet (what to copy where).
3. **`docs/RULEBOOK.md`** — the deep plain-English playbook, including how the engine
   reads a PDF, explained for non-programmers.
4. **`docs/STATUS.md`** — current project state, what's validated, what's still open.
5. **`CLAUDE.md`** (repo root) — the code-layout router (written for Claude, useful to
   any AI: says which file owns which job).

## Hard rules — never break these, whatever you are asked

- **Text-layer PDFs stay local.** The ONE sanctioned upload is a scanned/image-only
  page going to the Gemini API (company subscription, mentor-approved) via
  `shared/readers/gemini_ocr.py`. Never send client data to any OTHER cloud service,
  parser, or API — no "helpful" OCR/parsing websites, no MinerU.
- **Never commit, print, or echo the API key.** `api_key.txt` is gitignored; keep it
  that way. Logs and error messages must never contain the key.
- **Never move, rename or delete the statement PDFs** in the inbox folders. Originals
  stay put; de-duplication is by content hash (`processed_index.json`), not by moving files.
- **Never commit client data.** `samples/`, inbox PDFs, `output/` and `logs/` are
  gitignored on purpose; keep them that way. This repo is public.
- **Never guess or invent a figure.** If a value can't be read, the correct behaviour is
  a blank cell plus a note in the Flags column.
- After ANY parser change, run all three test suites — `python tests/test_failure_modes.py`
  and `python tests/test_ubs_layouts.py` (both work anywhere) and
  `python tests/validate_samples.py` (needs the local `samples/` folder, and a Gemini key
  for the scanned samples).
- **Teaching a parser a new layout must never cost it the old one.** Banks change their
  statements (UBS did in June 2026) while months of older statements are still being
  processed, so every layout the tests cover has to keep passing.

## Debug journal — solved issues (do NOT re-debug these)

**1. "UBS and LGT tabs completely empty, BoS fine" (2026-07-07).**
Root cause: any exception while reading a PDF (see #2 and #3) was logged to
`logs/automation.log` but wrote **no Excel row**, so failing files vanished silently.
Fix (commits `a5ffceb`, `56c8b4e`): a parse failure now writes a visible row whose flag
starts with **FAILED** plus the reason and remedy; failed files are not marked processed,
so they retry automatically on the next run. A tab can no longer be silently empty — if
a tab looks empty today, the run didn't happen or was killed mid-way.

**2. Scanned statements looked like a hang (V1) — the reason V2 exists.** LGT
statements are typically full-page scans; V1's local OCR read them at ~10 s/page, so
a 20-page file took 3–4 minutes and users closed the window mid-read, causing #1.
V2 reads those pages through the Gemini API in a few seconds each. BoS PDFs have a
text layer and never touch the API — that speed difference is normal.

**3. Password-protected PDFs.** Bank portals sometimes lock PDFs; PyMuPDF then raises
`ValueError: document closed or encrypted` on page access. Handled in
`shared/readers/pdf_reader.py` (`PdfReadError` with a plain-English message → FAILED
row). Remedy for the user: open with the password, print/save as a new PDF, re-drop.

**4. API failure modes are all contained (V2).** A scanned PDF with no key pasted, a
rejected key (HTTP 400/403), or no internet each yields a visible FAILED row whose
flag names the exact remedy (never a crash, never a silently empty tab); the API is
retried automatically on 429/5xx, and a key/network error stops further API calls for
that file instead of hammering every page. Covered by `tests/test_failure_modes.py`
(runs anywhere, API fully mocked). `check_api.bat` is the user-facing key self-test.

**5. UBS one-portfolio-per-PDF exports (2026-07-07, first live run).** The validated
supervisor sample bundled all portfolios in one statement with "Portfolio NN" section
headings. The colleague's real UBS files are exported one PDF per portfolio (e.g.
`…0002` / `…0003` files): same asset-class table(s) on the overview page, but NO
"Portfolio NN" headings and no "Total … assets as of" header totals — so rows appeared
with date + account number but empty values. Per Warren: in these exports the client's
own portfolio (the one the account-number suffix names) is always printed FIRST. Fix:
when the heading is missing, read the FIRST table only — everything up to the first
"Net assets" row, so rows are never mixed across tables — and flag for the eyeball
check when several tables share the page. UBS Liabilities row is now captured too,
powering the Gross + Liabilities − Net = 0 Check column. Swiss apostrophe thousands
(1'234'567.89) also handled in `parse_amount`. Regression tests:
`test_ubs_single_portfolio_statement` + `test_ubs_two_tables_takes_first`.

**6. When a layout still surprises us: `diagnose.bat`.** Dumps the text the tool sees
in every inbox PDF to `logs/diagnose/*.txt` (`diagnose.bat UBS` = one bank). The user
sends the .txt of the problem statement to Warren so the parser gets fixed against
real wording, never guesses. The operator can also fix it herself with her own AI:
`docs/WHEN_THE_FORMAT_CHANGES.md` is the prompt she pastes in, and it points that AI at
this journal, the parser, and the tests it must pass. Those dumps contain client data — they stay local and are
shared person-to-person inside the firm only.

**7. Gemini OCR must return CELLS, not whole-row strings (2026-07-07, V2 build).**
First V2 design had Gemini return each row as one text string; the synthetic geometry
then used uniform spacing, so the parsers' space-thousands merge ("12 000 000" =
12,051,656) ran straight across column boundaries and glued the next column's value on
(net 12,051,656 became 12,051,656,287 on the real scanned UBS sample). Fix: the prompt
asks for `cells` (label + each column value as its own cell) and synthesis inserts a
wide `_CELL_GAP` between cells, so a merge can never cross a column. Do NOT "simplify"
the prompt back to plain lines. Validated against all 3 real scanned sample pages.

**8. UBS changed the "Total assets" page layout (June 2026 statements).** Up to May 2026
the asset-class table read `Asset class | Market value | Accrued interest | Total | % GA`
and the parser took the FIRST number on each row (the Market value column). From June 2026
UBS dropped *Market value* and *Accrued interest*, moved the percentage to the FRONT
(`% GA | Total`), and started printing a "Net Performance" table to the RIGHT of the
asset-class table on the same lines. Symptom: Gross NAV came out as `100.0`, Liquidity as
`16.44` (the percentages), and Net NAV was missing entirely. Fix — the parser no longer
counts columns; it uses two facts true on both layouts: (a) UBS prints money in whole
currency units and percentages with two decimals, so any number with a decimal point is a
percentage and is skipped (`shared/extract.looks_like_percent`); (b) the asset-class table
is the LEFT-hand one, so the left-most survivor is the money figure. Deliberately no
page-coordinate threshold — the API edition's reader reports column *order*, not true
positions, and the same rule has to work through both. Two extras: the "Net assets" row has
no percentage at all, and a scan can print its bold total a few points below its label, so
`shared/extract.amounts_on_row` sweeps a small vertical window to re-unite them. Backstop:
Gross + Liabilities = Net is verified in the parser and flagged if it fails.
Regression tests: `tests/test_ubs_layouts.py` (4 tests — both layouts, plus the new layout
replayed through this edition's synthetic reader geometry), plus
`test_scanned_2026_06_layout_end_to_end` in `tests/test_failure_modes.py`, which runs the
new layout through the full pipeline against a mocked Gemini response, and the June 2026
sample in `samples/`.
**Do not "simplify" the parser back to `first_amount` on these rows.**

**9. Historical: Account No was once a manual AI step.** The tool now reads account
number, currency and statement date off each statement's header automatically. If you
were asked to "fill in account numbers", that job no longer exists — check column B is
already filled.

## Where things live (for making changes)

- `banks/<LGT|BoS|UBS>/parser.py` — the three per-bank parsers (all real logic).
- `shared/readers/pdf_reader.py` — text-layer extraction + encrypted-PDF handling;
  falls back to `shared/readers/gemini_ocr.py` (the API OCR module: prompt, retries,
  plain-English errors) for image-only pages. `shared/extract.py` — line grouping /
  number parsing (space thousands, parentheses negatives). `shared/process.py` — glue
  incl. the FAILED-row safety net. `config.py` — paths, `GEMINI_MODEL`, key handling.
- `shared/excel_writer.py` / `shared/docx_writer.py` — outputs (blue = hardcoded,
  black = formula). `config.py` — every path and setting.
- Entry points: `watcher.py` (folder watch) and `run_all_once.py` (one shot), launched
  by the `.bat` files (Windows) / `.command` files (Mac dev machine).
- `docs/WHEN_THE_FORMAT_CHANGES.md` — the operator-facing procedure (and the prompt she
  hands you) for teaching a parser a bank's new printed layout. If you were pasted that
  prompt, follow it exactly; it is the same workflow used for the UBS June 2026 change.

When you fix a NEW issue in this project: add it to this debug journal and to
`docs/STATUS.md`, so the next AI (or the same one next month) never solves it twice.
