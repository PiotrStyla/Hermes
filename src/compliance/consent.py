"""Per-senior consent records (GDPR / RODO art. 6 + 7).

Stored at `data/seniors/<id>/consent.json`. The system MUST refuse to record,
transcribe or share data outside the scopes granted here.

This is intentionally simple — one consent record per senior, last-write-wins.
For audit history we rely on the append-only `AuditLog`.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Iterable

from ..seniors.store import SENIORS_DIR


class ConsentStatus(str, Enum):
    """Lifecycle of a senior's consent."""

    NONE = "none"          # never asked
    GRANTED = "granted"
    DECLINED = "declined"
    REVOKED = "revoked"    # was granted, senior later withdrew


# Granular scopes the senior can opt into independently.
#
# Note on Art. 9 RODO: `process_health_data` is a SEPARATE explicit consent —
# under RODO it cannot be lumped into a general "ok to talk" consent.
#
# Note on AI training: `train_on_transcripts` is also a separate consent — using
# a transcript to update operator skills counts as a different processing
# purpose than simply storing/sharing the same transcript with family.
SCOPE_RECORD_AUDIO = "record_audio"               # store raw audio
SCOPE_TRANSCRIBE = "transcribe"                   # send audio to STT provider
SCOPE_STORE_TRANSCRIPT = "store_transcript"       # keep text on disk
SCOPE_SHARE_WITH_FAMILY = "share_with_family"     # send reports to family contact
SCOPE_PROCESS_HEALTH_DATA = "process_health_data"  # Art. 9 RODO special category
SCOPE_TRAIN_ON_TRANSCRIPTS = "train_on_transcripts"  # use transcripts to update skills

DEFAULT_SCOPES = (SCOPE_TRANSCRIBE, SCOPE_STORE_TRANSCRIPT, SCOPE_SHARE_WITH_FAMILY)

ALL_SCOPES = (
    SCOPE_RECORD_AUDIO,
    SCOPE_TRANSCRIBE,
    SCOPE_STORE_TRANSCRIPT,
    SCOPE_SHARE_WITH_FAMILY,
    SCOPE_PROCESS_HEALTH_DATA,
    SCOPE_TRAIN_ON_TRANSCRIPTS,
)


@dataclass
class ConsentRecord:
    """Immutable snapshot of a senior's consent decision."""

    senior_id: str
    status: ConsentStatus
    scopes: list[str] = field(default_factory=list)
    granted_at: str | None = None      # ISO-8601 UTC
    revoked_at: str | None = None
    language: str = "en"
    method: str = "verbal"             # verbal | written | proxy
    witness: str | None = None         # e.g. family member name for proxy consent
    transcript: str | None = None      # verbatim of consent dialogue when verbal
    notes: str = ""

    def covers(self, scope: str) -> bool:
        return self.status == ConsentStatus.GRANTED and scope in self.scopes

    def to_json(self) -> dict:
        d = asdict(self)
        d["status"] = self.status.value
        return d

    @classmethod
    def from_json(cls, data: dict) -> "ConsentRecord":
        return cls(
            senior_id=data["senior_id"],
            status=ConsentStatus(data.get("status", "none")),
            scopes=list(data.get("scopes", [])),
            granted_at=data.get("granted_at"),
            revoked_at=data.get("revoked_at"),
            language=data.get("language", "en"),
            method=data.get("method", "verbal"),
            witness=data.get("witness"),
            transcript=data.get("transcript"),
            notes=data.get("notes", ""),
        )


class ConsentStore:
    """Filesystem CRUD for consent records (one JSON per senior)."""

    def __init__(self, base_dir: Path = SENIORS_DIR):
        self.base_dir = base_dir

    def path_for(self, senior_id: str) -> Path:
        return self.base_dir / senior_id / "consent.json"

    def load(self, senior_id: str) -> ConsentRecord:
        path = self.path_for(senior_id)
        if not path.exists():
            return ConsentRecord(senior_id=senior_id, status=ConsentStatus.NONE)
        return ConsentRecord.from_json(json.loads(path.read_text(encoding="utf-8")))

    def save(self, record: ConsentRecord) -> Path:
        path = self.path_for(record.senior_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(record.to_json(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return path

    def grant(
        self,
        senior_id: str,
        scopes: Iterable[str] = DEFAULT_SCOPES,
        language: str = "en",
        method: str = "verbal",
        witness: str | None = None,
        transcript: str | None = None,
        notes: str = "",
    ) -> ConsentRecord:
        record = ConsentRecord(
            senior_id=senior_id,
            status=ConsentStatus.GRANTED,
            scopes=list(scopes),
            granted_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            language=language,
            method=method,
            witness=witness,
            transcript=transcript,
            notes=notes,
        )
        self.save(record)
        return record

    def revoke(self, senior_id: str, notes: str = "") -> ConsentRecord:
        current = self.load(senior_id)
        record = ConsentRecord(
            senior_id=senior_id,
            status=ConsentStatus.REVOKED,
            scopes=[],
            granted_at=current.granted_at,
            revoked_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            language=current.language,
            method=current.method,
            witness=current.witness,
            transcript=current.transcript,
            notes=(current.notes + "\n" + notes).strip(),
        )
        self.save(record)
        return record

    def decline(self, senior_id: str, notes: str = "") -> ConsentRecord:
        record = ConsentRecord(
            senior_id=senior_id,
            status=ConsentStatus.DECLINED,
            scopes=[],
            notes=notes,
        )
        self.save(record)
        return record
