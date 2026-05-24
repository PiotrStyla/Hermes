"""Synthesize Operator turns to MP3 files Twilio can <Play>."""

from __future__ import annotations

import os
from pathlib import Path


class TwilioTTS:
    """ElevenLabs synth → MP3 file on disk for `<Play>` by Twilio.

    Twilio accepts MP3 directly. We use 44.1 kHz mono MP3 for compatibility
    (Twilio resamples internally for the PSTN leg).
    """

    def __init__(
        self,
        api_key: str | None = None,
        voice_id: str | None = None,
        model_id: str | None = None,
    ):
        # Lazy-import so the rest of the project works without the ElevenLabs
        # SDK installed (e.g. running in dry-run mode in CI).
        from elevenlabs.client import ElevenLabs

        api_key = api_key or os.getenv("ELEVENLABS_API_KEY")
        if not api_key:
            raise RuntimeError(
                "ELEVENLABS_API_KEY not set. Required for telephony TTS."
            )
        self.client = ElevenLabs(api_key=api_key)
        self.voice_id = voice_id or os.getenv(
            "ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM"
        )
        self.model_id = model_id or os.getenv(
            "ELEVENLABS_MODEL", "eleven_multilingual_v2"
        )

    def synthesize_to_file(self, text: str, out_path: Path) -> Path:
        """Render `text` to an MP3 at `out_path`. Returns the path."""
        if not text.strip():
            raise ValueError("Cannot synthesize empty text.")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        chunks = self.client.text_to_speech.convert(
            voice_id=self.voice_id,
            model_id=self.model_id,
            text=text,
            output_format="mp3_44100_128",
        )
        with open(out_path, "wb") as f:
            for chunk in chunks:
                if chunk:
                    f.write(chunk)
        return out_path
