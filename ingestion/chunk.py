"""Section-aware semantic chunking with topic tagging.

Never blindly chunks every N characters: content is first split into
heading-delimited sections; long sections are then split at sentence
boundaries with a small overlap while keeping tables intact.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .clean import detect_and_strip_headers_footers
from .config import CHUNK_OVERLAP_CHARS, CHUNK_TARGET_CHARS
from .extract import RawPage, extract_file

# ---------------------------------------------------------------------------
# Topic taxonomy and keyword mapping (canonical topics used across the app)
# ---------------------------------------------------------------------------
TOPIC_KEYWORDS: dict[str, list[str]] = {
    "investment_objective": ["investment objective", "objective of the scheme"],
    "investment_strategy": ["investment strategy", "investment approach", "where will the scheme invest", "portfolio strategy"],
    "asset_allocation": ["asset allocation", "indicative asset allocation", "pattern of allocation"],
    "minimum_investment": ["minimum application amount", "minimum amount", "minimum purchase", "minimum investment"],
    "sip": ["systematic investment plan", " sip ", "sip facility", "sip details", "starting an sip", "modifying an sip"],
    "expense_ratio": ["total expense ratio", "ter ", "expense ratio", "recurring expenses", "management fees"],
    "exit_load": ["exit load", "exit charge", "contingent deferred sales charge", "cdsc", "load structure", "type of load"],
    "benchmark": ["benchmark", "tier i benchmark", "tier ii benchmark"],
    "riskometer": ["riskometer", "risk-o-meter", "risk o meter", "scheme riskometer", "potential risk class"],
    "fund_manager": ["fund manager", "fund management team", "managed by", "name of the fund manager"],
    "tracking_error": ["tracking error", "tracking difference"],
    "replication": ["replication", "sampling", "full replication"],
    "lock_in": ["lock-in", "lock in period", "locked-in"],
    "plans_options": ["plans and options", "options offered", "growth option", "idcw", "direct plan", "regular plan", "plans & options"],
    "nav": ["net asset value", "nav applicability", "applicable nav"],
    "aum": ["assets under management", "aum"],
    "redemption": ["redemption", "repurchase", "withdrawal", "swp", "systematic withdrawal"],
    "purchase": ["purchase", "subscription", "lump sum", "application amount"],
    "switch": ["switch", "switching"],
    "cutoff_time": ["cut-off timing", "cutoff timing", "cut off timing", "cut-off time", "business day"],
    "folio_statement": ["folio", "account statement", "consolidated account statement", "cas ", "statement of account"],
    "tax_capital_gains": ["capital gains", "capital gain", "taxation", "tax treatment", "tds"],
    "tax_80c": ["section 80c", "80c", "tax benefit", "income tax act"],
    "stamp_duty": ["stamp duty", "stt ", "securities transaction tax"],
    "elss": ["elss", "equity linked savings", "tax saver"],
    "categorization": ["categorization", "categorisation", "sebi circular", "scheme categorization"],
    "scores": ["scores", "grievance redressal", "complaint", "ogms"],
    "charges_fees": ["charges", "fees", "load structure", "transaction charges", "statutory levy"],
    "performance": ["performance", "returns since inception", "cagr", "absolute return", "compound annualized return"],
    "general": [],
}

_HEADING_RE = re.compile(
    r"^(?:(\d{1,2}(?:\.\d{1,2})*)[.)]?\s+)?([A-Z][A-Z0-9 ,&/\-()'%.:]{6,120}|"
    r"[A-Z][A-Za-z0-9 ,&/\-()':.\-]{4,120})\s*$"
)

_KNOWN_HEADINGS = [
    "investment objective", "investment strategy", "asset allocation pattern",
    "asset allocation", "exit load", "total expense ratio", "benchmark",
    "riskometer", "fund manager", "fund managers", "lock-in", "plans and options",
    "options available", "minimum application amount", "redemption", "switch",
    "taxation", "load structure", "fundamentals of the scheme", "features of the scheme",
    "scheme information", "constitution of hdfc mutual fund", "due diligence",
    "definition of terms", "transaction details", "general information",
    "how to apply", "rights of unitholders", "significant accounting policies",
    "risk factors", "special considerations", "portfolio disclosure",
    "computational methodology", "fees and expenses", "indian taxation",
]


def looks_like_heading(line: str) -> bool:
    s = line.strip()
    if not (3 < len(s) <= 140):
        return False
    if s.endswith((".", ",", ";")):
        return False
    if len(s.split()) > 10:
        return False
    low = s.lower()
    for h in _KNOWN_HEADINGS:
        if low == h or low.startswith(h) or (h in low and len(low) <= len(h) + 25):
            return True
    m = _HEADING_RE.match(s)
    if not m:
        return False
    # numbered headings like "2.3 Exit Load" or short ALL CAPS lines
    if m.group(1):
        return True
    letters = [c for c in s if c.isalpha()]
    if letters and sum(1 for c in letters if c.isupper()) / len(letters) > 0.75:
        return True
    # Title-case heading followed by nothing else — only treat as heading when short
    return len(s) <= 60 and s.count(":") == 0


def classify_topic(text: str, section_hint: str = "") -> str:
    """Word-boundary keyword scoring; a heading hit weighs 3x.
    Hyphens are normalized to spaces so 'capital-gains' matches 'capital gains'.
    """
    import re

    hay = f"{section_hint}\n{text[:1500]}".lower().replace("-", " ")
    hint_low = section_hint.lower().replace("-", " ")
    best_topic, best_hits = "general", 0
    for topic, kws in TOPIC_KEYWORDS.items():
        if topic == "general":
            continue
        hits = 0
        heading_hit = False
        for kw in kws:
            pat = re.compile(r"\b" + re.escape(kw.strip()) + r"\b")
            n = len(pat.findall(hay))
            if n:
                hits += n
                if pat.search(hint_low):
                    heading_hit = True
        if not hits:
            continue
        score = hits * (3 if heading_hit else 1)
        if score > best_hits:
            best_topic, best_hits = topic, score
    # the at-a-glance amount tables mention plans/options fields more often
    # than the minimum-investment keywords, so keyword voting mislabels them
    if "minimum application amount" in hay:
        best_topic = "minimum_investment"
    elif "minimum amount" in hay and re.search(r"\bsip\b", hay):
        # "SIP SWP & STP Details: Minimum amount" table rows carry the actual
        # SIP minimums; keyword voting tags them "sip" because SIP tokens
        # outnumber the one "minimum amount" mention
        best_topic = "minimum_investment"
    return best_topic


@dataclass
class Section:
    title: str
    pages: set
    lines: list[str]

    @property
    def text(self) -> str:
        return "\n".join(self.lines)


_SENT_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9])")


def _split_long_text(text: str, target: int, overlap: int) -> list[str]:
    """Sentence-boundary splitting with overlap; keeps table line blocks together."""
    blocks: list[str] = []
    for para in text.split("\n"):
        if "|" in para:  # table row — keep whole line as one block unit
            blocks.append(para)
        else:
            blocks.extend(_SENT_SPLIT_RE.split(para))

    chunks: list[str] = []
    buf = ""
    for b in blocks:
        if not b:
            continue
        if len(buf) + len(b) + 1 <= target:
            buf = f"{buf} {b}".strip()
            continue
        if buf:
            chunks.append(buf)
        if len(b) > target:
            words = b.split(" ")
            sub = ""
            for w in words:
                if len(sub) + len(w) + 1 <= target:
                    sub = f"{sub} {w}".strip()
                else:
                    chunks.append(sub)
                    sub = w[-overlap:] if overlap and overlap < len(w) else w
            buf = sub
        else:
            tail = buf[-overlap:] if overlap else ""
            buf = f"{tail} {b}".strip() if tail else b
    if buf:
        chunks.append(buf)
    return chunks


@dataclass
class Chunk:
    text: str
    page_number: int  # primary page
    page_end: int
    section: str
    topic: str


def build_sections(pages: list[RawPage]) -> list[Section]:
    sections: list[Section] = []
    current = Section(title="Preamble", pages=set(), lines=[])
    for p in pages:
        for line in p.text.split("\n"):
            if not p.is_table and looks_like_heading(line):
                if current.lines and current.text.strip():
                    sections.append(current)
                current = Section(title=line.strip(), pages={p.page}, lines=[])
                continue
            current.pages.add(p.page)
            current.lines.append(line)
    if current.text.strip():
        sections.append(current)
    return sections


def chunk_document(path, target_chars: int = CHUNK_TARGET_CHARS, overlap: int = CHUNK_OVERLAP_CHARS) -> list[Chunk]:
    raw_pages = extract_file(path)
    cleaned = detect_and_strip_headers_footers(raw_pages)

    # Special handling for Riskometer disclosure: one scheme = one chunk
    # so that "Risk-o-meter rating of HDFC Small Cap Fund" retrieves the
    # exact row, not a multi-scheme table chunk diluted by other schemes.
    if "riskometer" in path.name.lower():
        header = "HDFC Mutual Fund Annual Disclosure of Risk-o-meters as at March 31, 2026 (Risk-o-meter levels as per SEBI Master Circular)"
        out: list[Chunk] = []
        for p in cleaned:
            for line in p.text.split("\n"):
                if "HDFC" not in line:
                    continue
                # Heuristic: riskometer rows contain a scheme name + rating
                # e.g. "72 HDFC NIFTY SMALLCAP 250 INDEX FUND Very High Very High 0"
                chunk_text = f"{header}\n{line.strip()}"
                if len(chunk_text) < 30:
                    continue
                out.append(Chunk(text=chunk_text, page_number=p.page, page_end=p.page, section="Risk-o-meter Disclosure", topic="riskometer"))
        if out:
            return out

    sections = build_sections(cleaned)

    chunks: list[Chunk] = []
    for sec in sections:
        body = sec.text.strip()
        if len(body) < 40:
            continue
        pieces = [body] if len(body) <= target_chars else _split_long_text(body, target_chars, overlap)
        for piece in pieces:
            piece = piece.strip()
            if len(piece) < 40:
                continue
            # classify each final chunk individually so long/mixed sections
            # don't get one blanket topic
            topic = classify_topic(piece[:1500], sec.title)
            page_start = min(sec.pages) if sec.pages else 1
            page_end = max(sec.pages) if sec.pages else page_start
            header = sec.title if sec.title != "Preamble" else ""
            full = f"{header}\n{piece}".strip() if header else piece
            chunks.append(
                Chunk(text=full, page_number=page_start, page_end=page_end, section=sec.title, topic=topic)
            )
    return chunks
