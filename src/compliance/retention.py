"""Per-senior data retention policy (GDPR / RODO art. 5(1)(e)).

Stored at `data/seniors/<id>/retention.json`. The `purge` command scans the
filesystem and deletes artifacts older than the configured TTL.

Defaults are conservative for an MVP that keeps no audio at all:
    audio_days       = 0   (we don't store raw audio yet anyway)
    transcript_days  = 30
    report_days      = 180
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from ..seniors.store import SENIORS_DIR


@dataclass
class RetentionPolicy:
    """How long each artifact type is kept before automatic deletion."""

    senior_id: str
    audio_days: int = 0
    transcript_days: int = 30
    report_days: int = 180

    def ttl_for(self, kind: str) -> int:
        return {
            "audio": self.audio_days,
            "transcripts": self.transcript_days,
            "reports": self.report_days,
        }.get(kind, 0)

    def to_json(self) -> dict:
        return asdict(self)

    @classmethod
    def from_json(cls, data: dict) -> "RetentionPolicy":
        return cls(
            senior_id=data["senior_id"],
            audio_days=int(data.get("audio_days", 0)),
            transcript_days=int(data.get("transcript_days", 30)),
            report_days=int(data.get("report_days", 180)),
        )


class RetentionStore:
    """Filesystem CRUD + purge logic for retention policies."""

    def __init__(self, base_dir: Path = SENIORS_DIR):
        self.base_dir = base_dir

    def path_for(self, senior_id: str) -> Path:
        return self.base_dir / senior_id / "retention.json"

    def load(self, senior_id: str) -> RetentionPolicy:
        path = self.path_for(senior_id)
        if not path.exists():
            return RetentionPolicy(senior_id=senior_id)
        return RetentionPolicy.from_json(json.loads(path.read_text(encoding="utf-8")))

    def save(self, policy: RetentionPolicy) -> Path:
        path = self.path_for(policy.senior_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(policy.to_json(), indent=2),
            encoding="utf-8",
        )
        return path

    # ---- Purge ----

    def purge(self, senior_id: str, dry_run: bool = True) -> list[Path]:
        """Delete files older than this senior's retention policy.

        Returns the list of paths that were (or would be) deleted.
        """
        policy = self.load(senior_id)
        now = datetime.now(timezone.utc)
        deleted: list[Path] = []

        for kind in ("transcripts", "reports", "audio"):
            ttl = policy.ttl_for(kind)
            d = self.base_dir / senior_id / kind
            if not d.exists():
                continue
            cutoff = now - timedelta(days=ttl)
            for p in d.iterdir():
                if not p.is_file():
                    continue
                mtime = datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc)
                if mtime < cutoff:
                    deleted.append(p)
                    if not dry_run:
                        p.unlink()
        return deleted

    def forget(self, senior_id: str, dry_run: bool = True) -> list[Path]:
        """Hard delete: remove ALL personal data for this senior.

        Keeps the senior directory in place but empties profile/persona/transcripts/
        reports/learnings/consent/retention. The append-only audit log is NOT
        touched here (that record exists for legal defence); see `AuditLog.forget`
        if you need to scrub it separately.
        """
        from .consent import SENIORS_DIR as _SENIORS_DIR  # noqa: F401

        targets: list[Path] = []
        senior_dir = self.base_dir / senior_id
        if senior_dir.exists():
            for p in senior_dir.rglob("*"):
                if p.is_file():
                    targets.append(p)

        # Also wipe the persona file if present.
        persona = self.base_dir.parent / "personas" / f"{senior_id}.md"
        if persona.exists():
            targets.append(persona)

        if not dry_run:
            for p in targets:
                p.unlink()
        return targets
