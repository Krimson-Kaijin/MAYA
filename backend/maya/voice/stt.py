"""Speech-to-text abstraction.

In this prototype, actual speech recognition runs in the BROWSER via the Web
Speech API (Chrome/Edge): audio never leaves the user's machine and never
reaches this backend — only the final text transcript is POSTed to /api/chat
with mode="voice". That is a deliberate privacy choice, not a shortcut.

The classes here define the seam for a future local engine (e.g. whisper.cpp):
implement ``transcribe`` and wire it into a /api/voice/transcribe endpoint.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class SpeechToText(ABC):
    name = "base"

    @abstractmethod
    def transcribe(self, audio_bytes: bytes, mime: str = "audio/webm") -> str:
        ...


class BrowserSTT(SpeechToText):
    """Marker implementation: recognition happens client-side (Web Speech API)."""

    name = "browser-webspeech"

    def transcribe(self, audio_bytes: bytes, mime: str = "audio/webm") -> str:
        raise NotImplementedError(
            "BrowserSTT is client-side; the backend only ever receives text transcripts."
        )


class MockSTT(SpeechToText):
    """Test double: returns a canned transcript."""

    name = "mock"

    def __init__(self, transcript: str = ""):
        self.transcript = transcript

    def transcribe(self, audio_bytes: bytes, mime: str = "audio/webm") -> str:
        return self.transcript
