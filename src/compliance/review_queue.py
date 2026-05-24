"""Human-in-the-loop review queue (EU AI Act high-risk requirement).

Wellness call AI that touches mental/physical health is likely a high-risk
system under the AI Act, which mandates meaningful human oversight. We
implement that here as a deterministic queue: after the Supervisor (LLM)
review, certain calls are flagged for a human reviewer BEFORE the family
report is considered final.

Default flagging rules:
- First N calls per senior (default 3) — onboarding period.
- Any Supervisor score below `QUALITY_THRESHOLD` (default 7).
- Any mid-call consent withdrawal event in this call.

Entries live at `data/review_queue/<entry_id>.json`. They never disappear:
approving / flagging mutates the status field but the entry stays as evidence.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..seniors.store import DATA_DIR


REVIEW_DIR = DATA_DIR / "review_queue"

# Number of initial calls per senior that automatically require human review.
ONBOARDING_REVIEW_CALLS = 3


@dataclass
class ReviewEntry:
    """One item awaiting (or already cleared by) human review."""

    id: str
    senior_id: str
    created_at: str
    transcript_path: str
    report_path: str
    scores: dict[str, Any]
    reasons: list[str]
    status: str = "pending"   # pending | approved | flagged
    decided_at: str | None = None
    decided_by: str | None = None
    comment: str = ""

    def to_json(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "ReviewEntry":
        return cls(
            id=data["id"],
            senior_id=data["senior_id"],
            created_at=data["created_at"],
            transcript_path=data["transcript_path"],
            report_path=data["report_path"],
            scores=dict(data.get("scores", {})),
            reasons=list(data.get("reasons", [])),
            status=data.get("status", "pending"),
            decided_at=data.get("decided_at"),
            decided_by=data.get("decided_by"),
            comment=data.get("comment", ""),
        )


class ReviewQueue:
    """Filesystem CRUD for human-review entries."""

    def __init__(self, base_dir: Path = REVIEW_DIR):
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    # ---- Decide whether this call needs review ----

    @staticmethod
    def needs_review(
        prior_call_count: int,
        scores: dict[str, Any],
        withdrew_consent: bool,
        quality_threshold: int = 7,
        onboarding_calls: int = ONBOARDING_REVIEW_CALLS,
    ) -> list[str]:
        """Return the list of reasons review is needed (empty = no review)."""
        reasons: list[str] = []
        if prior_call_count < onboarding_calls:
            reasons.append(f"onboarding_period (call #{prior_call_count + 1})")
        for axis, value in scores.items():
            try:
                if int(value) < quality_threshold:
                    reasons.append(f"low_score:{axis}={value}")
            except (TypeError, ValueError):
                continue
        if withdrew_consent:
            reasons.append("mid_call_consent_withdrawal")
        return reasons

    # ---- CRUD ----

    def enqueue(
        self,
        senior_id: str,
        transcript_path: Path,
        report_path: Path,
        scores: dict[str, Any],
        reasons: list[str],
    ) -> ReviewEntry:
        entry = ReviewEntry(
            id=uuid.uuid4().hex[:12],
            senior_id=senior_id,
            created_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            transcript_path=str(transcript_path),
            report_path=str(report_path),
            scores=dict(scores),
            reasons=list(reasons),
        )
        self._save(entry)
        return entry

    def list(self, status: str | None = None) -> list[ReviewEntry]:
        entries: list[ReviewEntry] = []
        for p in sorted(self.base_dir.glob("*.json")):
            try:
                entry = ReviewEntry.from_json(json.loads(p.read_text(encoding="utf-8")))
            except Exception:  # noqa: BLE001
                continue
            if status and entry.status != status:
                continue
            entries.append(entry)
        return entries

    def get(self, entry_id: str) -> ReviewEntry | None:
        path = self._path_for(entry_id)
        if not path.exists():
            return None
        return ReviewEntry.from_json(json.loads(path.read_text(encoding="utf-8")))

    def decide(
        self,
        entry_id: str,
        status: str,
        decided_by: str = "cli",
        comment: str = "",
    ) -> ReviewEntry:
        if status not in ("approved", "flagged"):
            raise ValueError(f"status must be 'approved' or 'flagged', got {status!r}")
        entry = self.get(entry_id)
        if entry is None:
            raise FileNotFoundError(f"Review entry {entry_id!r} not found.")
        entry.status = status
        entry.decided_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        entry.decided_by = decided_by
        entry.comment = comment
        self._save(entry)
        return entry

    # ---- Internal ----

    def _path_for(self, entry_id: str) -> Path:
        return self.base_dir / f"{entry_id}.json"

    def _save(self, entry: ReviewEntry) -> Path:
        path = self._path_for(entry.id)
        path.write_text(
            json.dumps(entry.to_json(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return path
