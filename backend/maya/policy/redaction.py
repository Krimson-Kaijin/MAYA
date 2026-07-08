"""Redaction layer: masks sensitive spans before ANY text reaches the
summarizer, the UI, or storage. Applied even to SAFE documents — a stray card
number in a meeting note still gets masked.

Patterns come from config/policy.yaml → redaction.patterns. A pattern marked
``luhn: true`` only redacts digit runs that pass the Luhn check (avoids eating
consignment IDs and phone-length numbers that aren't cards).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class RedactionResult:
    text: str
    replacements: dict[str, int] = field(default_factory=dict)

    @property
    def total(self) -> int:
        return sum(self.replacements.values())


class Redactor:
    def __init__(self, policy_cfg: dict):
        self._patterns: list[tuple[str, re.Pattern, bool]] = []
        for spec in ((policy_cfg or {}).get("redaction", {}) or {}).get("patterns", []) or []:
            try:
                rx = re.compile(spec["regex"])
            except re.error:
                continue
            self._patterns.append((spec["name"], rx, bool(spec.get("luhn", False))))

    def redact(self, text: str) -> RedactionResult:
        counts: dict[str, int] = {}
        out = text
        for name, rx, needs_luhn in self._patterns:
            def _sub(m: re.Match) -> str:
                if needs_luhn:
                    digits = re.sub(r"\D", "", m.group(0))
                    from .sensitivity import luhn_valid
                    if not luhn_valid(digits):
                        return m.group(0)
                counts[name] = counts.get(name, 0) + 1
                return f"[REDACTED:{name}]"

            out = rx.sub(_sub, out)
        return RedactionResult(text=out, replacements=counts)
