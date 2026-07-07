"""File indexer — walks ONLY the approved folders from settings.yaml.

Per file: extract text → classify → for BLOCKED files store *metadata only*
(no text, ever) → for everything else store the *redacted* text. Raw sensitive
spans therefore never reach the index, and non-approved paths are never opened.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from ..policy.engine import PolicyEngine
from . import parsers

_VERSION_RE = re.compile(r"[_\-\s]v(\d+)\b", re.IGNORECASE)
_NAME_DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")


@dataclass
class IndexStats:
    indexed: int = 0
    blocked: int = 0
    skipped: int = 0

    def to_dict(self) -> dict:
        return {"indexed": self.indexed, "blocked": self.blocked, "skipped": self.skipped}


class FileIndexer:
    def __init__(self, config, db, policy: PolicyEngine, audit=None):
        self.config = config
        self.db = db
        self.policy = policy
        self.audit = audit

    def rebuild(self) -> IndexStats:
        stats = IndexStats()
        self.db.execute("DELETE FROM file_index")
        rows: list[tuple] = []
        now = datetime.now(timezone.utc).isoformat()

        for root in self.config.approved_folders:
            if not root.exists():
                continue
            for path in sorted(root.rglob("*")):
                if not path.is_file():
                    continue
                if path.suffix.lower() not in self.config.allowed_extensions:
                    continue
                if not self.policy.is_path_allowed(path):
                    stats.skipped += 1
                    continue
                try:
                    raw = parsers.extract_text(path, self.config.max_file_bytes)
                except Exception:
                    stats.skipped += 1
                    continue
                if raw is None:
                    stats.skipped += 1
                    continue

                prepared = self.policy.prepare_text(raw, subject=path.name)
                folder = str(path.parent.relative_to(root.parent)) if root.parent in path.parents else str(path.parent)
                vm = _VERSION_RE.search(path.stem)
                dm = _NAME_DATE_RE.search(path.stem)
                stat = path.stat()

                if not prepared.allowed:
                    stats.blocked += 1
                    text = ""  # BLOCKED: metadata only, content is never stored
                else:
                    stats.indexed += 1
                    text = prepared.text

                rows.append((
                    str(path), path.name, path.suffix.lower(), folder,
                    stat.st_mtime, stat.st_size,
                    prepared.level, ",".join(prepared.categories), text,
                    int(vm.group(1)) if vm else 0,
                    dm.group(1) if dm else "",
                    now,
                ))

        if rows:
            self.db.executemany(
                "INSERT OR REPLACE INTO file_index "
                "(path, name, ext, folder, mtime, size, sensitivity, categories, text, version, name_date, indexed_at) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                rows,
            )
        if self.audit:
            self.audit.log(
                "index.rebuild",
                detail=f"indexed={stats.indexed} blocked={stats.blocked} skipped={stats.skipped}",
            )
        return stats

    def get(self, path: str):
        return self.db.query_one("SELECT * FROM file_index WHERE path = ?", (path,))

    def count(self) -> int:
        row = self.db.query_one("SELECT COUNT(*) AS n FROM file_index")
        return int(row["n"]) if row else 0
