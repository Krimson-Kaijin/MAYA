"""Email connector abstraction. Connectors only ever expose messages from
approved labels; they never send anything themselves (drafts route through the
confirmation gate, and even a confirmed "send" in this prototype writes to a
local simulated outbox — see orchestrator/actions.py)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


class ConnectorNotConfigured(RuntimeError):
    pass


@dataclass
class Email:
    id: str
    sender: str
    sender_name: str
    subject: str
    date: str
    body: str
    label: str = "INBOX"

    def meta(self) -> dict:
        """Metadata only — safe to show even before classification."""
        return {"id": self.id, "sender_name": self.sender_name, "date": self.date,
                "label": self.label}


class EmailConnector(ABC):
    name: str = "base"
    status: str = "not_configured"   # mock | live | not_configured
    status_note: str = ""

    @abstractmethod
    def list_messages(self, labels: list[str] | None = None) -> list[Email]:
        ...
