"""Redaction: sensitive spans are masked before any NLP or display."""


def test_card_number_redacted(policy):
    r = policy.redactor.redact("Paid with 4539 1488 0343 6467 at the counter.")
    assert "4539" not in r.text
    assert "[REDACTED:CARD_NUMBER]" in r.text
    assert r.replacements.get("CARD_NUMBER") == 1


def test_non_luhn_number_preserved(policy):
    r = policy.redactor.redact("Tracking reference 1234 5678 9012 3453 for your box.")
    assert "1234 5678 9012 3453" in r.text


def test_otp_code_redacted(policy):
    r = policy.redactor.redact("Your one-time password is 482913, valid 10 minutes.")
    assert "482913" not in r.text
    assert "[REDACTED:OTP_CODE]" in r.text


def test_pan_and_ifsc_redacted(policy):
    r = policy.redactor.redact("PAN ABCDE1234F, IFSC HDFC0001234.")
    assert "ABCDE1234F" not in r.text
    assert "HDFC0001234" not in r.text
    assert r.total == 2


def test_password_redacted(policy):
    r = policy.redactor.redact("The wifi password is s3cretV@lue for guests.")
    assert "s3cretV@lue" not in r.text
    assert "[REDACTED:PASSWORD]" in r.text


def test_aadhaar_shaped_redacted(policy):
    r = policy.redactor.redact("ID on file: 1234 5678 9123.")
    assert "1234 5678 9123" not in r.text


def test_plain_business_text_untouched(policy):
    text = "SOP v3 reduces documentation turnaround from 24 hours to 12 hours."
    r = policy.redactor.redact(text)
    assert r.text == text
    assert r.total == 0
