# Handoff — read this first (for the colleague and her AI)

> **AI assistants:** your full orientation (reading order, hard rules, and the debug
> journal of already-solved issues) is in **`docs/FOR_COLLEAGUE_AI.md`** — start there.

This project automates reading **Gross NAV** and **Net NAV** off private-bank client
statements (LGT, Bank of Singapore = BoS, UBS) so they don't have to be typed by hand.
**This is the API edition (Version 2):** statements with selectable text are read
locally on this Windows PC, exactly like Version 1 — but scanned/image-only pages are
read through the company's **Gemini API** (key pasted once into `api_key.txt`),
which turns the old minutes-long OCR wait into a few seconds per page.

## ⚠️ The Excel and Word files are a DRAFT / staging area — NOT the final deliverable
The real/master file lives in another folder. The point of this tool is to **cut the work
in half**: instead of reading each PDF and typing figures into the master file (then
re-checking), the colleague:
1. lets the tool extract the figures into the draft `output/nav_master.xlsx`,
2. **eyeballs once** — compares the draft numbers against the screenshots in the Word
   doc (`banks/<bank>/<bank>_verification.docx`),
3. then **copy-pastes** the figures from the draft into her master file.

So treat `nav_master.xlsx` / the `.docx` as scratch that gets overwritten each run.

## The table she copies = the first 6 columns
On every bank tab, the first six columns are exactly:

| Statement Date (A) | Account No (B) | Currency (C) | Gross NAV (D) | Net NAV (E) | Liquidity (F) |
|--------------------|----------------|--------------|---------------|-------------|---------------|

That A:F block is what she copies into her master file. (Columns to the right —
Liabilities + a zero-check for BoS, Source PDF, Page, Updated At, Flags, and LGT's
add-back detail — are only there to help her eyeball; she doesn't copy those.)

**When copying into the master file, paste as VALUES** (in Excel: Paste Special → Values).
This matters because LGT's Gross NAV is a live formula; pasting as values turns it into a
plain number so it doesn't break in the destination file.

## How the whole system runs (Windows)
1. **One-time:** double-click **`setup.bat`** (installs the bundled libraries offline),
   then open **`api_key.txt`**, paste the company's Gemini API key, save, and
   double-click **`check_api.bat`** to confirm it says SUCCESS.
2. **Every day:** double-click **`run_watcher.bat`** and leave the window open.
3. Drop a statement PDF into the matching folder:
   `banks\LGT\inbox\`, `banks\BoS\inbox\`, `banks\UBS\inbox\`.
4. Text-based PDFs (BoS) process in a second or two, fully locally. Scanned statements
   (typically LGT) go through the Gemini API at a few seconds per page — the window
   prints progress the whole way.
   Then eyeball, and copy the A:F block into the master file.
   - On-demand instead of watching? Use **`run_once.bat`**.
5. **No need to delete old files** — already-processed files are skipped automatically
   (matched by content), so nothing duplicates. Just drop the new PDF in.

The `.command` files next to the `.bat` files are the Mac versions — **ignore them on Windows.**

## What each bank does
- **UBS** — statements bundle several portfolios; the portfolio number's suffix (e.g.
  `546-123456-03`) names the one table that gets read ("Portfolio 03"), always the Market
  value column. Gross, Net and Liquidity come straight off that table.
- **BoS** — Gross = "Investment Assets", Net = "Total Net Asset Value". Negatives print in
  parentheses, and an overdrawn client can have a NEGATIVE Net — that is real, not a bug.
  Any Overdrafts figure is captured with a formula check (Gross + Liabilities − Net = 0).
- **LGT** — the statement shows only the Net NAV ("Total"). The tool finds the negative
  line items (e.g. Credit, Derivatives) and writes Gross NAV as a formula that adds them
  back. Each add-back cell is tagged with its name. (Blue = read off the PDF, Black = formula.)

Account number, currency and statement date are read off each statement's header
automatically — there is no manual fill-in step.

## If something looks wrong
- The **Flags** column in the Excel notes when a figure couldn't be found. A flag starting
  with **FAILED** means the PDF couldn't be read at all (most often: it is password-protected,
  the API key hasn't been pasted into `api_key.txt` yet, or the internet is down) — the flag
  text says the fix, and the file is retried automatically on the next run.
- Full run log: `logs\automation.log`.
