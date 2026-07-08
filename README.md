# 🏦 Bank NAV Automation — API edition

> **Drop a bank statement PDF into a folder. Get the NAV figures in Excel — each one backed by a screenshot of the exact spot it came from.**
> Reads **LGT · Bank of Singapore · UBS** client statements, so you verify numbers by eyeballing, never by re-typing.

[![Runs on Windows](https://img.shields.io/badge/runs%20on-Windows-0ea5e9)](#-setup--use-windows)
[![Python 3.12](https://img.shields.io/badge/Python-3.12-3776ab)](https://www.python.org/downloads/release/python-3120/)
[![Banks: LGT | BoS | UBS](https://img.shields.io/badge/banks-LGT%20%7C%20BoS%20%7C%20UBS-8b5cf6)](#-what-it-does-and-doesnt)
[![Scans → Gemini API](https://img.shields.io/badge/scans-Gemini%20API-f59e0b)](#-how-it-works-the-mechanism)
[![Privacy: local-first](https://img.shields.io/badge/privacy-local--first-22c55e)](#-privacy--data-safety)

<sub>This is **Version 2** of [pinnacle-invoice-automation](https://github.com/warrenlimzf/pinnacle-invoice-automation). The one difference: scanned pages are read by the company's Gemini API instead of a slow local OCR engine. Everything else is identical.</sub>

---

## ⏱️ 30-second version

| | |
|---|---|
| **What is it?** | A desktop tool that reads private-bank NAV statements into one master Excel + a screenshot Word doc. |
| **Which banks?** | 🟣 LGT · 🔵 Bank of Singapore · 🟠 UBS. |
| **How do I set it up?** | Download ZIP → `setup.bat` → paste the company's API key → `check_api.bat`. [Steps below ⬇️](#-setup--use-windows) |
| **How do I use it?** | Drop each bank's PDF into its inbox folder. That's the whole job. |
| **Is client data safe?** | Yes. Normal statements never leave your PC; only *scanned* pages go to the company's Gemini API. [Details](#-privacy--data-safety) |

---

## 📖 Table of contents

1. [What it does (and doesn't)](#-what-it-does-and-doesnt)
2. [Setup & use (Windows)](#-setup--use-windows)
3. [How it works (the mechanism)](#-how-it-works-the-mechanism)
4. [Which files were read (and which weren't)](#-which-files-were-read-and-which-werent)
5. [Troubleshooting](#-troubleshooting)
6. [Privacy & data safety](#-privacy--data-safety)
7. [For developers / AI assistants](#-for-developers--ai-assistants)
8. [More documentation](#-more-documentation)

---

## 🧭 What it does (and doesn't)

**✅ This IS:**
- A tool that pulls six fields off each statement — **Statement Date, Account No, Currency, Gross NAV, Net NAV, Liquidity** — into one Excel workbook (one tab per bank, one row per statement).
- **Auditable by eye:** every number it writes comes with a screenshot of the exact spot on the PDF, saved into that bank's Word doc. You check by glancing, not by re-keying.
- A **draft / staging area** you copy *as values* into your own master file.

**❌ This is NOT:**
- Not a cloud service or a website — it runs on your own Windows PC.
- Not the final deliverable — the Excel/Word here are a draft to copy from.
- Not a guesser — if a label isn't found, the cell stays blank and says so. It never invents a number, and it never moves, renames or deletes your PDFs.

---

## 🧰 Setup & use (Windows)

### 1️⃣ Install Python — *one time ever*
Download **Python 3.12** (the "Windows installer (64-bit)") from the
[official page](https://www.python.org/downloads/release/python-3120/) and run it.
On the first screen, **tick "Add python.exe to PATH"** before clicking Install. That box matters.

> Everything here is **free, open-source software — nothing to buy.** (Gemini API usage runs on the company's existing subscription.) Already installed Python once? Skip straight to step 2.

### 2️⃣ Download the tool — *repeat on every update*
1. Open the [repository](https://github.com/warrenlimzf/pinnacle-invoice-automation-api) (no account needed).
2. Green **Code** button → **Download ZIP** → right-click → **Extract All**. Put it somewhere easy (e.g. Documents).
3. Upgrading? Copy your PDFs from the old `banks\<bank>\inbox\` folders into the new ones — **and copy your old `api_key.txt` across** so you don't re-paste the key.

### 3️⃣ Run setup — *once per copy*
Double-click **`setup.bat`**. It installs the bundled libraries **offline** from `vendor\` (no internet needed) and creates an empty **`api_key.txt`**. Close the window when it says it's done.

### 4️⃣ Paste the company's API key — *once per copy*
1. Open **`api_key.txt`** in Notepad.
2. Delete the placeholder line and **paste the company's Gemini API key** — one line, no stray spaces. Save and close.
3. Double-click **`check_api.bat`** — it sends one tiny test request (no client data) and prints **SUCCESS**, or tells you exactly what's wrong.

> 🔑 The key stays in that file on your PC. It is never committed, uploaded or shared (`api_key.txt` is on the ignore list). Key changed? Just paste the new one over it.

### 5️⃣ Daily use
| Mode | How |
|---|---|
| **Automatic** (recommended) | Double-click **`run_watcher.bat`**, leave the window open, and drop each PDF into `banks\LGT\inbox\` · `banks\BoS\inbox\` · `banks\UBS\inbox\`. Each file is read the moment it lands. |
| **On demand** | Put the PDFs in the inboxes first, then double-click **`run_once.bat`**. |

Text-layer statements (BoS, most UBS) finish in under a second and never touch the internet. Scanned statements (typically LGT) go page-by-page through the Gemini API at a **few seconds per page**, with progress printed the whole way. That cost is paid **once per file, ever** — read files are remembered and skipped next time.

### 6️⃣ Check, then copy into your master file
1. Open `output\nav_master.xlsx` next to that bank's Word doc (`banks\<bank>\<bank>_verification.docx`, which holds the screenshots).
2. Glance that each row matches its screenshot. **Blue** numbers were read straight off the PDF; **black** cells are live formulas the tool built (e.g. LGT's Gross NAV = Net NAV with negative line items added back, each tagged with its name). On scanned pages the crop is *approximate* (the API returns no pixel positions), so it shows the right area rather than the exact row — the numbers themselves are exact.
3. Copy the **A:F block** into your own master file, pasting **as values** (Paste Special → Values) so formulas become plain numbers.

> The Excel/Word here are a **draft**, never the final deliverable. Your original PDFs are **never moved, renamed or deleted.**

---

## 🔍 How it works (the mechanism)

**Two kinds of PDF, two reading paths.** A normal PDF stores its text as data — the file literally says which characters sit where — and the tool copies that out in microseconds, fully locally (every BoS statement). A *scanned* PDF stores each page as one photograph: millions of pixels, no text anywhere. For those pages only, the tool renders the page to an image and sends it to the **Gemini API**, which returns every line as structured JSON — *"this row says Net assets, 12 051 656, at this height."* Python rebuilds those lines into positioned text and hands them to the same parsers V1 uses. V1 did this with a local OCR engine at ~10s/page; the API does it in a few seconds with no heavy local install.

**Finding the numbers — each bank has its own parser, keyed to its real layout:**

| Bank | How the figures are read |
|---|---|
| 🟠 **UBS** | A statement can bundle several portfolios; the portfolio number's suffix (e.g. `…-03`) selects the right "Portfolio 03" table, and Gross / Net / Liquidity come from its **Market value** column. Whole-relationship header totals are ignored when a portfolio table exists. |
| 🔵 **BoS** | Gross = "Investment Assets", Net = "Total Net Asset Value". Negatives print in parentheses; an overdrawn account can genuinely be negative, captured with an audit formula (Gross + Liabilities − Net = 0) in the Check column. |
| 🟣 **LGT** | The statement shows only Net NAV ("Total"). The tool collects the negative line items (Credit, Derivatives, …) and writes Gross NAV as a **live Excel formula** adding them back, so the derivation is auditable cell by cell. |

**Nothing is guessed, and nothing fails silently.** If a label can't be found, the cell stays blank and the **Flags** column says so. If a whole PDF can't be read, the tool writes a row whose flag starts with **FAILED** and states the exact reason and fix — a bank tab is never silently empty. Every number that *is* written has a screenshot proving where it came from.

---

## 🗂️ Which files were read (and which weren't)

Statements are read **strictly one at a time**: a single unreadable file never blocks the others, and a file already written to the Excel is never read again. That's what makes repeat runs instant — and what stops paying to re-OCR the same scanned page twice.

So you never have to wonder what did or didn't go in. After **every** run the tool writes **`output\NEEDS_REUPLOAD.txt`**:

- ✅ If everything read cleanly, it says so.
- ⚠️ Otherwise it lists **each file that did *not* make it into the Excel**, the reason, and the fix.

The protocol when a file is listed is simple:

> **1.** Remove that file from its inbox folder → **2.** fix the cause (re-download a text-based copy, close the Excel if it was open, sort out the API key) → **3.** drop the corrected copy back into the same folder.

The same list also prints in the run window. Re-dropping only re-reads *that one file* — everything already in the Excel is left untouched.

<sub>Under the hood, two small records sit next to the tool: `processed_index.json` (files that are done) and `failed_index.json` (files still needing attention). You never open those — the `.txt` is the human view.</sub>

---

## 🩺 Troubleshooting

*Every problem seen so far, and the fix.*

| What you see | What it means | What to do |
|---|---|---|
| **Some statements are missing from the Excel** after a run | One or more files couldn't be read that run — never dropped silently. | Open **`output\NEEDS_REUPLOAD.txt`**: it names each file, the reason, and the fix. Remove and re-drop **only** those files; the rest stays put. |
| *"page N … had no text layer — read it through the Gemini API instead"* | **Not an error.** That statement is a scan; the API is reading it at a few seconds per page. | Wait — the window prints progress the whole way. |
| Flag: **no API key is set — open api_key.txt** | The key hasn't been pasted in yet (or the placeholder is still there). | Paste the company's key into `api_key.txt`, save, run `check_api.bat`, then run again — failed files retry automatically. |
| Flag: **the Gemini API rejected the key (HTTP 403/400)** | Key pasted incompletely, has stray spaces/line breaks, or the subscription is inactive. | Re-copy the key carefully into `api_key.txt` and verify with `check_api.bat`. Still failing? Ask whoever manages the company's Gemini subscription. |
| Flag: **could not reach the Gemini API** | No internet, or a proxy/firewall is blocking `generativelanguage.googleapis.com`. | Check the connection, then run again. (Text-layer statements still process fine offline.) |
| Flag starts with **FAILED — the PDF is password-protected** | Bank portals often lock PDFs; a locked PDF can't be read by any tool. | Open it with its password, **print/save as a new PDF** (removes the lock), drop the unlocked copy in. |
| *"Permission" / "file is open"* | Excel or Word has the output open, so Windows blocks writing. | Close it, drop the PDF in again (or re-run). |
| A blank cell + a note in Flags | That figure's label wasn't found — the tool never guesses. | Check the statement; if the bank truly changed its wording, the parser needs a small update (see next row). |
| A statement still extracts wrongly after all of the above | The bank uses a layout the parser hasn't met yet. | Run **`diagnose.bat`** (or `diagnose.bat UBS`). It dumps what the tool sees to `logs\diagnose\*.txt` — send the relevant `.txt` to the developer so the parser is fixed against real wording. These dumps stay on your computer. |

> 📄 Full run log: `logs\automation.log` — every action and error is recorded there.

---

## 🔒 Privacy & data safety

- **Text-layer statements never leave your computer.** Every BoS statement and most UBS statements are read 100% locally with PyMuPDF.
- **Only pages that are *pictures* of a statement** (scans, typically LGT) are sent to Google's Gemini API — under the **company's own subscription**, mentor-approved. No other cloud parser is ever used.
- **Nothing sensitive is ever committed** to this public repo: real statements, generated Excel/Word outputs, `processed_index.json` / `failed_index.json`, the `NEEDS_REUPLOAD.txt` report, and the **API key** are all gitignored.
- **Your originals are sacred.** The tool never moves, renames or deletes a statement PDF. De-duplication is by content hash, so nothing is ever touched on disk.

---

## 👩‍💻 For developers / AI assistants

- **AI opening this folder?** Start at **[docs/FOR_COLLEAGUE_AI.md](docs/FOR_COLLEAGUE_AI.md)** — reading order, hard rules, and the debug journal of solved issues.
- **Code layout:** `banks/<bank>/parser.py` (per-bank logic) · `shared/` (reader, the Gemini OCR module `shared/readers/gemini_ocr.py`, Excel/Word writers, the read-tracking `shared/index.py`) · `config.py` (all paths/settings incl. the API key file + model name) · `watcher.py` + `run_all_once.py` (entry points) · `check_api.py` (key self-test).
- **Tests:** `python tests/test_failure_modes.py` runs anywhere (synthetic PDFs, **mocked** API — no key or internet needed). `python tests/validate_samples.py` checks all real samples to the cent but needs the local, **never-committed** `samples/` folder (and a real key for the scanned samples).
- **Hard rules:** text-layer statements stay local; **only scanned pages** go to the Gemini API, on the company key; originals are never moved/deleted; no client data or key is ever committed.

---

## 📚 More documentation

| Doc | What's in it |
|---|---|
| 📘 [docs/RULEBOOK.md](docs/RULEBOOK.md) | The full plain-English playbook — the mechanism explained for non-programmers. |
| 📝 [HANDOFF.md](HANDOFF.md) | The day-to-day operator crib sheet (what to copy where). |
| 🤖 [docs/FOR_COLLEAGUE_AI.md](docs/FOR_COLLEAGUE_AI.md) | For any AI assistant opened in this folder — start here. |
| 📊 [docs/STATUS.md](docs/STATUS.md) | Project state and the debug journal. |

<sub>Built by [Warren Lim Zhan Feng](https://github.com/warrenlimzf) for internal use at Pinnacle. Not affiliated with Anthropic or Google; "Gemini" is a trademark of Google.</sub>
