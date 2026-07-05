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
import re
import signal
import sys
import time

from rich.console import Console

from .store import ScheduleStore


log = logging.getLogger(__name__)
_TIME_RE = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")


def _call_senior(senior_id: str, console: Console) -> None:
    """Job entrypoint: run in the scheduler thread pool."""
    from ..agents.manager import ManagerAgent

    console.print(f"[cyan]>> Scheduled call: {senior_id}[/cyan]")
    try:
        result = ManagerAgent().run_call_cycle(
            senior_id,
            console=console,
            voice_mode=False,
        )
        report_path = result.get("report_path", "n/a")
        console.print(f"  -> report: {report_path}")
    except PermissionError as exc:
        console.print(f"[red]  -> blocked (consent): {exc}[/red]")
        log.warning("Scheduled call blocked for %s: %s", senior_id, exc)
    except Exception as exc:  # noqa: BLE001
        console.print(f"[red]  -> failed: {exc}[/red]")
        log.exception("Scheduled call failed for %s", senior_id)


def _run_board_meeting(console: Console) -> None:
    """Job entrypoint: run one executive board meeting (CEO/QD/HR → directive)."""
    from ..company import CompanyRunner

    console.print("[magenta]>> Scheduled board meeting[/magenta]")
    try:
        result = CompanyRunner(console=console).run_board_meeting(persist=True)
        d = result.directive
        if d is not None:
            console.print(
                f"  -> directive: focus {d.focus_metric} via '{d.focus_skill}'"
            )
    except Exception as exc:  # noqa: BLE001
        console.print(f"[red]  -> board meeting failed: {exc}[/red]")
        log.exception("Scheduled board meeting failed")


def _run_training(rounds: int, console: Console) -> None:
    """Job entrypoint: run a self-play training loop with N rounds."""
    from ..training import TrainingLoop

    console.print(f"[cyan]>> Scheduled training: {rounds} rounds[/cyan]")
    try:
        loop = TrainingLoop(rounds=rounds, console=console)
        report = loop.run()
        console.print(
            f"[green]  -> training complete: {report['rounds']} rounds, "
            f"{report['total_updates']} skill updates[/green]"
        )
    except Exception as exc:  # noqa: BLE001
        console.print(f"[red]  -> training failed: {exc}[/red]")
        log.exception("Scheduled training failed")


def _load_timezone(tz_name: str):
    """Return a tzinfo object, falling back to UTC on unknown zone."""
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo(tz_name)
    except Exception:
        log.warning("Unknown timezone %r, falling back to UTC.", tz_name)
        from datetime import timezone
        return timezone.utc


def _parse_time_hhmm(value: str) -> tuple[int, int]:
    match = _TIME_RE.match(value.strip())
    if match is None:
        raise ValueError(f"board_review_time must be HH:MM (24h), got {value!r}.")
    return int(match.group(1)), int(match.group(2))


