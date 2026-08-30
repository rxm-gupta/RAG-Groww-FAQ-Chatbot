"""Unit tests for the ingestion chunker (no network, no DB)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ingestion.chunk import classify_topic, chunk_document, looks_like_heading

DOCS = Path(__file__).resolve().parents[3] / "data" / "documents"


def test_heading_detection():
    assert looks_like_heading("EXIT LOAD")
    assert looks_like_heading("Investment Objective")
    assert looks_like_heading("2.3 Total Expense Ratio")
    assert not looks_like_heading("The fund invests predominantly in small cap companies.")


def test_topic_classification():
    text = "Exit Load: 1% - If redeemed on or before one year from the date of allotment."
    assert classify_topic(text, "EXIT LOAD") == "exit_load"
    text2 = "The Total Expense Ratio of the Direct Plan is lower than the Regular Plan."
    assert classify_topic(text2, "TER") == "expense_ratio"


def test_chunk_sid_document():
    sid = DOCS / "SID - HDFC Small Cap Fund dated November 21 2025_0.pdf"
    if not sid.exists():
        print("SID file missing; skipping")
        return
    chunks = chunk_document(sid)
    assert len(chunks) > 20
    topics = {c.topic for c in chunks}
    assert "exit_load" in topics or "charges_fees" in topics
    for c in chunks[:5]:
        assert c.page_number >= 1
        assert len(c.text) > 30
        assert c.section


def test_chunks_are_reasonable_size():
    kim = next(iter(DOCS.glob("KIM - HDFC Flexi Cap*.pdf")), None)
    if not kim:
        print("KIM missing; skipping")
        return
    chunks = chunk_document(kim)
    sizes = [len(c.text) for c in chunks]
    assert max(sizes) < 4000  # target ~1200 + header tolerance
