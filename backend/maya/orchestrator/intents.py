"""Rule-based command parser for voice and chat input.

Deterministic and testable: wake-phrase stripping, intent patterns in priority
order, slot extraction (file queries, modes, ordinals), and clarification
questions when a required slot is missing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_ORDINALS = {
    "first": 1, "1st": 1, "second": 2, "2nd": 2, "third": 3, "3rd": 3,
    "fourth": 4, "4th": 4, "fifth": 5, "5th": 5, "last": -1,
}

_FILLER_RE = re.compile(
    r"\b(?:the|a|an|my|me|for me|please|that|this|file|files|document|documents|doc|named|called)\b",
    re.IGNORECASE,
)


@dataclass
class Intent:
    name: str
    slots: dict = field(default_factory=dict)
    clarify: str | None = None
    raw: str = ""

    def to_dict(self) -> dict:
        return {"name": self.name, "slots": self.slots, "clarify": self.clarify}


def strip_wake_phrase(text: str, wake_phrases: list[str]) -> tuple[str, bool]:
    t = text.strip()
    for wake in sorted(wake_phrases, key=len, reverse=True):
        m = re.match(rf"^\s*{re.escape(wake)}[\s,.!:-]+", t, flags=re.IGNORECASE)
        if m:
            return t[m.end():].strip(), True
    # bare wake word ("Maya?") — treat as a greeting trigger
    for wake in wake_phrases:
        if t.lower().rstrip("?!. ") == wake:
            return "", True
    return t, False


def _clean_query(fragment: str) -> str:
    q = _FILLER_RE.sub(" ", fragment)
    q = re.sub(r"[\"'?.!,]", " ", q)
    return re.sub(r"\s+", " ", q).strip()


def _ordinal_of(text: str) -> int | None:
    m = re.search(r"\b(first|second|third|fourth|fifth|1st|2nd|3rd|4th|5th|last)\b[\s-]*(?:one|file|result|doc|document|email)?",
                  text, re.IGNORECASE)
    if m:
        return _ORDINALS[m.group(1).lower()]
    if re.search(r"^\s*(it|that one|this one|that)\s*$", text, re.IGNORECASE):
        return -1
    return None


def _mode_of(text: str) -> str:
    if re.search(r"\b(detail|detailed|in depth|long|full)\b", text, re.IGNORECASE):
        return "detailed"
    if re.search(r"\b(short|brief|briefly|quick|tl;?dr|one[- ]liner)\b", text, re.IGNORECASE):
        return "short"
    return "medium"


def parse_command(text: str, wake_phrases: list[str] | None = None) -> Intent:
    raw = text or ""
    t, woke = strip_wake_phrase(raw, wake_phrases or ["maya", "hey maya", "ok maya"])
    low = t.lower().strip()

    def intent(name: str, slots: dict | None = None, clarify: str | None = None) -> Intent:
        return Intent(name=name, slots=slots or {}, clarify=clarify, raw=raw)

    if not low:
        return intent("greeting") if woke else intent("unknown")

    # -- confirmation gate replies (spoken or typed) ---------------------------
    words = set(re.findall(r"[a-z']+", low))
    if words and words <= {"yes", "yeah", "yep", "sure", "ok", "okay", "confirm",
                           "confirmed", "approve", "approved", "go", "ahead", "do",
                           "it", "proceed", "please"}:
        return intent("confirm")
    if words and words <= {"no", "nope", "cancel", "cancelled", "stop", "abort",
                           "never", "mind", "nevermind", "don't", "dont", "it",
                           "leave", "forget"} and not low.startswith("forget"):
        return intent("cancel")

    # -- meta ---------------------------------------------------------------------
    if re.search(r"\b(help|what can you do|capabilities|how do you work)\b", low):
        return intent("help")
    if len(low.split()) <= 4 and re.match(
            r"^(hi|hello|hey|namaskaram|namaste|good\s+(morning|afternoon|evening))\b", low):
        return intent("greeting")

    # -- memory & reminders ---------------------------------------------------------
    if re.search(r"\b(what do you know about me|show (my )?memor(y|ies)|list memor(y|ies)|review memory)\b", low):
        return intent("memory_show")
    m = re.match(r"^forget\s+(?:that\s+|the\s+|about\s+)?(.+)$", low)
    if m:
        return intent("memory_forget", {"query": _clean_query(m.group(1))})
    m = re.match(r"^remember\s+(?:that\s+)?(.+)$", t, re.IGNORECASE)
    if m:
        return intent("remember", {"value": m.group(1).strip()})
    m = re.match(r"^remind me\s+(?:to\s+)?(.+)$", t, re.IGNORECASE)
    if m:
        return intent("remind", {"value": m.group(1).strip()})

    # -- email --------------------------------------------------------------------
    if re.search(r"\b(email|emails|inbox|mail)\b", low) and re.search(
            r"\b(summari[sz]e|digest|check|read|triage|important|what'?s in)\b", low):
        return intent("email_digest")
    if re.search(r"\b(email|inbox)\s+(digest|summary|briefing)\b", low):
        return intent("email_digest")

    # -- draft reply -------------------------------------------------------------
    m = re.search(r"\b(?:draft|write|compose)\s+(?:a\s+|an\s+)?(?:reply|response)(?:\s+to\s+(.+))?", low)
    if m:
        ref = m.group(1)
        slots: dict = {}
        if ref:
            ordinal = _ordinal_of(ref)
            if ordinal:
                slots["ordinal"] = ordinal
            else:
                slots["query"] = _clean_query(ref)
        return intent("draft_reply", slots)

    # -- briefing / prioritization ---------------------------------------------------
    if re.search(r"\b(prioriti[sz]e|briefing|brief me(?! on)|my day|plan (for )?today|"
                 r"what should i (do|focus on)|top priorities|start my day)\b", low):
        return intent("briefing")

    # -- compare -----------------------------------------------------------------------
    if re.search(r"\bcompare\b|\bdiff\b|\bversus\b|\bvs\.?\b", low):
        names = re.findall(r"[\"“']([^\"”']+)[\"”']", t)
        if len(names) >= 2:
            return intent("compare_files", {"a": names[0], "b": names[1]})
        m = re.search(r"compare\s+(.+?)\s+(?:and|with|to|vs\.?|versus)\s+(.+)$", low)
        if m and not re.search(r"\b(these|those|them|the two)\b", low):
            return intent("compare_files",
                          {"a": _clean_query(m.group(1)), "b": _clean_query(m.group(2))})
        # "compare these two files" → resolve from session context
        return intent("compare_files", {"use_context": True})

    # -- tasks from a doc ------------------------------------------------------------
    m = re.search(r"\b(?:action items|tasks|to-?dos)\b(?:\s+(?:from|in|for)\s+(.+))?", low)
    if m and re.search(r"\b(extract|pull|list|get|what are|show|find)\b", low):
        target = m.group(1)
        slots = {}
        if target:
            ordinal = _ordinal_of(target)
            if ordinal:
                slots["ordinal"] = ordinal
            else:
                slots["query"] = _clean_query(target)
        return intent("extract_tasks", slots)

    # -- gated file operations -----------------------------------------------------
    m = re.match(r"^(?:move|archive)\s+(.+?)\s+(?:to|into)\s+(.+)$", low)
    if m:
        return intent("move_file", {"query": _clean_query(m.group(1)),
                                    "dest": m.group(2).strip().rstrip(".")})
    m = re.match(r"^(?:delete|trash)\s+(.+)$", low)
    if m:
        target = m.group(1)
        ordinal = _ordinal_of(target)
        slots = {"ordinal": ordinal} if ordinal else {"query": _clean_query(target)}
        return intent("delete_file", slots)

    # -- summarize file ---------------------------------------------------------------
    m = re.search(r"\b(?:summari[sz]e|tl;?dr(?: of)?|brief me on)\s+(.+)$", low)
    if m:
        target = m.group(1)
        mode = _mode_of(low)
        target = re.sub(r"\b(in detail|in depth|briefly|short(ly)?|detailed?|quick(ly)?)\b", "", target)
        ordinal = _ordinal_of(target)
        if ordinal:
            return intent("summarize_file", {"ordinal": ordinal, "mode": mode})
        q = _clean_query(target)
        if not q:
            return intent("summarize_file", {"mode": mode},
                          clarify="Which document should I summarize?")
        return intent("summarize_file", {"query": q, "mode": mode})

    # -- open/read → summarize medium ----------------------------------------------
    m = re.match(r"^(?:open|read|show me|show)\s+(.+)$", low)
    if m and re.search(r"\b(sop|report|notes?|review|summary|csv|pdf|docx?|md)\b", low):
        ordinal = _ordinal_of(m.group(1))
        if ordinal:
            return intent("summarize_file", {"ordinal": ordinal, "mode": "medium"})
        return intent("summarize_file", {"query": _clean_query(m.group(1)), "mode": "medium"})

    # -- find files -------------------------------------------------------------------
    if re.match(r"^(?:find|search|locate)$", low):
        return intent("find_file", {}, clarify="What should I look for?")
    m = re.search(r"\b(?:find|search(?:\s+for)?|locate|look for|where(?:'s| is))\s+(.+)$", low)
    if m:
        target = m.group(1)
        latest = bool(re.search(r"\b(latest|newest|most recent|recent)\b", low))
        ftype = None
        tm = re.search(r"\b(pdf|csv|docx|txt|md|markdown)\b", target)
        if tm:
            ftype = {"markdown": "md"}.get(tm.group(1), tm.group(1))
        q = _clean_query(re.sub(r"\b(latest|newest|most recent|recent)\b", "", target))
        if not q and not ftype:
            return intent("find_file", {}, clarify="What should I look for?")
        return intent("find_file", {"query": q, "latest": latest,
                                    **({"type": ftype} if ftype else {})})

    return intent("unknown")
