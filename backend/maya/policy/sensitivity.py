"""SAFE / SENSITIVE / BLOCKED content classification.

Rules come from config/policy.yaml (keyword and sender-domain lists) plus a few
structural detectors that don't belong in YAML: Luhn-valid card numbers, PAN,
IFSC, Aadhaar-shaped numbers, and OTP codes.

BLOCKED means: never summarized, never stored, never displayed — the rest of the
system only ever sees the category name.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

SAFE = "SAFE"
SENSITIVE = "SENSITIVE"
BLOCKED = "BLOCKED"

_PAN_RE = re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b")
_IFSC_RE = re.compile(r"\b[A-Z]{4}0[A-Z0-9]{6}\b")
# 4-4-4 digit groups that are NOT part of a longer (e.g. 16-digit card) number.
_AADHAAR_RE = re.compile(r"(?<!\d)(?<!\d[ \-])\b\d{4}[ \-]\d{4}[ \-]\d{4}\b(?![ \-]?\d)")
_CARDISH_RE = re.compile(r"\b(?:\d[ \-]?){13,19}\b")
_OTP_RE = re.compile(
    r"(?i)\b(?:otp|one[- ]time password|verification code|2fa code)\b\D{0,20}\d{4,8}"
)
_SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")


def luhn_valid(digits: str) -> bool:
    if not digits.isdigit() or not 13 <= len(digits) <= 19:
        return False
    total, alt = 0, False
    for ch in reversed(digits):
        d = ord(ch) - 48
        if alt:
            d *= 2
            if d > 9:
                d -= 9
        total += d
        alt = not alt
    return total % 10 == 0


def _find_card_numbers(text: str) -> bool:
    for m in _CARDISH_RE.finditer(text):
        digits = re.sub(r"[ \-]", "", m.group(0))
        if luhn_valid(digits):
            return True
    return False


@dataclass
class Classification:
    level: str = SAFE
    categories: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)

    @property
    def blocked(self) -> bool:
        return self.level == BLOCKED

    def to_dict(self) -> dict:
        return {"level": self.level, "categories": self.categories, "reasons": self.reasons}


class SensitivityClassifier:
    def __init__(self, policy_cfg: dict):
        sens = (policy_cfg or {}).get("sensitivity", {})
        self._blocked_rules = self._compile(sens.get("blocked", {}))
        self._sensitive_rules = self._compile(sens.get("sensitive", {}))
        self._sender_domains: list[tuple[str, str]] = []
        for cat, spec in (sens.get("blocked", {}) or {}).items():
            for dom in (spec or {}).get("sender_domains", []) or []:
                self._sender_domains.append((cat, dom.lower()))

    @staticmethod
    def _compile(rules: dict) -> list[tuple[str, re.Pattern]]:
        compiled = []
        for cat, spec in (rules or {}).items():
            words = (spec or {}).get("keywords", []) or []
            if not words:
                continue
            pattern = "|".join(
                r"\b" + re.escape(w.lower()).replace(r"\ ", r"\s+") + r"\b" for w in words
            )
            compiled.append((cat, re.compile(pattern)))
        return compiled

    def classify(self, text: str, sender: str = "", subject: str = "") -> Classification:
        haystack = f"{subject}\n{text}".lower()
        result = Classification()

        # Structural detectors first — these are BLOCKED regardless of keywords.
        raw = f"{subject}\n{text}"
        if _find_card_numbers(raw):
            self._mark(result, BLOCKED, "payments_cards", "card-number pattern (Luhn)")
        if _PAN_RE.search(raw):
            self._mark(result, BLOCKED, "government_id", "PAN pattern")
        if _AADHAAR_RE.search(raw):
            self._mark(result, BLOCKED, "government_id", "Aadhaar-shaped number")
        if _SSN_RE.search(raw):
            self._mark(result, BLOCKED, "government_id", "SSN pattern")
        if _IFSC_RE.search(raw):
            self._mark(result, BLOCKED, "banking", "IFSC code")
        if _OTP_RE.search(raw):
            self._mark(result, BLOCKED, "credentials", "OTP code")

        # Sender-domain rules (bank / payment senders are blocked outright).
        s = (sender or "").lower()
        for cat, dom in self._sender_domains:
            if dom in s:
                self._mark(result, BLOCKED, cat, f"sender domain '{dom}'")

        # Keyword rules from policy.yaml.
        for cat, rx in self._blocked_rules:
            m = rx.search(haystack)
            if m:
                self._mark(result, BLOCKED, cat, f"keyword '{m.group(0)}'")
        for cat, rx in self._sensitive_rules:
            m = rx.search(haystack)
            if m:
                self._mark(result, SENSITIVE, cat, f"keyword '{m.group(0)}'")

        return result

    @staticmethod
    def _mark(result: Classification, level: str, category: str, reason: str) -> None:
        rank = {SAFE: 0, SENSITIVE: 1, BLOCKED: 2}
        if rank[level] > rank[result.level]:
            result.level = level
        if category not in result.categories:
            result.categories.append(category)
        if reason not in result.reasons:
            result.reasons.append(reason)
