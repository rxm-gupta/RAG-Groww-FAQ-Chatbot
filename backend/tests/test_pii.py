"""Unit tests for the safety layer — no network required."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.app.safety.pii import scan_pii, scrub_pii


def test_pan_detected():
    r = scan_pii("My PAN is ABCDE1234F. Show my balance.")
    assert r.detected and "pan" in r.categories and "account_request" in r.categories


def test_aadhaar_detected():
    r = scan_pii("My Aadhaar is 1234 5678 9012")
    assert "aadhaar" in r.categories


def test_otp_detected():
    r = scan_pii("I received an OTP 553321. Can you check my account?")
    assert "otp" in r.categories


def test_folio_detected():
    r = scan_pii("Here is my folio number 12345678/34. Tell me my holdings.")
    assert "folio" in r.categories or "account_request" in r.categories


def test_folio_phrase_without_id_not_flagged():
    r = scan_pii("What is a Folio number?")
    assert "folio" not in r.categories
    assert not r.detected


def test_folio_with_is_connector_detected():
    r = scan_pii("My folio is 12345678")
    assert "folio" in r.categories


def test_folio_with_no_is_connector_detected():
    r = scan_pii("My folio no is 12345678")
    assert "folio" in r.categories


def test_folio_alphanumeric_id_detected():
    r = scan_pii("Folio 12AB3456 balance please")
    assert "folio" in r.categories


def test_email_detected():
    r = scan_pii("Email me at john.doe@example.com about my account")
    assert "email" in r.categories


def test_phone_detected():
    r = scan_pii("Call me at 9876543210 regarding my folio")
    assert "phone" in r.categories


def test_bank_account_detected():
    r = scan_pii("My bank account number is 12345678901, check my balance")
    assert "bank_account" in r.categories


def test_credentials_detected():
    r = scan_pii("password: hunter2 — log in for me")
    assert "credential" in r.categories


def test_clean_question_not_flagged():
    r = scan_pii("What is the exit load of HDFC Small Cap Fund?")
    assert not r.detected


def test_clean_question_with_numbers_not_flagged():
    r = scan_pii("What was the NAV of HDFC FlexiCap Fund in July 2026?")
    assert not r.detected


def test_scrub_removes_pan_and_email():
    out = scrub_pii("PAN ABCDE1234F email a@b.com ok")
    assert "ABCDE1234F" not in out and "a@b.com" not in out


def test_safe_summary_has_no_raw_values():
    r = scan_pii("PAN ABCDE1234F")
    assert "ABCDE" not in r.safe_summary
