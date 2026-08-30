"""PII / account-information detection. Runs BEFORE retrieval, embedding, or any
external call. Raw matched values are never logged."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

# --- regex patterns (compiled once) ---------------------------------------
PATTERNS: dict[str, re.Pattern] = {
    "pan": re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b"),
    # Aadhaar: 12 digits (with optional separators), or explicit keyword + number
    "aadhaar": re.compile(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}\b"),
    "otp": re.compile(r"\b(otp|one[\s-]?time\s*password|verification\s*code)\b", re.IGNORECASE),
    "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    # Indian mobile numbers: 10 digits (3-3-4) starting 6-9, allow +91/0 prefixes and separators
    "phone": re.compile(r"(?:\+?91[\s-]?)?\b[6-9]\d{2}[\s-]?\d{3}[\s-]?\d{4}\b|\b0[6-9]\d{2}[\s-]?\d{3}[\s-]?\d{4}\b"),
    "bank_account": re.compile(
        r"\b(?:account|acct|a\/c|bank)\b[\w\s]{0,15}?(?:is|:|-|#)?[\s.:-]{0,4}(\d{9,18})\b", re.IGNORECASE
    ),
    # folio ID must contain a digit so phrases like "What is a Folio number?"
    # don't match, while "Folio is 12345678" still does.
    "folio": re.compile(
        r"\b(?:folio|follio)\b(?:[\s:.:-]{0,3}(?:no|number|num|#|is)\b)*[\s:.:-]{0,3}"
        r"(?=[A-Za-z0-9/\-]*\d)([A-Za-z0-9][A-Za-z0-9/\-]{5,20})\b",
        re.IGNORECASE,
    ),
    "card": re.compile(r"\b(?:\d{4}[\s-]?){3}\d{1,7}\b"),
    # credential values: keyword followed by whitespace/colon/equals and a
    # value. A hyphen is deliberately NOT a separator so phrasings like
    # "password-protected" (a factual question about statement security) are
    # not flagged, while "password: hunter2" / "password hunter2" still are.
    "credential": re.compile(r"\b(password|passcode|username|login id|user id|pin)\b[\s:=]+\S+", re.IGNORECASE),
}

# keywords that indicate an account-level request even without a detectable identifier
ACCOUNT_REQUEST_KEYWORDS = [
    "my balance", "my holdings", "my portfolio", "my account", "my statement",
    "show my", "check my", "my folio", "my pan", "my investment status",
    "order status for my", "units held by me", "my nav",
    "account number", "fund balance", "show me my", "tell me my",
]

# possessive + sensitive-noun within the same sentence
_ACCOUNT_NOUN_RE = re.compile(
    r"\b(my|mine|me)\b[^.?!]{0,40}\b(balance|holdings|portfolio|statement|folio|account|investments|units)\b",
    re.IGNORECASE,
)


@dataclass
class PiiResult:
    detected: bool = False
    categories: list[str] = field(default_factory=list)

    HARD_CATEGORIES = {"pan", "aadhaar", "otp", "email", "phone", "bank_account", "folio", "card", "credential"}

    @property
    def safe_summary(self) -> str:
        """Log-safe summary — never includes the raw matched text."""
        return ",".join(self.categories) if self.categories else "none"

    @property
    def hard_identifier(self) -> bool:
        """True when an actual identifier/credential was found (vs a soft
        account-level request phrase)."""
        return bool(set(self.categories) & self.HARD_CATEGORIES)


def _keyword_hit(question: str) -> bool:
    low = question.lower()
    if any(kw in low for kw in ACCOUNT_REQUEST_KEYWORDS):
        return True
    return bool(_ACCOUNT_NOUN_RE.search(question))


def scan_pii(question: str) -> PiiResult:
    """Detect PAN/Aadhaar/bank/folio/OTP/phone/email/credentials/account requests.

    Returns categories only; callers must never log raw matches.
    """
    result = PiiResult()

    if PATTERNS["pan"].search(question):
        result.categories.append("pan")

    if re.search(r"\baadhaar|aadhar\b", question, re.IGNORECASE):
        result.categories.append("aadhaar")
    else:
        m = PATTERNS["aadhaar"].search(re.sub(r"[A-Za-z]", "", question))
        if m and not PATTERNS["card"].search(question):
            result.categories.append("aadhaar")

    if PATTERNS["otp"].search(question):
        result.categories.append("otp")

    if PATTERNS["email"].search(question):
        result.categories.append("email")

    if PATTERNS["phone"].search(question):
        result.categories.append("phone")

    if PATTERNS["bank_account"].search(question):
        result.categories.append("bank_account")

    if PATTERNS["folio"].search(question):
        result.categories.append("folio")

    if PATTERNS["credential"].search(question):
        result.categories.append("credential")

    if _keyword_hit(question):
        result.categories.append("account_request")

    result.detected = bool(result.categories)
    return result


def scrub_pii(text: str) -> str:
    """Best-effort removal of PII from free text before storing (e.g., feedback snippets)."""
    scrubbed = text
    for name in ("pan", "email", "card"):
        scrubbed = PATTERNS[name].sub("[redacted]", scrubbed)
    scrubbed = re.sub(r"\b\d{12}\b", "[redacted]", scrubbed)
    scrubbed = PATTERNS["phone"].sub("[redacted]", scrubbed)
    return scrubbed[:200]
