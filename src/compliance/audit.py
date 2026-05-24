"""Append-only audit log.

One JSONL file per UTC day at `data/audit/YYYY-MM-DD.jsonl`. Each line is a
single event with at minimum: timestamp, actor, action, senior_id, details.

Append-only by convention — code in this module never opens existing files for
write/truncate. We don't checksum the chain yet; that's a later evolution.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..seniors.store import DATA_DIR


AUDIT_DIR = DATA_DIR / "audit"


class AuditLog:
    """Append-only event log used for compliance evidence."""

    def __init__(self, base_dir: Path = AUDIT_DIR):
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _path_for_today(self) -> Path:
        return self.base_dir / f"{datetime.now(timezone.utc):%Y-%m-%d}.jsonl"

    def record(
        self,
        action: str,
        actor: str,
        senior_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Append a single event to today's log file. Returns the event dict."""
        event = {
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "actor": actor,
            "action": action,
            "senior_id": senior_id,
            "details": details or {},
        }
        path = self._path_for_today()
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
        return event

    def list_files(self) -> list[Path]:
        return sorted(self.base_dir.glob("*.jsonl"))

    def tail(self, n: int = 20, senior_id: str | None = None) -> list[dict[str, Any]]:
        """Return the most recent `n` events across all files (optionally filtered)."""
        events: list[dict[str, Any]] = []
        for path in self.list_files():
            for line in path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                try:
                    ev = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if senior_id and ev.get("senior_id") != senior_id:
                    continue
                events.append(ev)
        return events[-n:]
