import pytest
from sqlalchemy import text

from src.security.pii_redactor import (
    detect_pii,
    redact_pii,
)

def test_detect_ssn():
    text = "My SSN is 123-45-6789."
    assert detect_pii(text) == ["SSN"]

def test_detect_credit_card():
    text = "My card number is 4111 1111 1111 1111."
    assert detect_pii(text) == ["CREDIT_CARD"]

def test_detect_email():
    text = "My email is [john@example.com](mailto:john@example.com)."
    assert detect_pii(text) == ["EMAIL"]

def test_detect_phone():
    text = "My phone number is 801-431-1000."
    assert detect_pii(text) == ["PHONE"]

def test_detect_multiple_pii_types():
    text = (
        "My email is [john@example.com](mailto:john@example.com) "
        "and my phone is 801-431-1000."
    )
    assert detect_pii(text) == ["EMAIL", "PHONE"]

def test_redact_ssn():
    text = "My SSN is 123-45-6789."
    assert redact_pii(text) == "My SSN is [SSN]."

def test_redact_credit_card():
    text = "My card is 4111 1111 1111 1111."
    assert redact_pii(text) == "My card is [CREDIT_CARD]."

def test_redact_email():
    text = "Please contact me at [john@example.com](mailto:john@example.com)."
    assert redact_pii(text) == "Please contact me at [EMAIL]."

def test_redact_phone():
    text = "Call me at 801-431-1000."
    assert redact_pii(text) == "Call me at [PHONE]."

def test_redact_multiple_pii_types():
    text = (
        "My email is [john@example.com](mailto:john@example.com) "
        "and my phone is 801-431-1000."
    )

    assert redact_pii(text) == (
        "My email is [EMAIL] "
        "and my phone is [PHONE]."
    )

def test_redact_multiple_occurrences():
    text = (
        "Call 801-431-1000 or "
        "801-555-1234."
    )

    assert redact_pii(text) == (
        "Call [PHONE] or [PHONE]."
    )

def test_no_pii_returns_original_text():
    text = "I need help updating my vehicle map."

    assert detect_pii(text) == []
    assert redact_pii(text) == text

def test_empty_text():
    assert detect_pii("") == []
    assert redact_pii("") == ""

@pytest.mark.parametrize(
    "text",
    [
        "123-45-6789",
        "123 45 6789",
        "4111-1111-1111-1111",
        "4111111111111111",
        "[john@example.com](mailto:john@example.com)",
        "801-431-1000",
        "(801) 431-1000",
        "+1 801-431-1000",
    ],
)

def test_pii_redaction_never_returns_original_sensitive_value(text):
    redacted = redact_pii(text)

    assert redacted != text
    assert "[" in redacted
    assert "]" in redacted
