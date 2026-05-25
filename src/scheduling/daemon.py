"""APScheduler cron daemon — dials seniors at their scheduled time.

Each enabled senior with a `schedule.json` gets one cron job. Jobs are
re-synced from disk at startup. Changing a schedule (via CLI) requires a
daemon restart to take effect — acceptable for Phase 4.

Usage:
    python -m src scheduler start          # run until Ctrl-C
    python -m src scheduler start --once   # run all overdue calls now and exit
"""

from __future__ import annotations

import logging
import signal
import sys
import time

from rich.console import Console

from .store import ScheduleStore


log = logging.getLogger(__name__)


def _call_senior(senior_id: str, console: Console) -> None:
    """Job entrypoint: run in the scheduler thread pool."""
    from ..telephony.runner import start_outbound_call

    console.print(f"[cyan]⏰ Scheduled call: {senior_id}[/cyan]")
    try:
        result = start_outbound_call(senior_id, console=console)
        if result.get("dry_run"):
            console.print(f"[yellow]  ↳ dry-run (Twilio not configured)[/yellow]")
        else:
            console.print(f"  ↳ sid={result['twilio_call_sid']}")
    except PermissionError as exc:
        console.print(f"[red]  ↳ blocked (consent/phone): {exc}[/red]")
        log.warning("Scheduled call blocked for %s: %s", senior_id, exc)
    except Exception as exc:  # noqa: BLE001
        console.print(f"[red]  ↳ failed: {exc}[/red]")
        log.exception("Scheduled call failed for %s", senior_id)


def _load_timezone(tz_name: str):
    """Return a tzinfo object, falling back to UTC on unknown zone."""
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo(tz_name)
    except Exception:
        log.warning("Unknown timezone %r, falling back to UTC.", tz_name)
        from datetime import timezone
        return timezone.utc


def start_daemon(
    once: bool = False,
    dry_run: bool = False,
    console: Console | None = None,
) -> None:
    """Start the APScheduler daemon.

    If `once=True`, run all enabled calls immediately and return — useful for
    debugging or as a cron job entry-point on a server where the OS scheduler
    (cron / Task Scheduler) fires the process at the right time.
    """
    from apscheduler.schedulers.blocking import BlockingScheduler
    from apscheduler.schedulers.background import BackgroundScheduler

    log_console = console or Console()
    store = ScheduleStore()
    schedules = store.list_all(only_enabled=True)

    if not schedules:
        log_console.print("[yellow]No enabled call schedules found. Use `schedule set` first.[/yellow]")
        return

    if once:
        log_console.print(f"[bold]Running {len(schedules)} scheduled call(s) now (--once mode)[/bold]")
        for s in schedules:
            _call_senior(s.senior_id, log_console)
        return

    scheduler = BlockingScheduler(timezone="UTC")

    for s in schedules:
        tz = _load_timezone(s.timezone)
        scheduler.add_job(
            _call_senior,
            trigger="cron",
            args=[s.senior_id, log_console],
            day_of_week=s.apscheduler_day_of_week,
            hour=s.hour,
            minute=s.minute,
            timezone=tz,
            id=f"call_{s.senior_id}",
            name=f"Wellness call: {s.senior_id}",
            misfire_grace_time=300,  # 5 min grace if system was busy/asleep
            replace_existing=True,
        )
        log_console.print(
            f"  [green]✓[/green] Scheduled [bold]{s.senior_id}[/bold] "
            f"at {s.call_time} {s.timezone} [{s.apscheduler_day_of_week}]"
        )

    log_console.print(
        f"\n[bold green]Hermes scheduler running — {len(schedules)} job(s). "
        "Press Ctrl-C to stop.[/bold green]\n"
    )

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        log_console.print("\n[yellow]Scheduler stopped.[/yellow]")
        scheduler.shutdown(wait=False)
