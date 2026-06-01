"""ElevenLabs Text-to-Speech wrapper.

Streams PCM audio (16 kHz mono int16) from ElevenLabs and plays it through the
default output device with sounddevice. No ffmpeg / mpv dependency needed.
"""

from __future__ import annotations

import os

import numpy as np
import sounddevice as sd
from elevenlabs.client import ElevenLabs


SAMPLE_RATE = 16000  # must match output_format below


class ElevenLabsTTS:
    """Speaks text out loud through the default audio output device."""

    def __init__(
        self,
        api_key: str | None = None,
        voice_id: str | None = None,
        model_id: str | None = None,
    ):
        api_key = api_key or os.getenv("ELEVENLABS_API_KEY")
        if not api_key:
            raise RuntimeError(
                "ELEVENLABS_API_KEY not set. Add it to .env to use voice mode."
            )
        self.client = ElevenLabs(api_key=api_key)
        self.voice_id = voice_id or os.getenv(
            "ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM"
        )
        self.model_id = model_id or os.getenv(
            "ELEVENLABS_MODEL", "eleven_multilingual_v2"
        )

    def speak(self, text: str) -> None:
        """Synthesize and play `text`. Blocks until playback finishes."""
        if not text.strip():
            return

        audio_bytes = self._synthesize_raw(text)
        if not audio_bytes:
            return

        audio = np.frombuffer(audio_bytes, dtype=np.int16)
        sd.play(audio, samplerate=SAMPLE_RATE)
        sd.wait()

    def _synthesize_raw(self, text: str) -> bytes:
        """Return raw PCM 16 kHz int16 bytes (no playback)."""
        chunks = self.client.text_to_speech.convert(
            voice_id=self.voice_id,
            model_id=self.model_id,
            text=text,
            output_format="pcm_16000",
        )
        return b"".join(chunks)

    def stream_mulaw(self, text: str):
        """Generator yielding μ-law 8 kHz chunks for Twilio Media Streams."""
        from ..telephony.audio_codec import pcm_to_mulaw, resample_16k_to_8k

        raw = self._synthesize_raw(text)
        if not raw:
            return
        pcm = np.frombuffer(raw, dtype=np.int16)
        pcm_8k = resample_16k_to_8k(pcm)
        # Yield in ~20ms chunks (160 samples at 8 kHz)
        chunk_size = 160
        for i in range(0, len(pcm_8k), chunk_size):
            yield pcm_to_mulaw(pcm_8k[i:i + chunk_size])
