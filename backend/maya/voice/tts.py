"""Text-to-speech abstraction.

Playback in this prototype happens in the BROWSER via speechSynthesis: every
/api/chat response carries a ``speak`` string, and the frontend voices it with
the user's configured voice/rate (settings.yaml → voice). Nothing is synthesized
server-side.

The seam below allows a local engine (e.g. Piper) later: implement ``synthesize``
returning audio bytes and add a /api/voice/speak endpoint.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class TextToSpeech(ABC):
    name = "base"

    @abstractmethod
    def synthesize(self, text: str) -> bytes:
        ...


class BrowserTTS(TextToSpeech):
    """Marker implementation: synthesis happens client-side (speechSynthesis)."""

    name = "browser-speechsynthesis"

    def synthesize(self, text: str) -> bytes:
        raise NotImplementedError(
            "BrowserTTS is client-side; responses carry a 'speak' string instead."
        )


class MockTTS(TextToSpeech):
    """Test double: records what would have been spoken."""

    name = "mock"

    def __init__(self):
        self.spoken: list[str] = []

    def synthesize(self, text: str) -> bytes:
        self.spoken.append(text)
        return b""
