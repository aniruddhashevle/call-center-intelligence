import pytest

from src.security.pii_redactor import detect_pii, redact_pii


@pytest.mark.parametrize(
    "phone",
    [
        "123-456-7890",
        "(123) 456-7890",
        "+1 123-456-7890",
        "123.456.7890",
        "123 456 7890",
    ],
)
def test_phone_formats(phone):
    assert "PHONE" in detect_pii(phone)
    assert "[PHONE]" in redact_pii(phone)


@pytest.mark.parametrize(
    "email",
    [
        "john@example.com",
        "john.smith@example.co.uk",
        "support+test@example.org",
    ],
)
def test_email_formats(email):
    assert "EMAIL" in detect_pii(email)
    assert "[EMAIL]" in redact_pii(email)


@pytest.mark.parametrize(
    "ssn",
    [
        "123-45-6789",
        "987-65-4321",
    ],
)
def test_ssn_formats(ssn):
    assert "SSN" in detect_pii(ssn)
    assert "[SSN]" in redact_pii(ssn)


@pytest.mark.parametrize(
    "card",
    [
        "4111 1111 1111 1111",
        "4111-1111-1111-1111",
        "4111111111111111",
    ],
)
def test_credit_card_formats(card):
    assert "CREDIT_CARD" in detect_pii(card)
    assert "[CREDIT_CARD]" in redact_pii(card)


def test_pii_embedded_in_conversation():
    text = (
        "My name is John. "
        "My phone is 123-456-7890. "
        "My email is john@example.com. "
        "My SSN is 123-45-6789."
    )

    result = redact_pii(text)

    assert "[PHONE]" in result
    assert "[EMAIL]" in result
    assert "[SSN]" in result

    assert "123-456-7890" not in result
    assert "john@example.com" not in result
    assert "123-45-6789" not in result


def test_clean_text_is_unchanged():
    text = "Hello, I need help with my account."

    assert redact_pii(text) == text
    assert detect_pii(text) == []