"""Sensitivity classification: SAFE / SENSITIVE / BLOCKED."""


def test_luhn_valid_card_is_blocked(policy):
    c = policy.classifier.classify("Payment made with card 4539 1488 0343 6467 yesterday.")
    assert c.level == "BLOCKED"
    assert "payments_cards" in c.categories


def test_non_luhn_digits_are_not_cards(policy):
    # 16 digits that fail Luhn — must NOT be blocked as a card.
    c = policy.classifier.classify("Reference code 1234 5678 9012 3453 for the shipment.")
    assert "payments_cards" not in c.categories


def test_otp_is_blocked(policy):
    c = policy.classifier.classify("Your OTP for login is 482913. Do not share it.")
    assert c.level == "BLOCKED"
    assert "credentials" in c.categories


def test_pan_is_blocked(policy):
    c = policy.classifier.classify("KYC done, PAN ABCDE1234F on record.")
    assert c.level == "BLOCKED"
    assert "government_id" in c.categories


def test_payroll_is_blocked(policy):
    c = policy.classifier.classify("Please find attached your payslip for June 2026.")
    assert c.level == "BLOCKED"
    assert "payroll" in c.categories


def test_bank_sender_is_blocked(policy):
    c = policy.classifier.classify("Greetings of the day.", sender="alerts@hdfcbank.example")
    assert c.level == "BLOCKED"
    assert "banking" in c.categories


def test_ifsc_is_blocked(policy):
    c = policy.classifier.classify("Transfer to HDFC0001234 branch account.")
    assert c.level == "BLOCKED"


def test_health_is_sensitive_not_blocked(policy):
    c = policy.classifier.classify(
        "Appointment with Dr. Sudha on Thursday. Carry the blood test report.")
    assert c.level == "SENSITIVE"
    assert "health" in c.categories


def test_legal_is_sensitive(policy):
    c = policy.classifier.classify("We received a legal notice from the vendor's attorney.")
    assert c.level == "SENSITIVE"


def test_business_text_is_safe(policy):
    c = policy.classifier.classify(
        "Carrier pickup must be confirmed in the TMS with photo proof of sealed loading. "
        "Consignment HYD-88214 was delayed 26 hours due to driver shortage.")
    assert c.level == "SAFE"
    assert c.categories == []
