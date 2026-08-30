"""Fetch official Groww help/pricing pages as plain-text knowledge sources.

Only official Groww public pages (groww.in/help/*, groww.in/pricing) are used.
Saves cleaned text into data/documents and appends manifest rows.

Usage: python scripts/fetch_groww_help.py
"""
from __future__ import annotations

import csv
import re
import sys
from datetime import date
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

DOCS = ROOT / "data" / "documents"
MANIFEST = ROOT / "data" / "manifest.csv"

PAGES = [
    ("https://groww.in/help/mutual-funds/mf-sip/how-to-cancel-my-sip",
     "Groww Help - How can I cancel an ongoing SIP"),
    ("https://groww.in/help/mutual-funds/searchable/what-are-the-charges-for-mutual-fund-investments--93",
     "Groww Help - What are the charges for mutual fund investments"),
    ("https://groww.in/help/mutual-funds/order/what-is-my-current-order-status",
     "Groww Help - What is my current order status"),
    ("https://groww.in/help/mutual-funds/order/how-to-withdraw-redeem-4",
     "Groww Help - How do I withdraw or redeem from a mutual fund"),
    ("https://groww.in/pricing",
     "Groww Pricing - Brokerage Charges & Pricing"),
]

_TAG_RE = re.compile(r"<(script|style|noscript)[^>]*>.*?</\1>", re.DOTALL | re.IGNORECASE)
_HTML_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\n{3,}|[ \t]{2,}")


def html_to_text(html: str) -> str:
    txt = _TAG_RE.sub(" ", html)
    # keep line breaks where block tags were
    txt = re.sub(r"</(p|div|li|h[1-6]|tr)>", "\n", txt, flags=re.IGNORECASE)
    txt = _HTML_RE.sub("", txt)
    import html as htmllib

    txt = htmllib.unescape(txt)
    lines = [ln.strip() for ln in txt.splitlines()]
    return _WS_RE.sub("\n", "\n".join(ln for ln in lines if ln))


def main() -> None:
    DOCS.mkdir(exist_ok=True)
    today = date.today().isoformat()
    new_rows = []

    existing_urls = set()
    with open(MANIFEST, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
        fields = rows and list(rows[0].keys()) or [
            "file_name", "title", "scheme", "organization", "document_type",
            "document_date", "effective_date", "source_url", "source_id"]
        for r in rows:
            existing_urls.add(r.get("source_url", ""))

    for url, title in PAGES:
        if url in existing_urls:
            print(f"  already in manifest: {url}")
            continue
        try:
            resp = httpx.get(url, timeout=30, follow_redirects=True,
                             headers={"User-Agent": "Mozilla/5.0 (FAQ assistant corpus builder)"})
            if resp.status_code != 200:
                print(f"  ! HTTP {resp.status_code}: {url}")
                continue
            text = html_to_text(resp.text)
            if len(text) < 300:
                print(f"  ! too little content: {url}")
                continue
            fname = f"GROWW_HELP_{abs(hash(url)) % 10**8}.txt"
            (DOCS / fname).write_text(
                f"{title}\nSource: {url}\nFetched: {today}\n\n{text}", encoding="utf-8"
            )
            rows.append({
                "file_name": fname,
                "title": title,
                "scheme": "",
                "organization": "Groww",
                "document_type": "GROWW_HELP",
                "document_date": today,
                "effective_date": "",
                "source_url": url,
                "source_id": "",
            })
            print(f"  fetched: {title} ({len(text)} chars)")
        except Exception as exc:  # noqa: BLE001
            print(f"  ! failed {url}: {exc}")

    with open(MANIFEST, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "file_name", "title", "scheme", "organization", "document_type",
            "document_date", "effective_date", "source_url", "source_id"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"manifest updated: {len(rows)} total rows")


if __name__ == "__main__":
    main()
