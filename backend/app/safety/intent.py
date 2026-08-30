"""Rule-based intent classification, scheme extraction, and topic extraction.

Deterministic (no LLM) so guardrails can never be talked out of by the generator.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# --------------------------------------------------------------------------
# Schemes
# --------------------------------------------------------------------------
SCHEME_ALIASES: dict[str, list[str]] = {
    "HDFC FlexiCap Fund": ["flexicap", "flexi cap", "flexi-cap"],
    "HDFC Small Cap Fund": ["small cap fund", "smallcap", "small-cap"],
    "HDFC Large and Mid Cap Fund": ["large and mid cap", "large & mid cap", "large-mid cap", "large midcap"],
    "HDFC Index Fund - Nifty 50 Plan": ["index fund nifty 50", "nifty 50 plan", "nifty50 index fund", "nifty 50 index fund"],
    "HDFC ELSS Tax Saver Fund": ["elss tax saver", "tax saver fund", "elss fund", "hdfc elss"],
}

# scheme-specific topics require a scheme to answer
SCHEME_SPECIFIC_TOPICS = [
    "expense_ratio", "exit_load", "benchmark", "minimum_investment", "fund_manager",
    "tracking_error", "asset_allocation", "investment_objective", "investment_strategy",
    "lock_in", "plans_options", "replication", "riskometer",
]

TOPIC_KEYWORDS: dict[str, list[str]] = {
    "expense_ratio": ["expense ratio", "ter", "total expense", "management fee", "recurring expense", "charges for managing", "direct vs regular ter"],
    "exit_load": ["exit load", "exit charge", "redemption charge", "cdsc"],
    "benchmark": ["benchmark", "index tracked", "tier i benchmark"],
    "minimum_investment": ["minimum sip", "minimum lump", "minimum investment", "minimum application", "minimum purchase", "minimum amount"],
    "fund_manager": ["fund manager", "who manages", "managed by", "fund management"],
    "tracking_error": ["tracking error", "tracking difference"],
    "asset_allocation": ["asset allocation", "allocation pattern", "equity exposure", "how much in equity", "small cap allocation"],
    "investment_objective": ["investment objective", "objective of", "aim of the fund", "what is the fund for"],
    "investment_strategy": ["investment strategy", "investment approach", "how does the fund invest", "where does it invest"],
    "lock_in": ["lock-in", "lock in period", "locked in", "withdraw before 3 years", "redeem before 3 years", "3-year lock"],
    "plans_options": ["direct plan", "regular plan", "growth option", "idcw", "dividend option", "payout option", "plans and options"],
    "replication": ["replication", "sampling method", "full replication"],
    "riskometer": ["riskometer", "risk-o-meter", "risk o meter", "risk meter", "risk level of", "very high risk"],
    "sip": ["sip", "systematic investment plan", "start a sip", "stop a sip", "cancel sip", "pause sip", "modify sip", "sip date"],
    "redemption": ["redeem", "redemption", "withdraw money", "withdrawal", "sell units", "swp"],
    "purchase": ["lump sum", "purchase", "buy units", "subscribe", "invest amount"],
    "switch": ["switch", "switching"],
    "cutoff_time": ["cut-off", "cutoff", "nav applicability", "applicable nav", "what time"],
    "folio_statement": ["account statement", "cas", "consolidated account statement", "statement of account", "capital gains statement", "tax certificate", "folio number forgotten", "forgot my folio"],
    "tax_capital_gains": ["capital gains tax", "ltcg", "stcg", "tax on mutual funds", "taxation"],
    "tax_80c": ["80c", "tax saving", "tax benefit", "section 80c"],
    "stamp_duty": ["stamp duty", "stt", "transaction charge"],
    "elss": ["elss", "equity linked savings"],
    "categorization": ["sebi categorization", "scheme category", "open ended", "closed ended", "multi cap", "flexi cap fund category"],
    "scores": ["scores", "grievance", "complaint against amc", "ogms"],
    "charges_fees": ["charges", "fees", "costs", "levies", "commission", "platform fee"],
    "orders": ["order status", "order history", "transaction history", "where can i see my orders"],
    "payment": ["payment methods", "upi", "netbanking", "net banking", "payment options"],
    "performance_reported": ["historical performance reported", "returns reported", "performance reported in", "factsheet show", "as per factsheet", "as per sid"],
    "aum": ["aum", "assets under management"],
    "nav_value": ["current nav", "latest nav", "today's nav"],
}

GROWW_HINTS = [
    "groww", "on groww app", "through groww", "via groww",
]

REGULATORY_HINTS = [
    "sebi", "amfi", "regulation", "categorization", "riskometer definition", "what is cas",
    "stamp duty", "80c", "elss lock-in", "scores", "direct vs regular", "growth vs idcw",
    "what is idcw", "idcw meaning", "capital gains tax", "ltcg", "stcg", "tax rate",
]

OPERATIONAL_HINTS = [
    "how do i", "how can i", "process to", "steps to", "download", "statement",
    "cut-off", "when will nav apply", "settlement", "documents required",
    # general-process phrasings that must not be mistaken for account-specific
    # PII requests or advice
    "will i receive", "track my", "how long before", "how many days before",
]


@dataclass
class IntentResult:
    intent: str
    scheme: str | None = None
    topic: str | None = None


def extract_scheme(question: str) -> str | None:
    low = question.lower()
    for canonical, aliases in SCHEME_ALIASES.items():
        if any(a in low for a in aliases):
            return canonical
    return None


# Precompiled word-boundary patterns per topic. Substring counting is not
# safe here: short keywords like "ter" (expense_ratio) would match inside
# unrelated words ("riskometer", "risk meter") and, via the strict-> tie-break
# and dict order, steal the topic from the correct match.
_TOPIC_PATTERNS: dict[str, list[re.Pattern[str]]] = {
    topic: [re.compile(r"\b" + re.escape(kw.replace("-", " ")) + r"\b") for kw in kws]
    for topic, kws in TOPIC_KEYWORDS.items()
}


def extract_topic(question: str) -> str | None:
    """Return the most salient canonical topic for routing/retrieval.
    Hyphens are normalized to spaces so 'capital-gains' matches 'capital gains'.
    Keywords match on word boundaries only.
    """
    low = f" {question.lower().replace('-', ' ')} "
    # 'minimum lump-sum purchase amount' scores higher on the generic
    # 'purchase' keywords than on the specific minimum-investment ones,
    # so route minimum-amount questions explicitly first
    if "minimum" in low and any(p in low for p in (" lump sum ", "purchase amount", "application amount", "investment amount")):
        return "minimum_investment"
    best, best_hits = None, 0
    for topic, patterns in _TOPIC_PATTERNS.items():
        hits = sum(len(p.findall(low)) for p in patterns)
        if hits > best_hits:
            best, best_hits = topic, hits
    return best


def _has_any(text: str, needles: list[str]) -> bool:
    return any(n in text for n in needles)


# --------------------------------------------------------------------------
# Intent classification
# --------------------------------------------------------------------------
_ADVICE_RE = re.compile(
    r"\b(should i|which fund|which one|best fund|best scheme|safest|recommend|suggest me|"
    r"for my (goal|retirement|child|future)|good investment for me|choose for|invest in\?|"
    r"better than|top fund|ideal fund|suitable for me|"
    r"which\s+hdfc\s+mutual\s+fund|mutual fund is best|is best for me|"
    r"best (platform|broker|app)|better (platform|broker|app)|which platform)\b", re.IGNORECASE)

_PREDICTION_RE = re.compile(
    r"\b(will .{0,40}(return|give|deliver|yield)|next year|future return|expected return|"
    r"predict|forecast|how much (will|can) i (make|earn)|15%|20%|doubles? by)\b", re.IGNORECASE)

_COMPARISON_RE = re.compile(
    r"\b(which|what).{0,60}\b(performed best|perform(ed)? better|highest return|best past|"
    r"compare.{0,30}(returns?|funds?|schemes?)|ranking|rank the|versus each other|vs each other)\b"
    r"|\b(calculate|compute).{0,40}(compare|comparison|which.{0,30}better)"
    r"|\bcompare\b.{0,60}\b(returns?|funds?|schemes?)\b"
    r"|highest returns?\b", re.IGNORECASE)

_MARKET_TIMING_RE = re.compile(
    r"\b(market is down|market is up|market falls|market crash|good time to invest|right time to|"
    r"time the market|because the market|is now a good time|should i stop|should i start.*(now|today))\b",
    re.IGNORECASE)

_HIST_PERF_RE = re.compile(
    r"\b(historical performance|returns? (reported|shown|published)|what (returns|performance).{0,40}"
    r"(report|show|publish|state)|(factsheet|fact sheet|sid|kim).{0,40}(return|performance|cagr))\b",
    re.IGNORECASE)

_OUT_OF_SCOPE_RE = re.compile(
    r"\b(stocks?|shares?|trading|crypto|bitcoin|insurance|term plan|fd rates?|fixed deposit|"
    r"loan|credit card|demat charges|ipo|commodity|gold price|weather|cricket|movie)\b", re.IGNORECASE)

# operational timing phrasing ("how long before my SIP date should I cancel…")
# is a process question, not advice — suppress the broad "should i" ADVICE rule
_OPERATIONAL_TIMING_RE = re.compile(
    r"how (?:long|many days)\s+(?:before|prior|in advance)", re.IGNORECASE)


def classify_intent(question: str, pii_detected: bool | object = False) -> IntentResult:
    """Priority-ordered rule classification.

    pii_detected may be a bool (legacy/tests) or a PiiResult. Hard identifiers
    force PII_ACCOUNT; soft account-request phrases only override factual
    intents — explicit advice/refusal intents still take precedence so users
    get the more accurate refusal message.
    """
    q = question.strip()
    low = q.lower()

    from .pii import PiiResult

    if isinstance(pii_detected, PiiResult):
        hard_pii = pii_detected.hard_identifier
        soft_account = "account_request" in pii_detected.categories
    else:
        hard_pii = bool(pii_detected)
        soft_account = False

    scheme = extract_scheme(q)
    topic = extract_topic(q)

    if hard_pii:
        return IntentResult(intent="PII_ACCOUNT", scheme=scheme, topic=topic)

    if _MARKET_TIMING_RE.search(q):
        return IntentResult(intent="MARKET_TIMING", scheme=scheme, topic=topic)

    if _COMPARISON_RE.search(q):
        return IntentResult(intent="PERFORMANCE_COMPARISON", scheme=scheme, topic=topic)

    if _PREDICTION_RE.search(q):
        return IntentResult(intent="PERFORMANCE_PREDICTION", scheme=scheme, topic=topic)

    if _ADVICE_RE.search(q) and not _OPERATIONAL_TIMING_RE.search(q):
        return IntentResult(intent="ADVICE", scheme=scheme, topic=topic)

    if _OUT_OF_SCOPE_RE.search(q) and not scheme and not _has_any(low, OPERATIONAL_HINTS):
        return IntentResult(intent="OUT_OF_SCOPE", scheme=scheme, topic=topic)

    if _HIST_PERF_RE.search(q):
        return IntentResult(intent="HISTORICAL_PERFORMANCE", scheme=scheme,
                            topic=topic or "performance_reported")

    # Groww operational questions — but an account-level request phrasing
    # (e.g. "my Groww folio") must route to PII_ACCOUNT, not FACTUAL_GROWW
    if _has_any(low, GROWW_HINTS) and not soft_account:
        return IntentResult(intent="FACTUAL_GROWW", scheme=scheme, topic=topic or "groww_operations")

    # Regulatory/educational
    if _has_any(low, REGULATORY_HINTS) and not scheme:
        return IntentResult(intent="FACTUAL_REGULATORY", scheme=scheme, topic=topic)

    # Operational — must be checked BEFORE soft account-request override,
    # otherwise "How can I download my capital-gains statement?" (which
    # contains "my ... statement") would be misrouted to PII_ACCOUNT.
    if _has_any(low, OPERATIONAL_HINTS):
        return IntentResult(intent="FACTUAL_OPERATIONAL", scheme=scheme, topic=topic)

    if soft_account:
        # account-level request phrasing beats remaining factual routing
        return IntentResult(intent="PII_ACCOUNT", scheme=scheme, topic=topic)

    if scheme:
        return IntentResult(intent="FACTUAL_SCHEME", scheme=scheme, topic=topic)

    # factual-looking but scheme-specific topic without a scheme -> ambiguous
    if topic in SCHEME_SPECIFIC_TOPICS:
        return IntentResult(intent="AMBIGUOUS", scheme=None, topic=topic)

    if topic:
        return IntentResult(intent="FACTUAL_REGULATORY", scheme=None, topic=topic)

    return IntentResult(intent="AMBIGUOUS", scheme=None, topic=None)
