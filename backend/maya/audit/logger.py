"""Append-only audit log. Every access, classification block, memory write, and
action (executed or cancelled) lands here and is visible in the UI's Audit view.

The log records WHAT was touched (paths, message ids, categories) and never the
sensitive content itself."""

from __future__ import annotations

from datetime import datetime, timezone


class AuditLogger:
    def __init__(self, db):
        self.db = db

    def log(self, event: str, target: str = "", detail: str = "",
            sensitivity: str = "", outcome: str = "ok") -> None:
        self.db.execute(
            "INSERT INTO audit (ts, event, target, detail, sensitivity, outcome) "
            "VALUES (?,?,?,?,?,?)",
            (datetime.now(timezone.utc).isoformat(), event, target, detail,
             sensitivity, outcome),
        )

    def recent(self, limit: int = 100, event_prefix: str | None = None) -> list[dict]:
        if event_prefix:
            rows = self.db.query(
                "SELECT * FROM audit WHERE event LIKE ? ORDER BY id DESC LIMIT ?",
                (event_prefix + "%", limit),
            )
        else:
            rows = self.db.query("SELECT * FROM audit ORDER BY id DESC LIMIT ?", (limit,))
        return [dict(r) for r in rows]
