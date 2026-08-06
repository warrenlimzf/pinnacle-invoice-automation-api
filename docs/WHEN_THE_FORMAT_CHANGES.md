# When a bank changes its statement format

Banks redesign their statements every so often. UBS did it in June 2026: it moved the
percentage column to the front of the table and printed a second table beside it, and
suddenly the tool was writing `100.00` into Gross NAV instead of the real figure.

**You do not need the developer for this.** Everything the tool knows about a bank lives in
one small file, and the prompt below tells your AI assistant exactly how to update it and
how to prove the update worked. This page is the whole procedure.

---

## Signs the format changed

Any of these, on statements from one bank only, when the same bank used to work fine:

- A figure is obviously wrong — a small number like `100`, `16.44` or `-17.81` where
  millions should be.
- A cell is blank and the **Flags** column says something like *"Net NAV not found"* or
  *"Could not find the … overview page"*.
- A flag saying **Gross + Liabilities does not equal Net** — the tool caught itself.
- The Word verification doc's screenshot points at the right table, but the Excel number
  next to it doesn't match what you can read in that screenshot.

If instead the flag starts with **FAILED**, that is not a format change — it's a locked,
scanned or unreadable PDF, and `output\NEEDS_REUPLOAD.txt` tells you the fix.

---

## Step 1 — capture what the tool sees

1. Put the problem statement in its bank's inbox folder (e.g. `banks\UBS\inbox\`).
2. Double-click **`diagnose.bat`**, or run `diagnose.bat UBS` for one bank only.
3. It writes a plain-text dump to **`logs\diagnose\`** — one `.txt` per PDF. That file is
   the statement as the tool reads it, and it is what your AI needs.

> The dump contains real client figures. It stays on your computer. Only paste it into an
> AI assistant your firm has approved for client data — the same rule as the statements
> themselves. If in doubt, ask first, and blank out the account numbers before pasting.
>
> (This is the API edition: scanned pages are read through the company's Gemini API, so a
> scan's *image* does go to Google on the firm's own subscription. Statements that contain
> real text are still read entirely on your PC, and nothing else — no dump, no Excel, no
> output file — ever leaves the machine.)

## Step 2 — hand your AI the prompt below

Open the project folder in your AI assistant (Claude Code, Copilot, Cursor, ChatGPT with the
folder attached — any of them), then paste the prompt from the next section, filling in the
three blanks. Attach or paste **the `.txt` dump** and, if you can, **the page of the PDF**
that shows the table (a screenshot is fine).

## Step 3 — check what it did

Do not take "done" on trust. The prompt tells the AI to run the three test suites and show
you the output. What you should see:

```
All UBS layout tests passed.
All failure-mode tests passed.
All good.                      <- this line means the real sample statements still read correctly
```

Then drop the problem statement in again and check the number in the Excel against the
screenshot in the Word doc, exactly as you always do. **You are still the final check.**

---

## The prompt — copy everything in the box

Fill in the three `[...]` blanks, and delete the parts of the last line that don't apply.

```text
You are working inside the pinnacle-invoice-automation project on my computer. It reads
bank statement PDFs and writes the NAV figures into an Excel file. One bank has changed
its printed statement layout and the parser now reads the wrong numbers. Please fix it.

WHAT CHANGED
- Bank: [UBS / BoS / LGT]
- Version: this is the API edition (pinnacle-invoice-v2-api), which reads scanned pages
  through the company's Gemini API. Note the API returns each row as a list of cells with
  an estimated vertical position, so a rule that depends on exact page coordinates will
  NOT work here - see shared/readers/gemini_ocr.py.
