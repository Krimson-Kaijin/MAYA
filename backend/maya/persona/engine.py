"""MAYA's personality layer.

Every reply is composed as: core answer FIRST, optional quip second. Quips come
only from the reviewed pools in config/personality.yaml — the engine cannot
invent sarcasm, which keeps the personality bounded by construction.

Hard guardrails enforced in code (not just documented):
  - zero humor when sensitivity is SENSITIVE or BLOCKED, or on refusals/errors;
  - a wit budget (ratio per level, never two quips in a row);
  - no quip repeated within the configured window;
  - wit_level "off" silences all of it.
"""

from __future__ import annotations

import random
from collections import deque

from ..policy.sensitivity import SAFE

_CATEGORY_LABELS = {
    "banking": "banking",
    "payments_cards": "payment-card",
    "investments": "investment",
    "tax": "tax",
    "payroll": "payroll",
    "credentials": "credential (OTP/password)",
    "government_id": "government-ID",
    "health": "health",
    "legal": "legal",
    "personal": "personal",
}


class Persona:
    def __init__(self, personality_cfg: dict, wit_level: str = "classic",
                 telugu_flair: bool = True, rng: random.Random | None = None):
        cfg = personality_cfg or {}
        self.identity = cfg.get("identity", {})
        self.name = self.identity.get("name", "MAYA")
        self._quips: dict[str, list[str]] = cfg.get("quips", {}) or {}
        wit = cfg.get("wit", {}) or {}
        self._ratios: dict[str, float] = wit.get("ratio", {"subtle": 0.18, "classic": 0.38})
        self._recent: deque[str] = deque(maxlen=int(wit.get("no_repeat_window", 6)))
        self._flair = (cfg.get("telugu_flair", {}) or {}) if telugu_flair else {}
        self.wit_level = wit_level
        self._rng = rng or random.Random()
        self._plain_streak = 1  # allow a quip on the first eligible response

    # -- wit budget ---------------------------------------------------------------
    def set_wit_level(self, level: str) -> None:
        if level in ("off", "subtle", "classic"):
            self.wit_level = level

    def _quip_allowed(self) -> bool:
        if self.wit_level == "off":
            return False
        if self._plain_streak < 1:  # never two witty replies in a row
            return False
        ratio = float(self._ratios.get(self.wit_level, 0))
        return self._rng.random() < ratio

    def _pick(self, pool: str) -> str | None:
        lines = [q for q in self._quips.get(pool, []) if q not in self._recent]
        if not lines:
            return None
        return self._rng.choice(lines)

    # -- composition -----------------------------------------------------------------
    def compose(self, core: str, pool: str | None = None,
                sensitivity: str = SAFE, allow_wit: bool = True) -> str:
        """Core answer first; a quip only when every guardrail passes."""
        witty = (
            allow_wit
            and sensitivity == SAFE
            and pool is not None
            and self._quip_allowed()
        )
        if not witty:
            self._plain_streak += 1
            return core
        quip = self._pick(pool)
        if quip is None:
            self._plain_streak += 1
            return core
        self._recent.append(quip)
        self._plain_streak = 0
        return f"{core} {quip}" if core else quip

    # -- fixed-tone pieces --------------------------------------------------------------
    def refusal(self, categories: list[str], what: str = "that content") -> str:
        """Plain, respectful, zero humor — used for BLOCKED material."""
        names = sorted({_CATEGORY_LABELS.get(c, c) for c in categories}) or ["restricted"]
        label = " and ".join(names)
        return (
            f"That looks like {label} content. Per your privacy policy, I don't read, "
            f"summarize, or store it — {what} stays shielded."
        )

    def shielded_note(self, count: int, categories: list[str]) -> str:
        names = sorted({_CATEGORY_LABELS.get(c, c) for c in categories})
        cats = ", ".join(names) if names else "restricted"
        plural = "email" if count == 1 else "emails"
        return (f"{count} {plural} ({cats}) arrived and stayed shielded — "
                f"I didn't read or summarize them.")

    def greeting(self, hour: int) -> str:
        flair = self._flair.get("greeting", [])
        base = flair[0] if flair else "Hello."
        if hour < 12:
            pool = self._quips.get("greeting_morning", [])
        elif hour >= 17:
            pool = self._quips.get("greeting_evening", [])
        else:
            pool = []
        if pool and self.wit_level != "off":
            return f"{base} {pool[0]}"
        return f"{base} How can I help?"

    def ack(self) -> str:
        lines = self._flair.get("ack", [])
        return lines[0] if lines else "Done."
