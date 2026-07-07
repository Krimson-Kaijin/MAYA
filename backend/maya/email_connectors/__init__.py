from .base import ConnectorNotConfigured, Email, EmailConnector
from .mock_connector import MockEmailConnector
from .gmail_stub import GmailConnector
from .digest import build_digest

__all__ = [
    "Email", "EmailConnector", "ConnectorNotConfigured",
    "MockEmailConnector", "GmailConnector", "build_digest",
]


def get_connector(config):
    provider = config.get("email.provider", "mock")
    if provider == "gmail":
        return GmailConnector(config)
    return MockEmailConnector(config)