- What is wrong in the Excel: [e.g. "Gross NAV shows 100.00 and Net NAV is blank, for the
  June statement onwards. It should be 14,600,000 and 12,000,000."]
- The statement as the tool sees it is in: [paste the logs\diagnose\....txt file here, or
  attach it]

BEFORE YOU CHANGE ANYTHING, READ THESE FILES IN THIS ORDER — read only these, do not scan
the whole folder:
1. docs/FOR_COLLEAGUE_AI.md   - the hard rules and the debug journal of issues already
                                solved. Do not re-break anything in that journal.
2. banks/<BANK>/parser.py     - the only file that knows this bank's layout. Its docstring
                                describes every layout the tool already handles.
3. shared/extract.py          - the shared helpers for finding rows and reading numbers.
4. tests/test_ubs_layouts.py  - how a layout change is pinned down with a test.

HOW TO DO IT
- Work from the diagnose dump, never from memory or assumption about how the bank
  "probably" prints things. If the dump does not show something you need, tell me what is
  missing instead of guessing.
- Compare the new layout against the layouts already described in the parser's docstring,
  and tell me in plain English what actually changed - which columns moved, appeared or
  disappeared, and which row labels were reworded.
- THE OLD LAYOUT MUST KEEP WORKING. I still process older statements every month. Make the
  parser handle both; never replace one layout with the other.
- Prefer a rule based on something meaningful over a rule based on position. "The money
  column is the one printed in whole units, and the asset table is the left-hand one"
  survives a redesign; "the second number on the row" does not. Explain which fact you
  relied on and why it will still be true next quarter.
- Never invent or estimate a figure. If a value cannot be found, the correct behaviour is a
  blank cell plus a note in the Flags column - that is deliberate, keep it.
- The only approved outside service is the company's Gemini API, and only for pages that
  are scanned images, which the tool already handles. Do not upload the statement, the
  dump, or any client figure anywhere else - no other website, API or cloud parser.
- Do not delete, move or rename any file, and do not touch the PDFs in the inbox folders.
- Keep the comments and docstrings in the code up to date with what you changed, in the
  same plain style they already use, and describe the new layout in the parser's docstring
  the way the existing ones are described.

PROVE IT WORKS - I will not accept "it should work now"
- Add a test to tests/test_ubs_layouts.py that reproduces the NEW layout and asserts the
  correct figures, following the pattern already in that file. Keep the existing tests.
- Then run all three suites and show me the actual output:
      python tests/test_ubs_layouts.py
      python tests/test_failure_modes.py
      python tests/validate_samples.py
  The first two must pass. The last one reads the real sample statements and needs the
  Gemini API key set for the scanned ones - if there is no key on this machine it will stop
  with a message saying so, which is fine; say so rather than deleting the test. Any sample
  it DOES read must still come out correct: a failure there means your change broke an
  older layout and is not finished.
- tests/test_failure_modes.py also replays a full scanned statement through a mocked Gemini
  response. If you taught the parser a new layout, add that layout to those mocked rows too
  (see UBS_2026_06_LINES), so the fix is proven through the API path, not just locally.
- Show me a before/after of the figures for my statement: what the parser returned before
  your change and what it returns now.

WHEN IT WORKS
- Add a short entry to the debug journal in docs/FOR_COLLEAGUE_AI.md, in the same style as
  the entries already there: what I saw, what the real cause was, what you changed, and
  what a future AI should not undo.
- Update the bank's row in README.md and its section in docs/RULEBOOK.md if the description
  there is now out of date.
- Tell me in one paragraph, in plain English with no jargon, what was wrong and what you
  changed - I need to be able to explain it to my supervisor.

This project exists in two versions and the fix usually belongs in BOTH:
pinnacle-invoice-v1-python (reads scans on my own PC) and pinnacle-invoice-v2-api (reads
scans through the company's Gemini API). They are separate copies, not linked, so the same
change has to be applied to each one and the tests run in each. I have opened:
[the V1 folder / the V2 folder / both folders].
```

---

## If the AI gets stuck

Send Warren the `logs\diagnose\*.txt` file and a screenshot of the statement page. A layout
the parser has never met is a small fix against the real wording — but it has to be made
against the real wording, which is exactly what that dump is.
