"""Unit tests for intent classification and scheme extraction."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.app.safety.intent import classify_intent, extract_scheme, extract_topic


def cls(q):
    return classify_intent(q, pii_detected=False)


def test_factual_scheme_expense_ratio():
    r = cls("What is the expense ratio of HDFC FlexiCap Fund?")
    assert r.intent == "FACTUAL_SCHEME"
    assert r.scheme == "HDFC FlexiCap Fund"
    assert r.topic == "expense_ratio"


def test_factual_scheme_exit_load():
    r = cls("What is the exit load of HDFC Small Cap Fund?")
    assert r.intent == "FACTUAL_SCHEME"
    assert r.scheme == "HDFC Small Cap Fund"
    assert r.topic == "exit_load"


def test_benchmark_large_mid():
    r = cls("What is the benchmark of HDFC Large and Mid Cap Fund?")
    assert r.scheme == "HDFC Large and Mid Cap Fund"
    assert r.topic == "benchmark"


def test_tracking_error_index():
    r = cls("What is the tracking error of HDFC Index Fund - Nifty 50 Plan?")
    assert r.scheme == "HDFC Index Fund - Nifty 50 Plan"
    assert r.topic == "tracking_error"


def test_elss_lockin():
    r = cls("Can I redeem HDFC ELSS Tax Saver Fund before 3 years?")
    assert r.scheme == "HDFC ELSS Tax Saver Fund"


def test_groww_cancel_sip():
    r = cls("How do I cancel my SIP on Groww?")
    assert r.intent == "FACTUAL_GROWW"


def test_regulatory_cas():
    r = cls("What is CAS?")
    assert r.intent in ("FACTUAL_REGULATORY", "FACTUAL_OPERATIONAL")


def test_advice_which_best():
    r = cls("Which fund is best for a 5-year goal?")
    assert r.intent == "ADVICE"


def test_advice_should_i_buy():
    r = cls("Should I invest in HDFC Small Cap Fund?")
    assert r.intent == "ADVICE"


def test_prediction():
    r = cls("Will HDFC FlexiCap return 15% next year?")
    assert r.intent == "PERFORMANCE_PREDICTION"


def test_comparison():
    r = cls("Which fund performed best?")
    assert r.intent == "PERFORMANCE_COMPARISON"


def test_market_timing():
    r = cls("Should I stop my SIP because the market is down?")
    assert r.intent == "MARKET_TIMING"


def test_pii_priority_over_everything():
    r = classify_intent("What is the exit load? My PAN is ABCDE1234F", pii_detected=True)
    assert r.intent == "PII_ACCOUNT"


def test_soft_account_request_does_not_override_advice():
    from backend.app.safety.pii import PiiResult

    pii = PiiResult()
    pii.categories = ["account_request"]
    pii.detected = True
    r = classify_intent("Should I sell my HDFC FlexiCap Fund units?", pii_detected=pii)
    assert r.intent == "ADVICE"


def test_soft_account_request_yields_pii_when_no_other_intent():
    from backend.app.safety.pii import PiiResult

    pii = PiiResult()
    pii.categories = ["account_request"]
    pii.detected = True
    r = classify_intent("Can you tell me my current holdings?", pii_detected=pii)
    assert r.intent == "PII_ACCOUNT"


def test_historical_performance_allowed():
    r = cls("What historical performance is reported in the latest factsheet for HDFC FlexiCap Fund?")
    assert r.intent == "HISTORICAL_PERFORMANCE"


def test_out_of_scope():
    r = cls("What is the price of bitcoin today?")
    assert r.intent == "OUT_OF_SCOPE"


def test_ambiguous_scheme_missing():
    r = cls("What is the expense ratio?")
    assert r.intent == "AMBIGUOUS"
    assert r.scheme is None


def test_scheme_aliases():
    assert extract_scheme("Tell me about the smallcap fund") == "HDFC Small Cap Fund"
    assert extract_scheme("flexi cap fund details") == "HDFC FlexiCap Fund"


def test_topic_extraction():
    assert extract_topic("exit load charges") == "exit_load"
    assert extract_topic("fund manager name") == "fund_manager"


def test_topic_extraction_riskometer_not_stolen_by_ter_substring():
    # "riskometer" contains "ter"; word-boundary matching must keep the
    # riskometer topic from being reclassified as expense_ratio
    assert extract_topic("What is the riskometer for Flexi Cap Fund?") == "riskometer"
    assert extract_topic("What is the risk meter for Small Cap Fund?") == "riskometer"
    assert extract_topic("risk-o-meter level of the scheme") == "riskometer"
    # genuine expense-ratio phrasing must still classify correctly
    assert extract_topic("What is the TER of HDFC FlexiCap Fund?") == "expense_ratio"
    assert extract_topic("What is the expense ratio of the fund?") == "expense_ratio"
