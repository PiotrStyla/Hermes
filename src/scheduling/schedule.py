"""CallSchedule dataclass — per-senior call schedule config."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import datetime
from datetime import timezone as _UTC
from typing import Any


DAYS_OF_WEEK = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
DAYS_FULL = {
    "mon": "Monday", "tue": "Tuesday", "wed": "Wednesday",
    "thu": "Thursday", "fri": "Friday", "sat": "Saturday", "sun": "Sunday",
}
_TIME_RE = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")


@dataclass
class CallSchedule:
    """Call schedule for one senior."""

    senior_id: str
    call_time: str            # "HH:MM" in the given timezone
    timezone: str             # Olson tz name, e.g. "Europe/Warsaw"
    days_of_week: list[str]   # subset of DAYS_OF_WEEK
    enabled: bool = True
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self) -> None:
        self._validate()

    def _validate(self) -> None:
        if not _TIME_RE.match(self.call_time):
            raise ValueError(
                f"call_time must be HH:MM (24h), got {self.call_time!r}."
            )
        invalid = [d for d in self.days_of_week if d not in DAYS_OF_WEEK]
        if invalid:
            raise ValueError(
                f"Unknown day(s): {invalid}. Use {list(DAYS_OF_WEEK)}."
            )
        if not self.days_of_week:
            raise ValueError("days_of_week must not be empty.")

    @property
    def hour(self) -> int:
        return int(self.call_time.split(":")[0])

    @property
    def minute(self) -> int:
        return int(self.call_time.split(":")[1])

    @property
    def apscheduler_day_of_week(self) -> str:
        """Return APScheduler cron `day_of_week` string, e.g. 'mon,tue,fri'."""
        return ",".join(self.days_of_week)

    def summary(self) -> str:
        days = ", ".join(DAYS_FULL[d] for d in self.days_of_week)
        status = "enabled" if self.enabled else "disabled"
        return (
            f"{self.senior_id}: {self.call_time} {self.timezone} "
            f"[{days}] ({status})"
        )

    def to_json(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "CallSchedule":
        return cls(
            senior_id=data["senior_id"],
            call_time=data["call_time"],
            timezone=data.get("timezone", "UTC"),
            days_of_week=list(data.get("days_of_week", ["mon", "tue", "wed", "thu", "fri"])),
            enabled=data.get("enabled", True),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
        )

    @classmethod
    def new(
        cls,
        senior_id: str,
        call_time: str,
        timezone: str = "UTC",
        days_of_week: list[str] | None = None,
    ) -> "CallSchedule":
        now = datetime.now(_UTC.utc).isoformat(timespec="seconds")
        return cls(
            senior_id=senior_id,
            call_time=call_time,
            timezone=timezone,
            days_of_week=days_of_week or list(DAYS_OF_WEEK[:5]),  # mon-fri default
            created_at=now,
            updated_at=now,
        )
