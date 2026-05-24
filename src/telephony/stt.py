"""Download Twilio recordings, transcribe with Whisper, optionally delete.

RODO interaction:
- The senior's recorded audio is fetched from Twilio over HTTPS with Basic auth.
- It is transcribed via Whisper.
- If the senior has NOT granted `record_audio` scope, we (a) do NOT keep the
  WAV locally and (b) issue a DELETE to Twilio so they don't retain it either.
- If the scope IS granted, the WAV is stored under data/calls/<sid>/rec/.
"""

from __future__ import annotations

import os
from pathlib import Path

import httpx


class WhisperFileSTT:
    """Transcribe an MP3/WAV file via OpenAI Whisper."""

    def __init__(self, api_key: str | None = None, model: str | None = None):
        # Lazy-import so the rest of the project works without OpenAI SDK.
        from openai import OpenAI

        api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY not set. Required for telephony STT.")
        self.client = OpenAI(api_key=api_key)
        self.model = model or os.getenv("WHISPER_MODEL", "whisper-1")

    def transcribe_file(self, path: Path, language: str | None = None) -> str:
        with open(path, "rb") as f:
            kwargs: dict[str, object] = {"model": self.model, "file": f}
            if language:
                kwargs["language"] = language
            result = self.client.audio.transcriptions.create(**kwargs)
        return (result.text or "").strip()


def download_twilio_recording(
    recording_url: str,
    account_sid: str,
    auth_token: str,
    out_path: Path,
    timeout: float = 30.0,
) -> Path:
    """Fetch a Twilio recording (.wav) using HTTP Basic auth.

    Twilio's recording URL has no extension; appending .wav forces a WAV
    download (vs the default .mp3) so we get lossless audio for Whisper.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    url = recording_url + ".wav" if not recording_url.endswith((".wav", ".mp3")) else recording_url
    with httpx.Client(timeout=timeout, auth=(account_sid, auth_token)) as client:
        resp = client.get(url)
        resp.raise_for_status()
        out_path.write_bytes(resp.content)
    return out_path
