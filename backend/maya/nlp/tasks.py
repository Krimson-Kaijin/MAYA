"""Task-layer extraction: action items, deadlines, entities, risks.

Heuristic and deterministic. Understands the common markdown pattern of an
"Action items" / "Risks" section, and falls back to cue-based sentence scanning
for unstructured text.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .summarizer import split_sentences

_ACTION_CUES = re.compile(
    r"\b(?:must|should|need(?:s)? to|has to|have to|will (?:send|share|draft|review|push|pilot|prepare)|"
    r"to (?:send|share|draft|review|approve|verify|re-verify|push|pilot|complete)|"
    r"due|deadline|by (?:monday|tuesday|wednesday|thursday|friday|saturday|sunday|eod|end of|tomorrow|next week)|"
    r"action item|todo|please (?:send|share|review|approve|confirm))\b",
    re.IGNORECASE,
)

_DEADLINE_PATTERNS = [
    r"\b\d{4}-\d{2}-\d{2}\b",
    r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+\d{1,2}\b",
    r"\b\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\b",
    r"\bby\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday|tomorrow|eod|end of (?:day|week|month)|noon)\b",
    r"\b(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)\s+(?:eod|noon|morning|evening)\b",
]
_DEADLINE_RE = re.compile("|".join(_DEADLINE_PATTERNS), re.IGNORECASE)

_RISK_CUES = re.compile(
    r"\b(?:risk|risks|penalt|blocker|blocked on|concern|delay|escalat|dependen|fragile|"
    r"miss(?:es|ed)? the|slip(?:s|ping|ped)?|threshold|single[- ]vendor|backlog)\b",
    re.IGNORECASE,
)

_ENTITY_RE = re.compile(r"\b(?:[A-Z][a-z]{2,}\s){1,3}(?:[A-Z][a-z]{2,})\b|\b[A-Z]{2,5}-\d{3,6}\b")

_SECTION_RE = re.compile(r"^#{1,4}\s*(action items?|risks?|to[- ]?dos?)\s*$", re.IGNORECASE | re.MULTILINE)


@dataclass
class TaskReport:
    action_items: list[str] = field(default_factory=list)
    deadlines: list[str] = field(default_factory=list)
    entities: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "action_items": self.action_items, "deadlines": self.deadlines,
            "entities": self.entities, "risks": self.risks,
        }


def _section_bullets(text: str, kinds: tuple[str, ...]) -> list[str]:
    out: list[str] = []
    for m in _SECTION_RE.finditer(text):
        if not m.group(1).lower().startswith(kinds):
            continue
        tail = text[m.end():]
        nxt = re.search(r"^#{1,4}\s", tail, flags=re.MULTILINE)
        block = tail[: nxt.start()] if nxt else tail
        for line in block.splitlines():
            line = line.strip()
            if line.startswith(("-", "*", "•")):
                item = line.lstrip("-*• ").strip()
                if item:
                    out.append(item)
    return out


def extract_action_items(text: str, limit: int = 10) -> list[str]:
    items = _section_bullets(text, ("action", "to"))
    if items:
        return items[:limit]
    found = []
    for s in split_sentences(text):
        if _ACTION_CUES.search(s):
            found.append(s)
    return found[:limit]


def extract_deadlines(text: str, limit: int = 10) -> list[str]:
    seen, out = set(), []
    for m in _DEADLINE_RE.finditer(text):
        token = re.sub(r"\s+", " ", m.group(0)).strip()
        key = token.lower()
        if key not in seen:
            seen.add(key)
            out.append(token)
    return out[:limit]


def extract_entities(text: str, limit: int = 8) -> list[str]:
    counts: dict[str, int] = {}
    for m in _ENTITY_RE.finditer(text):
        name = re.sub(r"\s+", " ", m.group(0)).strip()
        # Drop sentence-starting false positives like "The Documentation".
        if name.split()[0].lower() in {"the", "this", "that", "these", "every", "all"}:
            continue
        counts[name] = counts.get(name, 0) + 1
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    return [name for name, _ in ranked[:limit]]


def extract_risks(text: str, limit: int = 6) -> list[str]:
    items = _section_bullets(text, ("risk",))
    if items:
        return items[:limit]
    found = []
    for s in split_sentences(text):
        if _RISK_CUES.search(s):
            found.append(s)
    return found[:limit]


def analyze(text: str) -> TaskReport:
    return TaskReport(
        action_items=extract_action_items(text),
        deadlines=extract_deadlines(text),
        entities=extract_entities(text),
        risks=extract_risks(text),
    )
