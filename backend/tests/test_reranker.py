"""Unit tests for the reranker and citation builder."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.app.rag.reranker import rerank
from backend.app.services.chat_service import build_citation


def _hit(scheme, topic, sim, org="HDFC Mutual Fund", doc_type="SID", date=None):
    return {
        "scheme": scheme,
        "topic": topic,
        "similarity": sim,
        "organization": org,
        "document_type": doc_type,
        "document_date": date,
        "page_number": 42,
        "chunk_text": "x" * 50,
        "metadata": {
            "source_id": "src_abc",
            "source_url": "https://www.hdfcfund.com/explore/mutual-funds/hdfc-small-cap",
            "document_title": "HDFC Small Cap Fund SID",
            "document_date": date or "",
        },
    }


def test_scheme_match_wins():
    hits = [
        _hit("HDFC FlexiCap Fund", "exit_load", 0.80),
        _hit("HDFC Small Cap Fund", "exit_load", 0.75),
    ]
    ranked = rerank(hits, query_scheme="HDFC Small Cap Fund", query_topic="exit_load", intent="FACTUAL_SCHEME")
    assert ranked[0]["scheme"] == "HDFC Small Cap Fund"


def test_topic_match_boost():
    hits = [
        _hit("HDFC Small Cap Fund", "benchmark", 0.78),
        _hit("HDFC Small Cap Fund", "exit_load", 0.74),
    ]
    ranked = rerank(hits, query_scheme="HDFC Small Cap Fund", query_topic="exit_load", intent="FACTUAL_SCHEME")
    assert ranked[0]["topic"] == "exit_load"


def test_groww_intent_prefers_groww_source():
    hits = [
        _hit(None, "sip", 0.70, org="HDFC Mutual Fund", doc_type="SID"),
        _hit(None, "sip", 0.68, org="Groww", doc_type="OTHER"),
    ]
    ranked = rerank(hits, None, "sip", intent="FACTUAL_GROWW")
    assert ranked[0]["organization"] == "Groww"


def test_regulatory_intent_prefers_sebi():
    hits = [
        _hit(None, "riskometer", 0.72, org="HDFC Mutual Fund"),
        _hit(None, "riskometer", 0.70, org="SEBI", doc_type="FAQ_DATASET"),
    ]
    ranked = rerank(hits, None, "riskometer", intent="FACTUAL_REGULATORY")
    assert ranked[0]["organization"] == "SEBI"


def test_freshness_breaks_ties():
    old = _hit("HDFC Small Cap Fund", "exit_load", 0.75, date="2021-01-01")
    new = _hit("HDFC Small Cap Fund", "exit_load", 0.75, date="2026-07-15")
    ranked = rerank([old, new], "HDFC Small Cap Fund", "exit_load", "FACTUAL_SCHEME")
    assert ranked[0]["document_date"] == "2026-07-15"


def test_citation_from_metadata_only():
    hit = _hit("HDFC Small Cap Fund", "exit_load", 0.8, date="2025-11-21")
    source, last_updated = build_citation(hit)
    assert source.url == "https://www.hdfcfund.com/explore/mutual-funds/hdfc-small-cap"
    assert source.page == 42
    assert source.source_id == "src_abc"
    assert last_updated == "Last updated from sources: November 2025"