def start_daemon(
    once: bool = False,
    dry_run: bool = False,
    board_review_hours: int = 0,
    board_review_time: str | None = None,
    board_review_timezone: str = "Europe/Warsaw",
    train_time: str | None = None,
    train_rounds: int = 0,
    train_timezone: str = "Europe/Warsaw",
    console: Console | None = None,
) -> None:
    """Start the APScheduler daemon.

    If `once=True`, run all enabled calls immediately and return — useful for
    debugging or as a cron job entry-point on a server where the OS scheduler
    (cron / Task Scheduler) fires the process at the right time.

    If `board_review_hours > 0`, run an executive board meeting every N hours.
    If `board_review_time` is set (HH:MM), run it daily at a fixed local time.
    If `train_time` is set (HH:MM) and `train_rounds > 0`, run a self-play
    training loop daily at that time with the given number of rounds.
    """
    if board_review_hours > 0 and board_review_time:
        raise ValueError("Use either board_review_hours OR board_review_time, not both.")

    board_fixed_time: tuple[int, int] | None = None
    if board_review_time:
        board_fixed_time = _parse_time_hhmm(board_review_time)

    board_enabled = board_review_hours > 0 or board_fixed_time is not None
    train_fixed_time: tuple[int, int] | None = None
    if train_time:
        train_fixed_time = _parse_time_hhmm(train_time)
    train_enabled = train_fixed_time is not None and train_rounds > 0

    log_console = console or Console()
    store = ScheduleStore()
    schedules = store.list_all(only_enabled=True)

    if not schedules and not board_enabled and not train_enabled:
        log_console.print("[yellow]No enabled schedules found. Use `schedule set` first, or enable board/training options.[/yellow]")
        return

    if once:
        if schedules:
            log_console.print(f"[bold]Running {len(schedules)} scheduled call(s) now (--once mode)[/bold]")
            for s in schedules:
                _call_senior(s.senior_id, log_console)
        if board_enabled:
            _run_board_meeting(log_console)
        if train_enabled:
            _run_training(train_rounds, log_console)
        return

    # Only the long-running daemon needs APScheduler.
    from apscheduler.schedulers.blocking import BlockingScheduler

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
            f"  [green]+[/green] Scheduled [bold]{s.senior_id}[/bold] "
            f"at {s.call_time} {s.timezone} [{s.apscheduler_day_of_week}]"
        )

    if board_review_hours > 0:
        from datetime import datetime, timedelta, timezone as dt_timezone

        first_run = datetime.now(dt_timezone.utc) + timedelta(minutes=1)
        scheduler.add_job(
            _run_board_meeting,
            trigger="interval",
            args=[log_console],
            hours=board_review_hours,
            next_run_time=first_run,
            id="board_meeting",
            name="Executive board meeting",
            misfire_grace_time=600,
            replace_existing=True,
        )
        log_console.print(
            f"  [green]+[/green] Scheduled [bold]board meeting[/bold] "
            f"every {board_review_hours}h (first run in ~1 min)"
        )

    if board_fixed_time is not None:
        board_hour, board_minute = board_fixed_time
        board_tz = _load_timezone(board_review_timezone)
        scheduler.add_job(
            _run_board_meeting,
            trigger="cron",
            args=[log_console],
            hour=board_hour,
            minute=board_minute,
            timezone=board_tz,
            id="board_meeting",
            name="Executive board meeting",
            misfire_grace_time=600,
            replace_existing=True,
        )
        log_console.print(
            f"  [green]+[/green] Scheduled [bold]board meeting[/bold] "
            f"daily at {board_review_time} {board_review_timezone}"
        )

    if train_enabled:
        train_hour, train_minute = train_fixed_time
        train_tz = _load_timezone(train_timezone)
        from datetime import datetime, timedelta, timezone as dt_timezone

        tomorrow = datetime.now(train_tz).date() + timedelta(days=1)
        start_date = datetime(
            tomorrow.year, tomorrow.month, tomorrow.day,
            train_hour, train_minute, tzinfo=train_tz,
        ).astimezone(dt_timezone.utc)
        scheduler.add_job(
            _run_training,
            trigger="cron",
            args=[train_rounds, log_console],
            hour=train_hour,
            minute=train_minute,
            timezone=train_tz,
            start_date=start_date,
            id="training",
            name=f"Self-play training ({train_rounds} rounds)",
            misfire_grace_time=600,
            replace_existing=True,
        )
        log_console.print(
            f"  [green]+[/green] Scheduled [bold]training[/bold] "
            f"daily at {train_time} {train_timezone} starting {tomorrow} "
            f"({train_rounds} rounds)"
        )

    n_jobs = len(schedules) + (1 if board_enabled else 0) + (1 if train_enabled else 0)
    log_console.print(
        f"\n[bold green]Hermes scheduler running - {n_jobs} job(s). "
        "Press Ctrl-C to stop.[/bold green]\n"
    )

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        log_console.print("\n[yellow]Scheduler stopped.[/yellow]")
        scheduler.shutdown(wait=False)
