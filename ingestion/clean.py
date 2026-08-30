"""Cleaning: header/footer removal, boilerplate dedup, whitespace normalization."""
from __future__ import annotations

import re
from collections import Counter

from .extract import RawPage

_URL_RE = re.compile(r"https?://\S+")
_WS_RE = re.compile(r"[ \t]+")
_MULTI_NL_RE = re.compile(r"\n{3,}")
_PAGE_NUM_RE = re.compile(r"^\s*(page\s*)?[-–—|]?\s*\d{1,4}\s*[-–—|]?\s*$", re.IGNORECASE)

# lines that are almost always running headers/footers in HDFC docs
_NOISE_PATTERNS = [
    r"^disclaimer.*",
    r"^mutual fund investments are subject to market risks.*",
    r"^read all scheme related documents carefully.*",
    r"^visit us at .*",
    r"^www\.hdfcfund\.com.*",
    r"^customer service.*",
    r"^toll free.*",
    r"^\s*cin:.*",
    r"^registered office.*",
    r"^hdfc mutual fund.*hdfc house.*",
    r"^continued\s*\.{3,}$",
]


def _is_noise(line: str) -> bool:
    low = line.strip().lower()
    if not low:
        return True
    if _PAGE_NUM_RE.match(line):
        return True
    return any(re.match(p, low) for p in _NOISE_PATTERNS)


def normalize_text(text: str) -> str:
    text = text.replace("\u00a0", " ").replace("\r\n", "\n").replace("\r", "\n")
    # strip NUL and other C0 control chars (Postgres rejects \u0000 in text)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", text)
    # common pdf ligature/encoding artifacts
    for bad, good in (("\uf06c", "-"), ("\uf0b7", "-"), ("\uf0d8", "-"), ("\uf020", " ")):
        text = text.replace(bad, good)
    lines = [_WS_RE.sub(" ", ln).strip() for ln in text.split("\n")]
    text = "\n".join(lines)
    text = _MULTI_NL_RE.sub("\n\n", text)
    return text.strip()


def detect_and_strip_headers_footers(pages: list[RawPage]) -> list[RawPage]:
    """Lines repeated on many pages (top or bottom of page) are boilerplate."""
    if len(pages) < 5:
        return [RawPage(page=p.page, label=p.label, text=normalize_text(p.text), is_table=p.is_table, meta=p.meta) for p in pages]

    top_counter: Counter[str] = Counter()
    bottom_counter: Counter[str] = Counter()
    for p in pages:
        lines = [ln.strip() for ln in p.text.split("\n") if ln.strip()]
        if not lines:
            continue
        for ln in lines[:2]:
            if 10 < len(ln) < 120:
                top_counter[ln] += 1
        for ln in lines[-2:]:
            if 10 < len(ln) < 120:
                bottom_counter[ln] += 1

    threshold = max(3, int(len(pages) * 0.4))
    boilerplate = {ln for ln, c in top_counter.items() if c >= threshold}
    boilerplate |= {ln for ln, c in bottom_counter.items() if c >= threshold}

    cleaned = []
    for p in pages:
        kept = []
        for ln in p.text.split("\n"):
            s = ln.strip()
            if s in boilerplate:
                continue
            if _is_noise(s):
                continue
            kept.append(ln)
        cleaned.append(
            RawPage(
                page=p.page,
                label=p.label,
                text=normalize_text("\n".join(kept)),
                is_table=p.is_table,
                meta=p.meta,
            )
        )
    return [c for c in cleaned if c.text]
