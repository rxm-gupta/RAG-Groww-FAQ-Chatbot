"""Unit tests for chat-service refusal ordering and the AMBIGUOUS try-answer flow."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import backend.app.services.chat_service as chat_service
from backend.app.rag.generator import looks_like_no_evidence
from backend.app.safety.messages import (
    ADVICE_MSG,
    AMBIGUOUS_NOT_FOUND_MSG,
    NOT_FOUND_MSG,
    PII_MSG,
)
from backend.app.services.chat_service import build_scheme_suggestions, handle_chat


def _hit(scheme=None, topic=None, sim=0.8):
    return {
        "scheme": scheme,
        "topic": topic,
        "similarity": sim,
        "organization": "HDFC Mutual Fund",
        "document_type": "SID",
        "document_date": "2026-01-01",
        "page_number": 42,
        "chunk_text": "x" * 50,
        "metadata": {
            "source_id": "src_abc",
            "source_url": "https://www.hdfcfund.com/explore/mutual-funds/hdfc-small-cap",
            "document_title": "HDFC Small Cap Fund SID",
            "document_date": "2026-01-01",
        },
    }


def _patch_pipeline(monkeypatch, ranked, answer):
    monkeypatch.setattr(chat_service, "retrieve", lambda *a, **k: ranked)
    monkeypatch.setattr(chat_service, "rerank", lambda hits, *a, **k: hits)
    monkeypatch.setattr(
        chat_service, "generate_answer_with_fallback", lambda evidence, q: (answer, "test-model")
    )
    import backend.app.rag.retriever as retriever

    monkeypatch.setattr(retriever, "get_client", lambda: object())


def test_soft_account_request_after_advice():
    resp = handle_chat("Should I sell my HDFC FlexiCap Fund units?", None)
    assert resp.refused and resp.refusal_type == "ADVICE" and resp.answer == ADVICE_MSG


def test_hard_pii_still_first():
    resp = handle_chat("My PAN is ABCDE1234F. Show my balance.", None)
    assert resp.refused and resp.refusal_type == "PII_ACCOUNT" and resp.answer == PII_MSG


def test_soft_account_request_alone_refused():
    resp = handle_chat("Can you tell me my current holdings?", None)
    assert resp.refused and resp.refusal_type == "PII_ACCOUNT" and resp.answer == PII_MSG


def test_folio_number_question_not_refused(monkeypatch):
    _patch_pipeline(monkeypatch, [_hit()], "A folio number identifies an investor.")
    resp = handle_chat("What is a Folio number?", None)
    assert not resp.refused
    assert "folio number identifies" in resp.answer


def test_operational_with_my_statement_not_pii_refused(monkeypatch):
    _patch_pipeline(monkeypatch, [], "unused")
    resp = handle_chat("How can I download my capital-gains statement?", None)
    assert not resp.refused
    assert resp.refusal_type == "NO_EVIDENCE"
    assert resp.answer == NOT_FOUND_MSG


def test_ambiguous_answer_gets_suggestions(monkeypatch):
    _patch_pipeline(monkeypatch, [_hit(sim=0.7)], "Exit load applies if you redeem early.")
    resp = handle_chat("What is the exit load?", None)
    assert not resp.refused
    assert resp.source is not None
    assert "Exit load applies" in resp.answer
    assert "Do you want to know about the exit load of HDFC FlexiCap Fund?" in resp.answer


def test_ambiguous_no_evidence_gets_suggestions_no_citation(monkeypatch):
    _patch_pipeline(
        monkeypatch, [_hit(sim=0.7)], "The information could not be found in the sources."
    )
    resp = handle_chat("What is the exit load?", None)
    assert not resp.refused
    assert resp.source is None
    assert resp.refusal_type == "NO_EVIDENCE"
    assert resp.answer.startswith(AMBIGUOUS_NOT_FOUND_MSG)
    assert "You could also ask about a specific scheme:" in resp.answer


def test_ambiguous_threshold_gate_gives_suggestions(monkeypatch):
    _patch_pipeline(monkeypatch, [_hit(sim=0.1)], "unused")
    resp = handle_chat("What is the exit load?", None)
    assert not resp.refused
    assert resp.source is None
    assert resp.refusal_type == "NO_EVIDENCE"
    assert resp.answer.startswith(AMBIGUOUS_NOT_FOUND_MSG)


def test_suggestions_builder_three_lines():
    text = build_scheme_suggestions("exit_load")
    lines = [l for l in text.splitlines() if l.startswith("- ")]
    assert len(lines) == 3
    assert all("HDFC" in l for l in lines)


def test_suggestions_builder_generic_fallback():
    text = build_scheme_suggestions(None)
    assert "Tell me about HDFC FlexiCap Fund" in text


def test_no_evidence_patterns():
    assert looks_like_no_evidence("It couldn\u2019t be found in the documents.")
    assert looks_like_no_evidence("The information could not be found.")
    assert looks_like_no_evidence("The value could not be determined.")
    assert looks_like_no_evidence("This data isn\u2019t available in the SID.")
    assert looks_like_no_evidence("The information you\u2019re looking for is not present.")
    assert looks_like_no_evidence("The TER is not specified in the document.")
    assert looks_like_no_evidence("Exit load is not disclosed in this factsheet.")
    assert not looks_like_no_evidence("The exit load is 1% if redeemed within one year.")
    assert not looks_like_no_evidence("The minimum lump-sum investment is Rs 5,000.")
