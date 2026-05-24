"""Telephony module — bridges the Hermes call cycle with Twilio's PSTN.

Architecture:
- `config`         : env-var lookups for Twilio + public webhook URL.
- `tts`            : ElevenLabs synth → MP3 file under data/calls/<sid>/.
- `session`        : per-call JSON state on disk (history, audio paths, status).
- `twilio_client`  : thin wrapper over the Twilio REST SDK with dry-run mode.
- `server`         : FastAPI app exposing /twilio/start, /turn, /status, /audio/<sid>/<f>.
- `runner`         : initiates outbound calls + post-call Manager handoff.

Real Twilio integration is fully optional — `dry_run=True` lets the whole
pipeline be exercised locally without an account or a public URL.
"""

from .config import TelephonyConfig
from .session import CallState, CallStateStore
from .twilio_client import TwilioCallClient

__all__ = [
    "CallState",
    "CallStateStore",
    "TelephonyConfig",
    "TwilioCallClient",
]
