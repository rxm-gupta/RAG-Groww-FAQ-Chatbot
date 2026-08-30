"""Central message constants — the only place refusal/error wording lives."""
NOT_FOUND_MSG = "I couldn't find this information in the official sources available to me."
AMBIGUOUS_NOT_FOUND_MSG = "I couldn't find this in the official sources available to me."

DB_ERROR_MSG = "Sorry, I couldn't retrieve the official source information right now."
GEN_ERROR_MSG = "Sorry, I couldn't generate the answer right now."

PII_MSG = (
    "I can't access or retrieve personal account information such as balances, holdings, "
    "PAN-linked information, folio details, or OTP-protected data. I can only provide general "
    "factual information from the official sources in this FAQ assistant."
)

ADVICE_MSG = (
    "I can provide factual information about the HDFC Mutual Fund schemes in this knowledge base, "
    "but I can't recommend which fund to buy, sell, or choose for a personal goal."
)

PREDICTION_MSG = (
    "I can't predict future returns, NAV, or performance. Historical figures are reported only "
    "when they appear in an official retrieved source, without extrapolation. You can ask what "
    "historical performance an official factsheet reports for a specific scheme."
)

COMPARISON_MSG = (
    "I can't compare schemes' performance or rank them as best or worst. I can report the "
    "historical performance stated in an individual scheme's official documents if you ask about "
    "a specific fund."
)

MARKET_TIMING_MSG = (
    "I can't advise on market timing or whether now is a good time to invest, start, or stop a SIP. "
    "I can explain how SIPs, redemption, and NAV applicability work using official sources."
)

OUT_OF_SCOPE_MSG = (
    "That question is outside this assistant's scope. I can answer factual questions about the five "
    "HDFC Mutual Fund schemes, mutual-fund operations, regulatory topics, and Groww's public "
    "mutual-fund processes."
)

AMBIGUOUS_SCHEME_MSG = "Which HDFC Mutual Fund scheme would you like to know about?"

SUPPORTED_SCHEMES = [
    "HDFC FlexiCap Fund",
    "HDFC Small Cap Fund",
    "HDFC Large and Mid Cap Fund",
    "HDFC Index Fund - Nifty 50 Plan",
    "HDFC ELSS Tax Saver Fund",
]

DISCLAIMER = (
    "Facts-only assistant. This chatbot provides factual information from official public sources "
    "and does not provide investment, financial, portfolio, or tax advice. Do not enter PAN, "
    "Aadhaar, OTPs, bank details, folio numbers, or other personal/account information."
)
