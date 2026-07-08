"""Two-document comparison: summaries side by side, shared vs distinctive
vocabulary, per-document action items, and metadata deltas."""

from __future__ import annotations

import re
from collections import Counter

from .summarizer import ExtractiveSummarizer, _STOPWORDS, _WORD
from .tasks import extract_action_items, extract_deadlines


def _top_terms(text: str, n: int = 30) -> Counter:
    counts: Counter = Counter()
    for w in _WORD.findall(text.lower()):
        if w not in _STOPWORDS and len(w) > 3 and not w.isdigit():
            counts[w] += 1
    return Counter(dict(counts.most_common(n)))


def compare_documents(name_a: str, text_a: str, name_b: str, text_b: str) -> dict:
    summarizer = ExtractiveSummarizer()
    terms_a, terms_b = _top_terms(text_a), _top_terms(text_b)
    shared = [w for w, _ in (terms_a & terms_b).most_common(10)]
    only_a = [w for w, _ in (terms_a - terms_b).most_common(8)]
    only_b = [w for w, _ in (terms_b - terms_a).most_common(8)]

    def meta(text: str) -> dict:
        return {
            "words": len(_WORD.findall(text.lower())),
            "deadlines": extract_deadlines(text, limit=6),
        }

    va = re.search(r"[_\-\s]v(\d+)\b", name_a, re.IGNORECASE)
    vb = re.search(r"[_\-\s]v(\d+)\b", name_b, re.IGNORECASE)
    version_note = None
    if va and vb and va.group(1) != vb.group(1):
        newer = name_a if int(va.group(1)) > int(vb.group(1)) else name_b
        version_note = f"These look like versions of the same document — {newer} is newer."

    return {
        "a": {"name": name_a, "summary": summarizer.summarize(text_a, "short").to_dict(),
              "action_items": extract_action_items(text_a, limit=5), **meta(text_a)},
        "b": {"name": name_b, "summary": summarizer.summarize(text_b, "short").to_dict(),
              "action_items": extract_action_items(text_b, limit=5), **meta(text_b)},
        "shared_topics": shared,
        "only_in_a": only_a,
        "only_in_b": only_b,
        "version_note": version_note,
    }
