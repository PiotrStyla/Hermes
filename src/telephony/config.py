"""Environment-driven config for the telephony layer.

We never hard-code anything sensitive. Real Twilio credentials live in `.env`
(which is gitignored). For local dev / demos, `dry_run=True` skips the SDK
entirely and prints the would-be call payload.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class TelephonyConfig:
    """Snapshot of telephony env vars."""

    account_sid: str
    auth_token: str
    from_number: str           # our purchased Twilio number, E.164
    public_base_url: str       # e.g. https://abc123.ngrok.app  (no trailing slash)
    machine_detection: str     # "DetectMessageEnd" | "Enable" | ""  (off)
    record_max_seconds: int    # safety cap on Twilio <Record>
    record_silence_timeout: int  # seconds of silence to stop recording

    @classmethod
    def from_env(cls) -> "TelephonyConfig":
        return cls(
            account_sid=os.getenv("TWILIO_ACCOUNT_SID", ""),
            auth_token=os.getenv("TWILIO_AUTH_TOKEN", ""),
            from_number=os.getenv("TWILIO_FROM_NUMBER", ""),
            public_base_url=os.getenv("TELEPHONY_PUBLIC_URL", "").rstrip("/"),
            machine_detection=os.getenv("TWILIO_MACHINE_DETECTION", "DetectMessageEnd"),
            record_max_seconds=int(os.getenv("TWILIO_RECORD_MAX_SECONDS", "20")),
            record_silence_timeout=int(os.getenv("TWILIO_RECORD_SILENCE_SECONDS", "3")),
        )

    def is_configured(self) -> bool:
        return bool(self.account_sid and self.auth_token and self.from_number)

    def missing_keys(self) -> list[str]:
        missing = []
        if not self.account_sid:
            missing.append("TWILIO_ACCOUNT_SID")
        if not self.auth_token:
            missing.append("TWILIO_AUTH_TOKEN")
        if not self.from_number:
            missing.append("TWILIO_FROM_NUMBER")
        if not self.public_base_url:
            missing.append("TELEPHONY_PUBLIC_URL")
        return missing
