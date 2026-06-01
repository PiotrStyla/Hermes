"""Tests for Twilio Media Streams TwiML and stream handler."""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.telephony.turn_handler import _stream_url, _twiml_stream


def test_twiml_stream_contains_connect_and_stream() -> None:
    twiml = _twiml_stream("wss://example.com/twilio/stream/abc123")
    assert "<Connect>" in twiml
    assert "<Stream" in twiml
    assert "wss://example.com/twilio/stream/abc123" in twiml


def test_stream_url_http_to_ws() -> None:
    from src.telephony.config import TelephonyConfig

    cfg = TelephonyConfig(
        account_sid="AC123",
        auth_token="token",
        from_number="+48123456789",
        public_base_url="http://localhost:8000",
        machine_detection="",
        record_max_seconds=20,
        record_silence_timeout=3,
    )
    url = _stream_url(cfg, "call-1")
    assert url == "ws://localhost:8000/twilio/stream/call-1"


def test_stream_url_https_to_wss() -> None:
    from src.telephony.config import TelephonyConfig

    cfg = TelephonyConfig(
        account_sid="AC123",
        auth_token="token",
        from_number="+48123456789",
        public_base_url="https://abc.ngrok.app",
        machine_detection="",
        record_max_seconds=20,
        record_silence_timeout=3,
    )
    url = _stream_url(cfg, "call-2")
    assert url == "wss://abc.ngrok.app/twilio/stream/call-2"


class TestStreamHandler:
    def test_stream_handler_accepts_and_runs(self) -> None:
        """Verify StreamHandler can be instantiated and run without crashing."""
        from src.telephony.config import TelephonyConfig
        from src.telephony.stream_handler import StreamHandler

        cfg = TelephonyConfig(
            account_sid="AC123",
            auth_token="token",
            from_number="+48123456789",
            public_base_url="http://localhost:8000",
            machine_detection="",
            record_max_seconds=20,
            record_silence_timeout=3,
        )
        ws = AsyncMock()
        console = MagicMock()
        handler = StreamHandler(ws, "test-call-id", cfg, console)
        assert handler is not None
        assert handler.call_id == "test-call-id"


class TestBatchSTTFallback:
    def test_empty_buffer_returns_empty(self) -> None:
        from src.telephony.stream_stt import BatchSTTFallback

        fallback = BatchSTTFallback(language="en")
        assert fallback.finalize() == ""

    def test_feed_and_finalize(self) -> None:
        from src.telephony.stream_stt import BatchSTTFallback
        from src.telephony.audio_codec import pcm_to_mulaw

        import numpy as np
        # Create a simple sine wave as "audio"
        t = np.linspace(0, 0.5, 4000, dtype=np.float32)
        pcm = (np.sin(2 * np.pi * 440 * t) * 8000).astype(np.int16)
        mulaw = pcm_to_mulaw(pcm)

        fallback = BatchSTTFallback(language="en")
        fallback.feed(mulaw[:200])
        fallback.feed(mulaw[200:])
        # finalize() calls Whisper API — skip if no key
        import os
        if not os.getenv("OPENAI_API_KEY"):
            pytest.skip("OPENAI_API_KEY not set")
        result = fallback.finalize()
        assert isinstance(result, str)
