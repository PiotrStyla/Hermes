"""Per-call state for live Twilio sessions.

Each ongoing or completed call has a directory under `data/calls/<call_sid>/`:
  state.json       — the CallState (history, status, paths)
  tts/<n>.mp3      — synthesized operator audio (served to Twilio)
  rec/<n>.wav      — downloaded senior recordings (only kept if record_audio scope)

The state file is the source of truth for the call between webhook hits;
Twilio's webhooks are stateless on our side, so we round-trip CallSid → state.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..seniors.store import DATA_DIR


CALLS_DIR = DATA_DIR / "calls"


@dataclass
class CallState:
    """In-memory representation of one live or finished telephony session."""

    call_sid: str                    # Twilio's identifier (or our local id in simulate mode)
    senior_id: str
    status: str = "initiated"        # initiated|ringing|in_progress|completed|failed|voicemail
    started_at: str = ""
    ended_at: str | None = None
    end_reason: str | None = None    # natural_end|withdrawal|voicemail|max_turns|error
    voice_mode: bool = True
    history: list[dict[str, str]] = field(default_factory=list)  # [{role, content}]
    operator_system_prompt: str = ""
    record_audio_consent: bool = False
    health_consent: bool = False
    training_consent: bool = False
    twilio_recording_sids: list[str] = field(default_factory=list)
    tts_files: list[str] = field(default_factory=list)
    rec_files: list[str] = field(default_factory=list)
    turn_count: int = 0

    def to_json(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "CallState":
        return cls(**data)


class CallStateStore:
    """Filesystem CRUD for `CallState` objects."""

    def __init__(self, base_dir: Path = CALLS_DIR):
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    # ---- Paths ----

    def call_dir(self, call_sid: str) -> Path:
        d = self.base_dir / call_sid
        d.mkdir(parents=True, exist_ok=True)
        (d / "tts").mkdir(exist_ok=True)
        (d / "rec").mkdir(exist_ok=True)
        return d

    def state_path(self, call_sid: str) -> Path:
        return self.call_dir(call_sid) / "state.json"

    # ---- CRUD ----

    def exists(self, call_sid: str) -> bool:
        return self.state_path(call_sid).exists()

    def create(
        self,
        call_sid: str,
        senior_id: str,
        operator_system_prompt: str,
        record_audio_consent: bool,
        health_consent: bool,
        training_consent: bool,
        voice_mode: bool = True,
    ) -> CallState:
        state = CallState(
            call_sid=call_sid,
            senior_id=senior_id,
            started_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            voice_mode=voice_mode,
            operator_system_prompt=operator_system_prompt,
            record_audio_consent=record_audio_consent,
            health_consent=health_consent,
            training_consent=training_consent,
        )
        self.save(state)
        return state

    def load(self, call_sid: str) -> CallState:
        path = self.state_path(call_sid)
        if not path.exists():
            raise FileNotFoundError(f"No call state for sid={call_sid!r}")
        return CallState.from_json(json.loads(path.read_text(encoding="utf-8")))

    def save(self, state: CallState) -> None:
        self.state_path(state.call_sid).write_text(
            json.dumps(state.to_json(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def list(self, status: str | None = None) -> list[CallState]:
        out: list[CallState] = []
        for d in sorted(self.base_dir.iterdir()):
            if not d.is_dir():
                continue
            sp = d / "state.json"
            if not sp.exists():
                continue
            try:
                state = CallState.from_json(json.loads(sp.read_text(encoding="utf-8")))
            except Exception:  # noqa: BLE001
                continue
            if status and state.status != status:
                continue
            out.append(state)
        return out

    def mark_ended(self, state: CallState, reason: str, status: str = "completed") -> None:
        state.status = status
        state.end_reason = reason
        state.ended_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        self.save(state)
