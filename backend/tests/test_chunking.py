"""Unit tests for the ingestion chunker (no network, no DB)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ingestion.chunk import classify_topic, chunk_document, looks_like_heading
from ingestion.extract import _text_outside_tables, extract_pdf

DOCS = Path(__file__).resolve().parents[3] / "data" / "documents"


class _FakePage:
    """Minimal pdfplumber-page stand-in for _text_outside_tables tests."""

    def __init__(self, words, cell_boxes):
        self._words = words
        self.cells = cell_boxes

    def extract_words(self):
        return self._words

    def extract_text(self):
        return " ".join(w["text"] for w in self._words)


def test_text_outside_tables_excludes_cell_words():
    page = _FakePage(
        words=[
            {"text": "Header", "x0": 10, "x1": 50, "top": 10, "bottom": 20},
            {"text": "Minimum", "x0": 10, "x1": 60, "top": 100, "bottom": 110},
            {"text": "amount", "x0": 65, "x1": 115, "top": 100, "bottom": 110},
            {"text": "Rs.", "x0": 400, "x1": 420, "top": 100, "bottom": 110},
            {"text": "300", "x0": 425, "x1": 450, "top": 100, "bottom": 110},
        ],
        cell_boxes=[(5, 95, 500, 115)],
    )
    out = _text_outside_tables(page, [type("T", (), {"cells": page.cells})()])
    assert out == "Header"


def test_text_outside_tables_no_tables_returns_full_text():
    page = _FakePage(
        words=[
            {"text": "Plain", "x0": 10, "x1": 40, "top": 10, "bottom": 20},
            {"text": "text", "x0": 45, "x1": 70, "top": 10, "bottom": 20},
        ],
        cell_boxes=[],
    )
    assert _text_outside_tables(page, []) == "Plain text"


def test_scheme_summary_pdf_has_clean_minimum_rows():
    """Regression: the scheme-summary table must not produce garbled text
    like 'Minimum 49 - Rs. 300' where the row label/value pairing is lost."""
    summary = next(iter(DOCS.glob("HDFCEQ_*.pdf")), None)
    if not summary:
        print("scheme summary PDF missing; skipping")
        return
    pages = extract_pdf(summary)
    page1 = pages[0].text
    assert "Minimum 49 - Rs. 300" not in page1
    assert "SIP SWP & STP Details: Minimum amount" in page1
    assert "Minimum Application Amount | Rs.100" in page1


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


def test_topic_classification_sip_minimum_amount_row():
    # scheme-summary "SIP SWP & STP Details: Minimum amount" rows carry the
    # actual SIP minimums; SIP tokens must not steal the topic from
    # minimum_investment
    text = (
        "SIP SWP & STP Details: Minimum amount of HDFC Flexi Cap Fund: "
        "For SIP DSIP, WSIP, MSIP - Rs. 100; QSIP - Rs. 1500; HSIP - Rs. 2500; "
        "YSIP - Rs. 5000. For SWAP Fixed SWAP - Rs. 100; Variable SWAP - Rs. 300."
    )
    assert classify_topic(text, "SIP SWP & STP Details: Minimum amount") == "minimum_investment"


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
