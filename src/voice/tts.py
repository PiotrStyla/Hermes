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

        chunks = self.client.text_to_speech.convert(
            voice_id=self.voice_id,
            model_id=self.model_id,
            text=text,
            output_format="pcm_16000",
        )
        audio_bytes = b"".join(chunks)
        if not audio_bytes:
            return

        audio = np.frombuffer(audio_bytes, dtype=np.int16)
        sd.play(audio, samplerate=SAMPLE_RATE)
        sd.wait()
