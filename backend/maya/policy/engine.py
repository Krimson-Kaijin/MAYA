"""Policy engine — the single choke point for privacy decisions.

Answers three questions:
  1. May MAYA read this path?           (allowlist + denylist)
  2. May MAYA use this text?            (classify → redact → PreparedContent)
  3. May MAYA perform this action now?  (safe / gated / forbidden)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .redaction import Redactor
from .sensitivity import BLOCKED, SAFE, Classification, SensitivityClassifier


@dataclass
class PreparedContent:
    """Text after the policy gate. When ``allowed`` is False the text is empty
    and only the classification survives — callers never see blocked content."""

    allowed: bool
    level: str
    categories: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)
    text: str = ""
    redactions: dict[str, int] = field(default_factory=dict)


class PolicyEngine:
    def __init__(self, config):
        self.config = config
        self.classifier = SensitivityClassifier(config.policy)
        self.redactor = Redactor(config.policy)
        actions = (config.policy or {}).get("actions", {})
        self._safe = set(actions.get("safe", []) or [])
        self._gated = set(actions.get("gated", []) or [])
        self._forbidden = set(actions.get("forbidden", []) or [])
        self.confirmation_timeout = int(actions.get("confirmation_timeout_seconds", 180))

    # -- path permissions -------------------------------------------------------
    def is_path_allowed(self, path: Path | str) -> bool:
        p = Path(path).resolve()
        inside = False
        for folder in self.config.approved_folders:
            try:
                p.relative_to(folder)
                inside = True
                break
            except ValueError:
                continue
        if not inside:
            return False
        lowered = [part.lower() for part in p.parts]
        for pattern in self.config.denied_patterns:
            if any(pattern in part for part in lowered):
                return False
        return True

    # -- content gate -------------------------------------------------------------
    def prepare_text(self, text: str, sender: str = "", subject: str = "") -> PreparedContent:
        cls: Classification = self.classifier.classify(text, sender=sender, subject=subject)
        if cls.level == BLOCKED:
            return PreparedContent(
                allowed=False, level=BLOCKED,
                categories=cls.categories, reasons=cls.reasons,
            )
        red = self.redactor.redact(text)
        return PreparedContent(
            allowed=True, level=cls.level or SAFE,
            categories=cls.categories, reasons=cls.reasons,
            text=red.text, redactions=red.replacements,
        )

    # -- action risk ---------------------------------------------------------------
    def action_risk(self, action: str) -> str:
        if action in self._forbidden:
            return "forbidden"
        if action in self._gated:
            return "gated"
        if action in self._safe:
            return "safe"
        # Unknown actions are treated as gated — fail closed, but let the user decide.
        return "gated"
