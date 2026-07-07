---
title: Bank NAV Automation — Rulebook
tags: [pinnacle, automation, playbook, internal]
---

# Bank NAV Automation — Rulebook

> [!info] What this document is
> The full plain-English explanation of how this tool works, written so Warren can
> understand every moving part and teach the colleague from it. The short version
> she actually uses is the repo's `README.md` on GitHub. This is the deep version.

## 1. What the tool does, in one breath

The colleague drops a bank statement PDF (LGT, Bank of Singapore, or UBS) into a folder.
The tool finds the overview page inside the (often long) statement, reads the **statement
date, account number, currency, Gross NAV, Net NAV and Liquidity** off it, writes them into
a master Excel, and saves a screenshot of the exact part of the PDF each number came from
into a Word document. She opens the Excel and the Word side by side, checks the numbers
match the screenshots, then copies the figures into her own master file.

Statements with selectable text are read entirely on her own computer with a local
library (PyMuPDF) — nothing sent to the internet, exactly like Version 1. The ONE
exception in this API edition: a page that is only a *picture* of a statement (a scan)
is sent to Google's **Gemini API** to be read, under the company's own subscription.
The key is pasted once into `api_key.txt` and stays on her PC.

> [!important] It is a draft, not the final file
> The Excel this tool produces is a **staging area**, not her real master spreadsheet. The
> whole point is to cut her work roughly in half: instead of reading each PDF and typing
> figures into her master and then double-checking, she lets the tool extract the numbers,
> eyeballs them once against the screenshots, and pastes them across as values.

## 2. The big picture of how it runs

There are two pieces of plumbing worth understanding.

**Python** is the engine. It is a programming language, and the whole tool is written in it.
Nothing runs unless Python is installed on the machine first.

**The `.bat` files** are the buttons. A `.bat` file ("batch file") is just a plain text file
holding a short list of commands, with a special ending that tells Windows "this is runnable."
Double-clicking one opens a black window and runs those commands for you, top to bottom, so
the colleague never has to open a terminal or type anything herself. You can open any `.bat`
in Notepad and read exactly what it will do. Nothing is hidden.

> [!note] Mac vs Windows launchers
> The folder has launchers ending in both `.bat` (Windows) and `.command` (Mac). Each
> operating system can only run its own kind, and double-clicking the wrong one simply does
> nothing. The colleague is on Windows, so she uses the `.bat` files and ignores the
> `.command` ones. They are harmless, just two sets of the same buttons for two machines.

## 3. Installing Python (the one part people get wrong)

Install **Python 3.12** specifically. The tool ships with its libraries pre-packaged for
Python 3.11 to 3.13, so 3.12 is the safe middle choice. A different version can cause the
offline install to fail and fall back to needing internet.

On the **first** install screen there is a checkbox: **"Add python.exe to PATH"**. Tick it
before clicking Install.

