"""Daily email digest builder.

Every message passes through the policy gate first:
  BLOCKED   → goes to the "shielded" bucket as a category-level notice only.
              Its content is never summarized, stored, or shown.
  SENSITIVE → redacted, flagged, handled without humor downstream.
  SAFE      → redacted (stray secrets still masked), then bucketed.

Buckets: urgent · action · meetings · follow_ups · noise, per the product brief.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

from ..policy.engine import PolicyEngine
from .base import Email

_URGENT_RE = re.compile(
    r"\b(?:urgent|asap|immediately|escalat\w*|critical|penalty|by (?:tomorrow|tonight|eod|"
    r"monday|tuesday|wednesday|thursday|friday)|before (?:wednesday|thursday|friday|eod)|deadline)\b",
    re.IGNORECASE,
)
# Strong signals only — merely *mentioning* a meeting shouldn't hijack the bucket.
_MEETING_RE = re.compile(
    r"\b(?:invitation|invite(?:d)?\b|appointment|calendar invite|conference room|"
    r"call scheduled|confirm (?:your )?attendance)\b", re.IGNORECASE)
_NOISE_RE = re.compile(
    r"\b(?:unsubscribe|newsletter|promo\w*|discount|% off|last chance|limited time|"
    r"webinar recording|you are receiving this)\b", re.IGNORECASE)
_ACTION_RE = re.compile(
    r"\b(?:can you|could you|please (?:approve|review|send|share|confirm)|need your|"
    r"approve|waiting on|request(?:ing)? (?:a|your)|action item|by (?:tuesday|eod|tomorrow))\b",
    re.IGNORECASE,
)
_FOLLOWUP_RE = re.compile(r"^re:|\b(?:following up|follow[- ]up|further to|as discussed|any update)\b",
                          re.IGNORECASE)


def _first_sentence(text: str, width: int = 180) -> str:
    flat = re.sub(r"\s+", " ", text).strip()
    m = re.search(r"(?<=[.!?])\s", flat)
    s = flat[: m.start()] if m and m.start() < width else flat[:width]
    return s.strip()


def build_digest(emails: list[Email], policy: PolicyEngine, vip_senders: list[str],
                 audit=None) -> dict:
    buckets: dict[str, list[dict]] = {
        "urgent": [], "action": [], "meetings": [], "follow_ups": [], "noise": [],
        "shielded": [],
    }

    for e in emails:
        prepared = policy.prepare_text(e.body, sender=e.sender, subject=e.subject)

        if not prepared.allowed:
            # Category-level notice only. No subject, no body, no sender address —
            # the category and arrival time are all MAYA retains.
            buckets["shielded"].append({
                "id": e.id,
                "categories": prepared.categories,
                "date": e.date,
                "note": "Shielded by privacy policy — content not read or summarized.",
            })
            if audit:
                audit.log("email.shielded", target=e.id,
                          detail=f"categories={','.join(prepared.categories)}",
                          sensitivity="BLOCKED", outcome="shielded")
            continue

        red_subject = policy.redactor.redact(e.subject).text
        haystack = f"{e.subject}\n{prepared.text}"
        is_vip = e.sender.lower() in vip_senders
        urgent_hits = len(_URGENT_RE.findall(haystack))
        # A VIP sender using deadline language is urgent even without shouting.
        urgent_score = urgent_hits + (2 if is_vip and urgent_hits else 0)

        item = {
            "id": e.id,
            "sender_name": e.sender_name,
            "subject": red_subject,
            "date": e.date,
            "one_line": _first_sentence(prepared.text),
            "sensitivity": prepared.level,
            "vip": is_vip,
            "why": [],
        }

        if urgent_score >= 2 or _URGENT_RE.search(e.subject or ""):
            item["why"].append("deadline/escalation language" + (" + VIP sender" if is_vip else ""))
            buckets["urgent"].append(item)
        elif _MEETING_RE.search(haystack):
            item["why"].append("meeting/appointment")
            buckets["meetings"].append(item)
        elif _ACTION_RE.search(haystack):
            item["why"].append("asks something of you")
            buckets["action"].append(item)
        elif _FOLLOWUP_RE.search(e.subject or "") or _FOLLOWUP_RE.search(prepared.text):
            item["why"].append("ongoing thread")
            buckets["follow_ups"].append(item)
        elif _NOISE_RE.search(haystack):
            item["why"].append("bulk/promotional")
            buckets["noise"].append(item)
        else:
            item["why"].append("no strong signal")
            buckets["follow_ups"].append(item)

        if audit:
            audit.log("email.read", target=e.id, detail=f"bucket ok, level={prepared.level}",
                      sensitivity=prepared.level)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "counts": {k: len(v) for k, v in buckets.items()},
        "buckets": buckets,
        "source_note": "Mock inbox — fictional sample data",
    }
