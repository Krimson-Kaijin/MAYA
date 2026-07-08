"""Keyword search over the file index, with type/folder/date filters.

Ranking: filename hits weigh most, then term frequency in (already redacted)
text, an all-terms bonus, and a freshness key so "latest" queries can prefer
newer versions (mtime → _vN in the name → date in the name).
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

_STOPWORDS = {
    "the", "a", "an", "of", "in", "on", "for", "to", "and", "or", "is", "are",
    "my", "me", "our", "this", "that", "with", "from", "file", "files",
    "document", "documents", "doc", "docs", "latest", "newest", "recent",
    "find", "search", "locate", "show", "please",
}


@dataclass
class SearchHit:
    path: str
    name: str
    ext: str
    folder: str
    mtime: float
    size: int
    sensitivity: str
    categories: list[str]
    score: float
    snippet: str
    shielded: bool = False

    def to_dict(self) -> dict:
        return {
            "path": self.path, "name": self.name, "ext": self.ext,
            "folder": self.folder, "mtime": self.mtime, "size": self.size,
            "sensitivity": self.sensitivity, "categories": self.categories,
            "score": round(self.score, 2), "snippet": self.snippet,
            "shielded": self.shielded,
        }


def tokenize(query: str) -> list[str]:
    terms = re.findall(r"[a-z0-9]+", (query or "").lower())
    return [t for t in terms if t not in _STOPWORDS and len(t) > 1]


def search_index(
    db,
    query: str,
    *,
    ftype: str | None = None,
    folder: str | None = None,
    after: float | None = None,
    before: float | None = None,
    latest: bool = False,
    limit: int = 8,
) -> list[SearchHit]:
    terms = tokenize(query)
    rows = db.query("SELECT * FROM file_index")
    hits: list[SearchHit] = []

    for row in rows:
        if ftype and row["ext"].lstrip(".") != ftype.lstrip(".").lower():
            continue
        if folder and folder.lower() not in row["folder"].lower():
            continue
        if after and row["mtime"] < after:
            continue
        if before and row["mtime"] > before:
            continue

        name_l = row["name"].lower()
        text_l = (row["text"] or "").lower()
        shielded = row["sensitivity"] == "BLOCKED"

        score, matched = 0.0, 0
        for t in terms:
            n = name_l.count(t)
            # Blocked files: match on NAME only — their content is not in the index.
            c = 0 if shielded else text_l.count(t)
            if n or c:
                matched += 1
                score += 3.0 * n + math.log1p(c)
        if terms and matched == 0:
            continue
        if terms and matched == len(terms):
            score += 2.0
        if not terms:
            score = 1.0  # browse mode: filters only

        if latest:
            score += _freshness(row)

        snippet = "" if shielded else _snippet(row["text"] or "", terms)
        hits.append(SearchHit(
            path=row["path"], name=row["name"], ext=row["ext"], folder=row["folder"],
            mtime=row["mtime"], size=row["size"], sensitivity=row["sensitivity"],
            categories=[c for c in (row["categories"] or "").split(",") if c],
            score=score, snippet=snippet, shielded=shielded,
        ))

    hits.sort(key=lambda h: (-h.score, -h.mtime, h.name))
    return hits[:limit]


def _freshness(row) -> float:
    bonus = row["version"] * 1.5
    if row["name_date"]:
        bonus += 1.0
    return bonus


def _snippet(text: str, terms: list[str], width: int = 220) -> str:
    if not text:
        return ""
    flat = re.sub(r"\s+", " ", text).strip()
    if not terms:
        return flat[:width]
    lower = flat.lower()
    pos = min((lower.find(t) for t in terms if lower.find(t) >= 0), default=0)
    start = max(0, pos - 60)
    clip = flat[start:start + width]
    return ("…" if start > 0 else "") + clip + ("…" if start + width < len(flat) else "")
