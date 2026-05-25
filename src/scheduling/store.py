"""Filesystem CRUD for CallSchedule objects.

One JSON file per senior: `data/seniors/<id>/schedule.json`.
"""

from __future__ import annotations

import json
from datetime import datetime
from datetime import timezone as _UTC
from pathlib import Path

from ..seniors.store import SENIORS_DIR
from .schedule import CallSchedule


class ScheduleStore:
    """Read/write per-senior call schedules."""

    def __init__(self, base_dir: Path = SENIORS_DIR):
        self.base_dir = base_dir

    def _path(self, senior_id: str) -> Path:
        return self.base_dir / senior_id / "schedule.json"

    def exists(self, senior_id: str) -> bool:
        return self._path(senior_id).exists()

    def load(self, senior_id: str) -> CallSchedule:
        path = self._path(senior_id)
        if not path.exists():
            raise FileNotFoundError(f"No schedule for {senior_id!r}. Use `schedule set` first.")
        return CallSchedule.from_json(json.loads(path.read_text(encoding="utf-8")))

    def save(self, schedule: CallSchedule) -> Path:
        path = self._path(schedule.senior_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(schedule.to_json(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return path

    def set(
        self,
        senior_id: str,
        call_time: str,
        timezone: str = "UTC",
        days_of_week: list[str] | None = None,
    ) -> CallSchedule:
        """Create or replace the schedule for `senior_id`."""
        now = datetime.now(tz=_UTC.utc).isoformat(timespec="seconds")
        if self.exists(senior_id):
            existing = self.load(senior_id)
            schedule = CallSchedule(
                senior_id=senior_id,
                call_time=call_time,
                timezone=timezone,
                days_of_week=days_of_week or existing.days_of_week,
                enabled=existing.enabled,
                created_at=existing.created_at,
                updated_at=now,
            )
        else:
            schedule = CallSchedule.new(
                senior_id=senior_id,
                call_time=call_time,
                timezone=timezone,
                days_of_week=days_of_week,
            )
        self.save(schedule)
        return schedule

    def remove(self, senior_id: str) -> bool:
        path = self._path(senior_id)
        if path.exists():
            path.unlink()
            return True
        return False

    def set_enabled(self, senior_id: str, enabled: bool) -> CallSchedule:
        schedule = self.load(senior_id)
        schedule.enabled = enabled
        schedule.updated_at = datetime.now(tz=_UTC.utc).isoformat(timespec="seconds")
        self.save(schedule)
        return schedule

    def list_all(self, only_enabled: bool = False) -> list[CallSchedule]:
        schedules: list[CallSchedule] = []
        for senior_dir in sorted(self.base_dir.iterdir()):
            if not senior_dir.is_dir():
                continue
            path = senior_dir / "schedule.json"
            if not path.exists():
                continue
            try:
                s = CallSchedule.from_json(json.loads(path.read_text(encoding="utf-8")))
            except Exception:  # noqa: BLE001
                continue
            if only_enabled and not s.enabled:
                continue
            schedules.append(s)
        return schedules

