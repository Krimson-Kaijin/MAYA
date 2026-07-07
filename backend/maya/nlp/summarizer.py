"""Summarization for MAYA.

The default engine is a LOCAL EXTRACTIVE summarizer: it scores sentences by
normalized word frequency, position, and numeric-content bonus, then returns the
top sentences in document order. Deterministic, fast, fully offline, and honest —
it selects the document's own sentences; it does not paraphrase.

``LLMSummarizer`` is the clearly-marked plug-in point for an API-backed model.
It is NOT configured in this prototype and refuses to pretend otherwise.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field

_MODES = {"short": 2, "medium": 4, "detailed": 7}

_STOPWORDS = set(
    """a an the and or but if then than that this these those of in on at for to from by
    with as is are was were be been being it its it's we our you your they their he she
    his her not no do does did done have has had having will would should could can may
    must into over under about after before during between within per each any all some
    more most much many such only also just very there here when where which who whom
    what how why while so because through up down out off again once i""".split()
)

_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(])|\n{2,}")
_WORD = re.compile(r"[a-z0-9']+")


@dataclass
class Summary:
    mode: str
    headline: str
    bullets: list[str] = field(default_factory=list)
    original_words: int = 0
    engine: str = "extractive-local"

    def to_dict(self) -> dict:
        return {
            "mode": self.mode, "headline": self.headline, "bullets": self.bullets,
            "original_words": self.original_words, "engine": self.engine,
        }

    @property
    def text(self) -> str:
        return " ".join(self.bullets)


def split_sentences(text: str) -> list[str]:
    # Strip markdown decorations but keep the words.
    clean = re.sub(r"^#{1,6}\s*", "", text, flags=re.MULTILINE)
    clean = re.sub(r"[*_`]{1,3}", "", clean)
    parts = _SENT_SPLIT.split(clean)
    out = []
    for p in parts:
        s = re.sub(r"\s+", " ", p).strip(" -•\t")
        if s and len(s.split()) >= 4:
            out.append(s)
    return out


def first_heading(text: str) -> str | None:
    m = re.search(r"^#{1,3}\s+(.+)$", text, flags=re.MULTILINE)
    return m.group(1).strip() if m else None


class ExtractiveSummarizer:
    name = "extractive-local"

    def summarize(self, text: str, mode: str = "medium") -> Summary:
        n_target = _MODES.get(mode, _MODES["medium"])
        sentences = split_sentences(text)
        words_total = len(_WORD.findall(text.lower()))
        headline = first_heading(text) or (sentences[0][:120] if sentences else "")

        if len(sentences) <= n_target:
            return Summary(mode=mode, headline=headline, bullets=sentences,
                           original_words=words_total)

        freq: dict[str, int] = {}
        for s in sentences:
            for w in _WORD.findall(s.lower()):
                if w not in _STOPWORDS and len(w) > 2:
                    freq[w] = freq.get(w, 0) + 1
        max_f = max(freq.values()) if freq else 1

        scored: list[tuple[float, int, str]] = []
        for idx, s in enumerate(sentences):
            words = [w for w in _WORD.findall(s.lower()) if w in freq]
            if not words:
                continue
            base = sum(freq[w] / max_f for w in words) / (len(words) ** 0.6)
            if idx == 0:
                base += 0.35            # opening sentence usually frames the doc
            if re.search(r"\d", s):
                base += 0.15            # business docs: numbers carry the signal
            if len(s.split()) > 55:
                base -= 0.2             # penalize run-ons
            scored.append((base, idx, s))

        scored.sort(key=lambda t: -t[0])
        chosen = sorted(scored[:n_target], key=lambda t: t[1])
        return Summary(mode=mode, headline=headline,
                       bullets=[s for _, _, s in chosen],
                       original_words=words_total)


class NotConfiguredError(RuntimeError):
    pass


class LLMSummarizer:
    """Plug-in point for an API-backed abstractive summarizer.

    NOT CONFIGURED in this prototype: it requires MAYA_LLM_API_KEY and a real
    client implementation. It exists so the swap is one line in get_summarizer —
    the policy pipeline (classify → redact → summarize) stays identical.
    """

    name = "llm-api"

    def summarize(self, text: str, mode: str = "medium") -> Summary:
        raise NotConfiguredError(
            "LLM summarization is not configured. Set MAYA_LLM_API_KEY and implement "
            "the client call in LLMSummarizer.summarize(). MAYA falls back to the "
            "local extractive engine by default."
        )


def get_summarizer(config=None):
    if os.environ.get("MAYA_LLM_API_KEY"):
        # A real deployment would return a configured LLMSummarizer here.
        # The prototype stays honest: extractive unless someone writes the client.
        pass
    return ExtractiveSummarizer()
