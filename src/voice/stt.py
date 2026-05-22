"""Speech-to-Text via OpenAI Whisper API."""

from __future__ import annotations

import io
import os
import wave

import numpy as np
from openai import OpenAI


class WhisperSTT:
    """Transcribes recorded audio into text using OpenAI's Whisper API."""

    def __init__(self, api_key: str | None = None, model: str | None = None):
        api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "OPENAI_API_KEY not set. Add it to .env to use voice mode."
            )
        self.client = OpenAI(api_key=api_key)
        self.model = model or os.getenv("WHISPER_MODEL", "whisper-1")

    def transcribe(
        self,
        audio: np.ndarray,
        sample_rate: int,
        language: str | None = None,
    ) -> str:
        """Send a numpy int16 mono audio array to Whisper and return its text.

        `language` is the ISO-639-1 code (e.g., 'en', 'pl'). When omitted,
        Whisper auto-detects, but specifying it speeds things up and improves
        accuracy.
        """
        if audio.size == 0:
            return ""

        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)  # int16
            wav.setframerate(sample_rate)
            wav.writeframes(audio.tobytes())
        wav_buffer.seek(0)
        wav_buffer.name = "speech.wav"  # OpenAI client uses this for content-type

        kwargs: dict[str, object] = {"model": self.model, "file": wav_buffer}
        if language:
            kwargs["language"] = language

        result = self.client.audio.transcriptions.create(**kwargs)
        return (result.text or "").strip()