> [!tip] What "Add to PATH" actually means
> You do not choose where Python goes. The installer drops it in a default folder by itself
> (something like `C:\Users\<name>\AppData\Local\Programs\Python\Python312\`).
>
> PATH is a short list of folders that Windows searches whenever a command refers to a
> program by name. When a `.bat` file says the word `python`, Windows walks down that list
> and uses the **first** `python.exe` it finds, then stops. It does **not** scan the whole
> hard drive.
>
> Ticking the box does two things at once: it installs Python to that default folder **and**
> adds that folder to the PATH list. So with the box ticked, the `.bat` files can find Python
> instantly. With it unticked, Python is still installed but not on the list, so the `.bat`
> says "python was not found" and setup fails.

## 4. Getting the tool onto her PC

The project lives on GitHub as a **public** repo, so she needs no account and no login:

`https://github.com/warrenlimzf/pinnacle-invoice-automation-api`

The simplest route for a non-technical person: open the link, click the green **Code**
button, choose **Download ZIP**, then right-click the downloaded file and **Extract All**.

> [!tip] Why download/clone instead of zipping your own folder
> A live copy of this project on Warren's Mac contains a hidden `.venv` folder. That folder
> holds libraries compiled for **macOS**, which will not run on Windows. GitHub never stores
> `.venv` (it is in `.gitignore`), so anything she downloads or clones from GitHub is already
> clean, with no `.venv` at all. Her `setup.bat` then builds a fresh **Windows** `.venv`.
> This is the whole reason we go through GitHub rather than emailing a zip of the Mac folder.

If she prefers the command line and has Git installed, the equivalent is:

```bash
git clone https://github.com/warrenlimzf/pinnacle-invoice-automation-api.git
```

## 5. The three files she ever touches

| File | When | What it does |
|---|---|---|
| `setup.bat` | Once, ever | Builds the isolated Python environment, installs the libraries (offline, from the bundled `vendor` folder), and creates `api_key.txt`. |
| `api_key.txt` | Once, ever | Open in Notepad, paste the company's Gemini API key over the placeholder, save. Then double-click `check_api.bat` to confirm it says SUCCESS. |
| `run_watcher.bat` | Each working session | Starts the watcher and leaves a window open. This is the "go" button. |

> [!note] What setup.bat installs into
> It creates a folder called `.venv` (a "virtual environment"). Think of it as a private box
> inside the project that holds just this tool's libraries, kept separate from the rest of
> the computer. The libraries come from the `vendor` folder, which already contains the
> correct Windows files, so the install works with no internet. If that ever fails (usually
> a Python version mismatch), it automatically tries the internet as a backup.

## 6. What `run_watcher.bat` actually does

When double-clicked it: checks that setup has been run, activates the `.venv` box, then starts
`watcher.py` and keeps the window open. While that window stays open the watcher sits and
watches the three inbox folders:

- `banks\LGT\inbox`
- `banks\BoS\inbox`
- `banks\UBS\inbox`

The instant a PDF appears in one of them, the watcher:

1. waits until the file has finished copying (so it never reads a half-written file),
2. checks whether it has already done this exact file (see the re-do section below),
3. reads the Gross and Net NAV, writes them into `output\nav_master.xlsx`,
4. saves a screenshot of the exact PDF section into that bank's `_verification.docx`,
5. and at startup also sweeps up any PDFs already sitting in the inboxes, so nothing is missed.

> [!warning] It never moves or deletes her PDFs
> Originals stay exactly where she puts them. The tool remembers what it has processed by
> taking a fingerprint of each file's contents, not by moving files around.

## 7. Reading and copying the results

Open `output\nav_master.xlsx`. There is one tab per bank, and each row is one statement,
identified by the PDF's filename in the "Source PDF" column. The columns are ranked by
importance, in the order the supervisor's guide lists them:

| A | B | C | D | E | F |
|---|---|---|---|---|---|
| Statement Date | Account No | Currency | Gross NAV | Net NAV | Liquidity |

After F come the housekeeping columns: **Liabilities** and a **Check** cell (Bank of
Singapore only — the check is a live formula, Gross + Liabilities − Net, which should show
0.00), then Source PDF, Page, Updated At and Flags. For LGT, the negative line items that
were added back sit further right (column N onwards), each with a comment naming the line
item, feeding the Gross NAV formula.

Open the matching Word file next to it, for example `banks\LGT\LGT_verification.docx`. It
holds the screenshots of where each number was read from. Glance across to confirm the
figures match.

Then copy the **A to F block** into her own master file, pasting **as values**. The account
number is now read straight off the statement header (LGT's "Client number", BoS's
"Portfolio No.", UBS's "Portfolio number"), so there is no manual fill-in step any more.

> [!tip] Colour code in the Excel
> Numbers in **dark blue** are read straight off the PDF (hardcoded). Numbers in **black**
> are calculated by a live formula you can click and audit. Formulas appear wherever a figure
> was DERIVED rather than read: LGT's Gross NAV (Net plus the added-back negatives), any
> Gross-equals-Net case, and the BoS check cell. This is standard finance convention.

## 7b. How the engine actually reads a PDF (the mechanism, for non-programmers)

Warren asked for the machinery to be written down in plain terms, so here it is.

**A digital PDF already knows its own text.** When a bank generates a statement, the file
stores every word along with its exact position on the page, like a map: "the word
'Total' sits 105mm from the left, 260mm from the top." The tool uses a local library called
**PyMuPDF** to read that map. It never "looks" at the page like a human; it asks the file
directly for its words and their coordinates. That is also why the screenshots are possible:
once the tool knows *where* a number sits, it can render just that rectangle of the page
into an image for the Word doc.

**Step 1 — find the right page.** Statements run to dozens of pages, but each bank has one
overview page that carries everything we need. The tool walks page by page looking for that
page's fingerprint: LGT's says "Asset allocation overview", BoS's has "Investment Assets"
plus "Total Net Asset Value", UBS's has the "Portfolio number" header plus a "Gross assets"
row. First page that matches wins; the rest of the document is ignored.

**Step 2 — rebuild the table rows.** Words that sit at the same height on the page belong to
the same visual row, so the tool groups them into lines: `Liquidity  95,000.00  48.67 % ...`.
Each line splits into a **label** (the words before the first number) and its **numbers**,
read left to right. The first number on a row is the one in the leftmost money column, which
for all three banks is the current-month value we want.

**Step 3 — apply each bank's rule.** This is the part that was tuned against the supervisor's
green-boxed guide:

- **LGT** — Net NAV is the "Total" row of the allocation table. Every NEGATIVE line item
  (Credit, Derivatives, and so on) is collected, and Gross = Net with those added back, so
  Gross is always at least Net. That arithmetic is written into Excel as a formula, not a
  number, so it can be audited later. Liquidity is its own row in the same table.
- **BoS** — Gross is the "Investment Assets" row, Net is "Total Net Asset Value". Negative
  numbers print in parentheses, `(85,000.00)`, and the tool reads those as minus — an
  overdrawn client genuinely has a negative Net. If a Liabilities/Overdrafts section exists
  it is captured too, purely to power the check formula.
- **UBS** — the trap here is that UBS bundles several portfolios into one statement. The
  header's "Total gross/net assets" figures cover the WHOLE relationship, so they are the
  wrong numbers. The portfolio number ends in a suffix, e.g. `546-123456-03`, and that
  suffix names the one table to read: the tool finds the "Portfolio 03" section and takes
  its "Gross assets", "Net assets" and "Liquidity" rows, always the **Market value** column
  (the first number). Numbers use spaces as thousand separators (`14 500 000`), which the
  tool re-joins.

**Step 4 — the safety net for scanned PDFs.** Occasionally a PDF is really just a photograph
of a page (a scan, or a screenshotted page saved as PDF) with no text stored inside. For
those, the tool renders the page to an image and sends it to the **Gemini API**, which
reads it and sends back every printed row as data (this is the one Version-2 change —
Version 1 did this with a slow local OCR engine at ~10 seconds a page; the API takes a
few seconds). Statements downloaded from a bank portal normally never need this.

**Why a "static" program can do this reliably:** each bank's format is standardised and does
not change month to month. The tool never guesses — it anchors on the exact printed labels
("Total Net Asset Value", "Gross assets", "Client number:"), and when a label is missing it
writes a note in the Flags column instead of inventing a number. Every figure it does write
is backed by a screenshot of the exact spot it came from, so a human stays the final check.

## 8. Re-doing a row (if she deletes something by mistake)

If she accidentally deletes rows in the Excel and wants them back, there are two ways:

**Her easy way:** delete that bank's PDF from its inbox folder, then drop the same PDF back
in. A freshly dropped file is treated as "do this again," so the row gets rebuilt. (This was a
deliberate change. Before, the tool would have skipped a file it had already seen.)

**The bulk way (for Warren or power use):** run `python run_all_once.py --redo`, which rebuilds every row from whatever PDFs are still in the inboxes, even ones already done.

> [!note] Why re-doing is safe
> Each PDF maps to one row by its filename, so re-doing overwrites that same row rather than creating a duplicate. You cannot end up with the same statement counted twice.

## 9. Stopping and starting

To **stop** the tool, close the black window the watcher runs in (or press Ctrl+C inside it).
On a Windows office PC that window is usually **PowerShell** (the older name is Command Prompt).
Closing it stops the watching. To start again the next day, double-click `run_watcher.bat`.

If she would rather run on demand instead of leaving a window open, `run_once.bat` processes
whatever is in the inboxes right now and then closes.

## 10. Things to watch for

- **Validation status:** the parsers are now validated against five REAL statements supplied
  by the supervisor (two LGT including one with add-backs, two BoS including an overdrawn
  account with liabilities and a negative Net NAV, and a multi-portfolio UBS). Every figure
  matched the supervisor's green-boxed guide to the cent, including through the scanned-page
  (API OCR) path.
  The real samples stay in the local `samples/` folder (never committed — client data) and
  `tests/validate_samples.py` re-checks all of them in one run.
- **Excel or Word open:** if the master Excel or a bank's Word file is open when a PDF is
  dropped, the write fails. The tool logs a clear message; just close the file and re-drop.
- **A blank cell + a note in Flags** means the tool could not find that figure's label on
  the page. It never guesses. Check the statement, and if the bank genuinely changed its
  wording, the parser needs a one-line update.
- **Scanned/image-only PDFs** need the Gemini API key in `api_key.txt` (and internet).
  Without it the tool flags exactly that, and the fix is to paste the key (verify with
  `check_api.bat`) or to re-download a text-based statement from the bank portal.
- **A row whose Flags column starts with "FAILED"** means that PDF could not be read at all,
  and the flag text says why and what to do. The usual causes: the PDF is
  password-protected (open it with the password, print/save it as a new PDF, drop the
  unlocked copy in), the API key hasn't been pasted in, or the internet was down.
  Failed files are retried automatically on every run, so after fixing the cause she just
  runs the tool again — no special steps. A bank tab can never be silently empty: every PDF
  the tool touches gets a row, even when reading it failed.

## 11. Where the settings live

Everything tweakable sits in `config.py`: the folder paths, the screenshot sharpness, and the
management fee rate (`MGMT_FEE_RATE`, currently unset until we agree the real rule against a
real statement). The output workbook is `output\nav_master.xlsx`.

---

Related: the repo `README.md` (canonical user guide) · [[FOR_COLLEAGUE_AI]] · [[STATUS]]
