# Bank NAV automation — API edition (LGT · Bank of Singapore · UBS)

Drop a private-bank client-statement **PDF** into that bank's inbox folder. The tool
reads **Statement Date, Account No, Currency, Gross NAV, Net NAV and Liquidity** off
the statement, writes them into one Excel workbook (one tab per bank, one row per
statement), and saves a **screenshot of the exact spot on the PDF** each number came
from into a Word document — so you check the numbers by eyeballing, not re-typing.

**This is Version 2 of [pinnacle-invoice-automation](https://github.com/warrenlimzf/pinnacle-invoice-automation).**
The only difference: scanned/image-only statement pages are read through the company's
**Gemini API** instead of a slow local OCR engine — seconds per page instead of minutes,
no heavy OCR install, no risk of closing the window mid-read. Everything else (the
parsers, the Excel, the Word verification docs) is identical to Version 1.

**Privacy:** normal statements with selectable text (every BoS statement, most UBS)
are read **entirely on your own computer and never uploaded anywhere** — exactly like
Version 1. Only pages that are *pictures* of a statement (scans, typically LGT) are
sent to Google's Gemini API under the **company's own subscription** for reading. No
real statement or output file is ever committed to this repository, and neither is the
API key.

Documentation map:
- **This README** — setup, daily use, how it works, and every known problem + fix.
- **[docs/RULEBOOK.md](docs/RULEBOOK.md)** — the full plain-English playbook (same
  content as here, in more depth, including the mechanism explained for non-programmers).
- **[HANDOFF.md](HANDOFF.md)** — the day-to-day operator crib sheet (what to copy where).
- **[docs/FOR_COLLEAGUE_AI.md](docs/FOR_COLLEAGUE_AI.md)** — **if you are an AI assistant**
  (Claude / Gemini / ChatGPT / Copilot) opened inside this folder, start THERE. It says
  what to read, where the handoff is, and lists every issue already debugged.
- **[docs/STATUS.md](docs/STATUS.md)** — project state and the debug journal.

---

## Setup & use (Windows)

### Step 1 — install Python *(ONE time ever — skip this forever after)*
Download **Python 3.12** — the "Windows installer (64-bit)" from
<https://www.python.org/downloads/release/python-3120/> — and run it.
On the very first screen, **tick "Add python.exe to PATH"** before clicking Install.
That box matters; don't skip it.

Python and everything this tool installs is **free, open-source software. There is
nothing to buy.** (The Gemini API usage runs on the company's existing subscription.)

> Already installed Python once? Then every future update starts from **Step 2**.

### Step 2 — download the latest tool *(repeat this whenever there's an update)*
1. Open <https://github.com/warrenlimzf/pinnacle-invoice-automation-api> (no account needed).
2. Click the green **Code** button → **Download ZIP**.
3. Right-click the ZIP → **Extract All**. Put the folder somewhere easy (e.g. Documents).
4. If you had an older copy: **copy your statement PDFs** from the old folder's
   `banks\<bank>\inbox\` folders into the new folder's same inbox folders — and copy
   your old **`api_key.txt`** across too so you don't have to paste the key again. Then
   the old folder is yours to keep or bin.

### Step 3 — run setup *(once per downloaded copy)*
Double-click **`setup.bat`**. It installs the bundled libraries **offline** from the
`vendor/` folder (no internet needed) and creates an empty **`api_key.txt`** in the
folder. When it says setup is complete, close the window.

### Step 4 — paste the company's API key *(once per downloaded copy)*
1. Open **`api_key.txt`** (in the tool's folder) in Notepad — double-clicking it works.
2. Delete the placeholder line and **paste the company's Gemini API key** — one line,
   no spaces before or after. Save and close.
3. Double-click **`check_api.bat`**. It sends one tiny test request (no client data)
   and prints **SUCCESS** if the key works — or tells you exactly what's wrong.

The key stays in that file on your PC. It is never committed, uploaded or shared —
`api_key.txt` is on the repository's ignore list. If the key ever changes, just paste
the new one over it.

### Step 5 — daily use
- **Automatic (recommended):** double-click **`run_watcher.bat`** and leave the window
  open. Drop each bank's PDF into its inbox folder:
  `banks\LGT\inbox\` · `banks\BoS\inbox\` · `banks\UBS\inbox\`
  Each file is processed the moment it lands.
- **On demand:** put the PDFs in the inboxes first, then double-click **`run_once.bat`**.

Statements with a text layer (BoS, most UBS) finish in under a second and never touch
the internet. Scanned statements (typically LGT) go page-by-page through the Gemini
API at a **few seconds per page** — the window prints progress lines the whole way.
This cost is paid **once per file, ever**: processed files are remembered (by content),
so the next run skips them instantly.

### Step 6 — check, then copy into the master file
1. Open `output\nav_master.xlsx` (one tab per bank) next to that bank's Word file
   (`banks\<bank>\<bank>_verification.docx`, which holds the screenshots).
2. Glance that each row's numbers match its screenshot. **Blue** numbers were read
   straight off the PDF; **black** cells are live formulas the tool built (e.g. LGT's
   Gross NAV = Net NAV with the negative line items added back — each add-back cell is
   tagged with its name). On scanned pages the screenshot crop is *approximate* (the
   API doesn't return pixel positions), so it shows the right area of the page rather
   than the exact row — the numbers themselves are transcribed exactly.
3. Copy the **A:F block** (Statement Date | Account No | Currency | Gross NAV | Net NAV
   | Liquidity) into your own master file, pasting **as values** (Paste Special →
   Values), so the formulas become plain numbers.

The Excel/Word here are a **draft / staging area**, never the final deliverable.
Your original PDFs are **never moved, renamed or deleted**.

---

## How it actually works (the mechanism)

**Two kinds of PDF, two reading paths.** A normal PDF stores its text as data — the
file literally says which characters sit where — and the tool copies that out in
microseconds, fully locally (every BoS statement). A *scanned* PDF stores each page as
one photograph: millions of pixels and no text anywhere. For those pages only, the tool
renders the page to an image and sends it to the **Gemini API**, which reads the page
and sends back every line of text as structured JSON — "this row says Net assets,
12 051 656, at this height on the page." Python then rebuilds those lines into
positioned text and hands them to the same bank parsers Version 1 uses. Version 1 did
this recognition with a local OCR engine at ~10 seconds a page; the API does it in a
few seconds with no local heavy lifting.

**Finding the numbers.** Each bank has its own parser, keyed to that bank's real layout:
- **UBS** — statements can bundle several portfolios; the portfolio number's suffix
  (e.g. `…-03`) selects the right "Portfolio 03" table, and Gross / Net / Liquidity are
  read from its **Market value** column. The header's whole-relationship totals are
  deliberately ignored when a portfolio table exists.
- **BoS** — Gross = "Investment Assets", Net = "Total Net Asset Value". Negatives print
  in parentheses; an overdrawn account can genuinely have a negative Net. Overdrafts are
  captured with an audit formula (Gross + Liabilities − Net = 0) in the Check column.
- **LGT** — the statement shows only the Net NAV ("Total"). The tool collects the
  negative line items (Credit, Derivatives, …) and writes Gross NAV as a **live Excel
  formula** adding them back, so the derivation is auditable cell by cell.

**Nothing is guessed, and nothing fails silently.** If a figure's label can't be found,
the cell stays blank and the **Flags** column says so. If a whole PDF can't be read, the
tool writes a row whose flag starts with **FAILED** and states the exact reason and fix
— a bank tab can never be silently empty. Failed files are retried automatically on the
next run. Every number that *is* written has a screenshot proving where it came from.

**File memory.** Each processed PDF is remembered by its content (a hash), not its
name — old files are never re-processed, nothing duplicates, and re-dropping a file
after deleting its row rebuilds exactly that row. (That also means a statement's API
cost is paid once, not on every run.)

**Which files were read — and which weren't.** Statements are read strictly **one at a
time**: a single unreadable file never blocks the others, and a file already written to
the Excel is never read again (that is what makes repeat runs instant and stops paying
to re-OCR the same scanned page twice). So you never have to wonder what did or didn't
go in: after **every** run the tool writes **`output\NEEDS_REUPLOAD.txt`**. If everything
read cleanly it says so; otherwise it lists each file that did **not** make it into the
Excel, the reason, and the fix — **remove that file from its inbox folder, sort out the
cause, then drop the corrected copy back into the same folder.** The same list is printed
in the run window. (Under the hood two small records sit next to the tool — `processed_index.json`
for files that are done, `failed_index.json` for files still needing attention — but you
never open those; the `.txt` is the human-readable view.)

---

## Troubleshooting — every problem seen so far, and the fix

| What you see | What it means | What to do |
|---|---|---|
| **Some statements are missing from the Excel** after a run | One or more files couldn't be read that run — they're never dropped silently. | Open **`output\NEEDS_REUPLOAD.txt`**: it names each file that wasn't read, the reason, and the fix. Remove and re-drop **only** those files — everything already in the Excel stays put. |
| Lines like *"page N … had no text layer — read it through the Gemini API instead"* | **Not an error.** That statement is a scan; the API is reading it at a few seconds per page. | Wait — the window prints progress the whole way. |
| A row's flag says **no API key is set — open api_key.txt** | The key hasn't been pasted in yet (or the placeholder is still there). | Open `api_key.txt`, paste the company's Gemini API key, save, run `check_api.bat`, then just run again — failed files retry automatically. |
| A row's flag says **the Gemini API rejected the key (HTTP 403/400)** | The key was pasted incompletely, has stray spaces/line breaks, or the subscription is inactive. | Re-copy the key into `api_key.txt` carefully and verify with `check_api.bat`. If it still fails, ask whoever manages the company's Gemini subscription. |
| A row's flag says **could not reach the Gemini API** | No internet, or the company proxy/firewall is blocking `generativelanguage.googleapis.com`. | Check the connection, then run again. (Text-layer statements still process fine offline.) |
| A row's flag starts with **FAILED — the PDF is password-protected** | Bank portals often lock PDFs with a password; a locked PDF can't be read by any tool. | Open the PDF with its password, **print/save it as a new PDF** (this removes the lock), drop the unlocked copy in. |
| *"Permission"* / *"file is open"* message | Excel or Word has the output file open, so Windows blocks writing. | Close the file, drop the PDF in again (or re-run). |
| A blank cell + a note in Flags | That figure's label wasn't found on the page — the tool never guesses. | Check the statement; if the bank truly changed its wording, the parser needs a small update (see next row). |
| A statement still extracts wrongly after all of the above | The bank uses a layout/wording the parser hasn't met yet. | Run **`diagnose.bat`** (or `diagnose.bat UBS` for one bank). It writes what the tool sees in each PDF to `logs\diagnose\*.txt` — send the .txt for the problem statement to the developer so the parser is fixed against real wording, not guesses. These dumps stay on your computer. |

Full run log: `logs\automation.log` — every action and error is recorded there.

---

## For developers / AI assistants

- Start at **[docs/FOR_COLLEAGUE_AI.md](docs/FOR_COLLEAGUE_AI.md)** (reading order, hard
  rules, and the debug journal of solved issues).
- Code layout: `banks/<bank>/parser.py` (per-bank logic), `shared/` (reader, the
  Gemini OCR module `shared/readers/gemini_ocr.py`, Excel/Word writers), `config.py`
  (all paths/settings incl. the API key file and model name), `watcher.py` +
  `run_all_once.py` (entry points), `check_api.py` (key self-test).
- Tests: `python tests/test_failure_modes.py` runs anywhere (synthetic PDFs, **mocked**
  API — no key or internet needed); `python tests/validate_samples.py` checks all real
  samples to the cent but needs the local, **never-committed** `samples/` folder (and a
  real key for the scanned samples).
- Hard rules: text-layer statements stay local; **only scanned pages** go to the Gemini
  API, on the company key; originals are never moved/deleted; and no client data or key
  is ever committed — `samples/`, inbox PDFs, outputs and `api_key.txt` are gitignored.
