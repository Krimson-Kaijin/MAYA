"""MOCK email connector — reads fictional messages from
sample_data/emails/inbox.json. Clearly labelled as mock everywhere it surfaces
(status badge in the UI, source notes in digests). No real mailbox is touched."""

from __future__ import annotations

import json
from pathlib import Path

from .base import Email, EmailConnector


class MockEmailConnector(EmailConnector):
    name = "mock"
    status = "mock"
    status_note = "Mock inbox — fictional sample data (sample_data/emails/inbox.json)"

    def __init__(self, config, inbox_path: Path | None = None):
        self.config = config
        self.inbox_path = inbox_path or (config.root / "sample_data" / "emails" / "inbox.json")

    def list_messages(self, labels: list[str] | None = None) -> list[Email]:
        allowed = [l.lower() for l in (labels or self.config.approved_labels)]
        if not self.inbox_path.exists():
            return []
        data = json.loads(self.inbox_path.read_text(encoding="utf-8"))
        out = []
        for m in data.get("messages", []):
            if m.get("label", "INBOX").lower() not in allowed:
                continue  # least privilege: unapproved labels are invisible
            out.append(Email(
                id=m["id"], sender=m.get("from", ""), sender_name=m.get("from_name", ""),
                subject=m.get("subject", ""), date=m.get("date", ""),
                body=m.get("body", ""), label=m.get("label", "INBOX"),
            ))
        out.sort(key=lambda e: e.date, reverse=True)
        return out
