"""Checks the Gemini API key works, without touching any client PDF.

Run it after pasting the company key into api_key.txt (double-click
check_api.bat on Windows). It sends a tiny "reply OK" request — no client
data — and prints exactly what is wrong if anything fails.
"""
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import config


def main() -> int:
    config.ensure_api_key_file()
    key = config.get_gemini_api_key()
    if not key:
        print()
        print("NO API KEY SET.")
        print(f"  1. Open this file in Notepad:  {config.API_KEY_FILE}")
        print("  2. Delete the placeholder line and paste the company's Gemini API key.")
        print("  3. Save the file and run this check again.")
        return 1

    print(f"Key found ({key[:6]}...{key[-4:]}). Testing model "
          f"'{config.GEMINI_MODEL}'...")
    body = json.dumps({
        "contents": [{"parts": [{"text": "Reply with the single word OK."}]}],
        "generationConfig": {"temperature": 0},
    }).encode("utf-8")
    url = ("https://generativelanguage.googleapis.com/v1beta/models/"
           f"{config.GEMINI_MODEL}:generateContent")
    req = urllib.request.Request(
        url, data=body,
        headers={"Content-Type": "application/json", "x-goog-api-key": key},
        method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        text = payload["candidates"][0]["content"]["parts"][0]["text"].strip()
        print(f"SUCCESS — the API answered: {text!r}")
        print("The key works. Scanned PDFs will now be read through the API.")
        return 0
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            detail = e.read().decode("utf-8", "replace")[:400]
        except Exception:
            pass
        print(f"FAILED — the API rejected the request (HTTP {e.code}).")
        if e.code in (400, 401, 403):
            print("  The key looks wrong or inactive. Re-copy it into "
                  "api_key.txt (no extra spaces or line breaks) and check the "
                  "company subscription is active.")
        elif e.code == 404:
            print(f"  The model name '{config.GEMINI_MODEL}' was not found — "
                  "it may need updating in config.py.")
        elif e.code == 429:
            print("  Rate limit hit — wait a minute and try again.")
        print(f"  API said: {detail}")
        return 1
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        print(f"FAILED — could not reach the Gemini API at all ({e}).")
        print("  Check the internet connection / company proxy, then try again.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
