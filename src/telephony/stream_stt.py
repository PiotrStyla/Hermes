"""Streaming STT for Twilio Media Streams.

Uses Deepgram real-time API for sub-second transcription.
Falls back to batch Whisper when DEEPGRAM_API_KEY is not set.
"""

from __future__ import annotations

import asyncio
import json
import os
from typing import Callable

import numpy as np
import websockets


class StreamingSTT:
    """Real-time speech-to-text via Deepgram WebSocket."""

    def __init__(self, language: str = "en"):
        self.api_key = os.getenv("DEEPGRAM_API_KEY", "")
        self.language = language
        self._ws: websockets.WebSocketClientProtocol | None = None
        self._on_transcript: Callable[[str, bool], None] | None = None

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def connect(self, on_transcript: Callable[[str, bool], None]) -> None:
        """Open Deepgram WebSocket. `on_transcript(text, is_final)` called per result."""
        if not self.is_configured:
            return
        self._on_transcript = on_transcript
        url = f"wss://api.deepgram.com/v1/listen?encoding=mulaw&sample_rate=8000&language={self.language}&interim_results=true"
        self._ws = await websockets.connect(url, extra_headers={"Authorization": f"Token {self.api_key}"})
        asyncio.create_task(self._read_loop())

    async def send_audio(self, mulaw_chunk: bytes) -> None:
        if self._ws:
            await self._ws.send(mulaw_chunk)

    async def close(self) -> str:
        """Send close and return final transcript."""
        if self._ws:
            await self._ws.send(json.dumps({"type": "CloseStream"}))
            final = await self._ws.recv()
            await self._ws.close()
            self._ws = None
            try:
                data = json.loads(final)
                return data.get("channel", {}).get("alternatives", [{}])[0].get("transcript", "")
            except (json.JSONDecodeError, KeyError, IndexError):
                return ""
        return ""

    async def _read_loop(self) -> None:
        if not self._ws or not self._on_transcript:
            return
        try:
            async for msg in self._ws:
                try:
                    data = json.loads(msg)
                except json.JSONDecodeError:
                    continue
                alt = data.get("channel", {}).get("alternatives", [{}])[0]
                text = alt.get("transcript", "")
                is_final = data.get("is_final", False)
                if text:
                    self._on_transcript(text, is_final)
        except websockets.ConnectionClosed:
            pass


class BatchSTTFallback:
    """Buffer audio, transcribe with Whisper at end of turn."""

    def __init__(self, language: str = "en"):
        self.language = language
        self._buffer: list[bytes] = []

    def feed(self, mulaw_chunk: bytes) -> None:
        self._buffer.append(mulaw_chunk)

    def finalize(self) -> str:
        from .audio_codec import mulaw_to_pcm, resample_8k_to_16k
        from ..voice.stt import WhisperSTT

        if not self._buffer:
            return ""
        raw = b"".join(self._buffer)
        self._buffer.clear()
        pcm_8k = mulaw_to_pcm(raw)
        pcm_16k = resample_8k_to_16k(pcm_8k)
        try:
            stt = WhisperSTT()
            return stt.transcribe(pcm_16k, 16000, language=self.language if self.language != "en" else None)
        except Exception:
            return ""
