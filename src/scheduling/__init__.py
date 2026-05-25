"""Scheduling module — autonomously dials seniors at their configured call time.

Per-senior config lives at `data/seniors/<id>/schedule.json`.
The daemon (`scheduler start`) uses APScheduler cron jobs — one per enabled
senior — and delegates to `telephony.runner.start_outbound_call`.
"""

from .schedule import CallSchedule, DAYS_OF_WEEK
from .store import ScheduleStore

__all__ = ["CallSchedule", "DAYS_OF_WEEK", "ScheduleStore"]
