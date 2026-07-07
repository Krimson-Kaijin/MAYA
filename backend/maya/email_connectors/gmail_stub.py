"""Gmail connector stub — NOT CONFIGURED, and honest about it.

A real integration would use the official Gmail API with OAuth2:
  1. Create a Google Cloud project, enable the Gmail API.
  2. OAuth consent + credentials.json; request the narrowest scope:
     https://www.googleapis.com/auth/gmail.readonly
  3. Restrict queries to the labels in settings.yaml → email.approved_labels.
  4. Keep the policy pipeline unchanged: every message still passes through
     classify → shield/redact before anything downstream sees it.

This stub exists so the swap is config-only (email.provider: gmail); it refuses
to run without real credentials rather than pretending."""

from __future__ import annotations

from .base import ConnectorNotConfigured, Email, EmailConnector


class GmailConnector(EmailConnector):
    name = "gmail"
    status = "not_configured"
    status_note = "Gmail connector stub — requires OAuth credentials (see gmail_stub.py)"

    def __init__(self, config):
        self.config = config

    def list_messages(self, labels: list[str] | None = None) -> list[Email]:
        raise ConnectorNotConfigured(
            "The Gmail connector is a documented stub and has no credentials. "
            "Set email.provider back to 'mock' or implement OAuth per gmail_stub.py."
        )
