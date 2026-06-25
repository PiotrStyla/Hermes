"""Command-line interface for the Hermes Elderly Care system."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Force UTF-8 stdout/stderr so Rich console output does not crash on Windows
# with legacy code pages (cp1250) when emitting non-ASCII characters.
if sys.stdout.isatty() is False:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass

from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

from .agents.manager import ManagerAgent
from .compliance import (
    AuditLog,
    ConsentStore,
    RetentionStore,
    ReviewQueue,
)
from .compliance.consent import DEFAULT_SCOPES
from .scheduling.store import ScheduleStore
from .scheduling.schedule import DAYS_OF_WEEK
from .seniors.store import SeniorStore
from .skills.loader import SkillsLoader


# Load .env from project root.
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

console = Console()


def cmd_call(args: argparse.Namespace) -> int:
    manager = ManagerAgent()
    try:
        result = manager.run_call_cycle(
            args.senior_id,
            console=console,
            voice_mode=args.voice,
            allow_no_consent=args.allow_no_consent,
        )
    except FileNotFoundError as e:
        console.print(f"[red]{e}[/red]")
        return 1
    except RuntimeError as e:
        console.print(f"[red]{e}[/red]")
        return 1

    console.rule("[bold green]Call cycle complete[/bold green]")
    console.print(f"Transcript: {result['transcript_path']}")
    console.print(f"Report:     {result['report_path']}")
    if result["skill_updates_applied"]:
        console.print(f"Skills updated: {', '.join(result['skill_updates_applied'])}")
    return 0


def cmd_list_seniors(_: argparse.Namespace) -> int:
    store = SeniorStore()
    ids = store.list_ids()
    if not ids:
        console.print("[yellow]No seniors found in data/seniors/[/yellow]")
        return 0

    table = Table(title="Seniors")
    table.add_column("ID")
    table.add_column("Name")
    table.add_column("Age")
    table.add_column("Calls")
    table.add_column("Reports")
    for sid in ids:
        try:
            p = store.load(sid)
            transcripts = len(store.list_transcripts(sid))
            reports = len(store.list_reports(sid))
            table.add_row(p.id, p.name, str(p.age), str(transcripts), str(reports))
        except Exception as e:  # noqa: BLE001
            table.add_row(sid, f"[red]error: {e}[/red]", "-", "-", "-")
    console.print(table)
    return 0


def cmd_view_history(args: argparse.Namespace) -> int:
    store = SeniorStore()
    if not store.exists(args.senior_id):
        console.print(f"[red]Senior {args.senior_id!r} not found[/red]")
        return 1

    transcripts = store.list_transcripts(args.senior_id)
    reports = store.list_reports(args.senior_id)

    console.print(f"[bold]Transcripts ({len(transcripts)}):[/bold]")
    for t in transcripts:
        console.print(f"  {t.name}")
    console.print(f"[bold]Reports ({len(reports)}):[/bold]")
    for r in reports:
        console.print(f"  {r.name}")
    return 0


def cmd_view_skills(_: argparse.Namespace) -> int:
    loader = SkillsLoader()
    skills = loader.load_all()
    if not skills:
        console.print("[yellow]No skills found[/yellow]")
        return 0
    table = Table(title="Operator Skills")
    table.add_column("Skill")
    table.add_column("Bytes")
    for name, content in skills.items():
        table.add_row(name, str(len(content)))
    console.print(table)
    return 0


# ---- Compliance commands ----


def cmd_consent_show(args: argparse.Namespace) -> int:
    record = ConsentStore().load(args.senior_id)
    console.print(f"[bold]Consent for {args.senior_id}[/bold]")
    console.print(f"  status:     {record.status.value}")
    console.print(f"  scopes:     {record.scopes or '(none)'}")
    console.print(f"  granted_at: {record.granted_at}")
    console.print(f"  revoked_at: {record.revoked_at}")
    console.print(f"  language:   {record.language}")
    console.print(f"  method:     {record.method}")
    if record.witness:
        console.print(f"  witness:    {record.witness}")
    if record.notes:
        console.print(f"  notes:      {record.notes}")
    return 0


def cmd_consent_grant(args: argparse.Namespace) -> int:
    store = SeniorStore()
    if not store.exists(args.senior_id):
        console.print(f"[red]Senior {args.senior_id!r} not found[/red]")
        return 1
    profile = store.load(args.senior_id)
    scopes = args.scope or list(DEFAULT_SCOPES)
    record = ConsentStore().grant(
        senior_id=args.senior_id,
        scopes=scopes,
        language=profile.language,
        method=args.method,
        witness=args.witness,
        notes=args.notes or "",
    )
    AuditLog().record(
        "consent_granted",
        actor="cli",
        senior_id=args.senior_id,
        details={"scopes": scopes, "method": args.method, "witness": args.witness},
    )
    console.print(f"[green]Consent granted for {args.senior_id}[/green] — scopes: {record.scopes}")
    return 0


def cmd_consent_revoke(args: argparse.Namespace) -> int:
    record = ConsentStore().revoke(args.senior_id, notes=args.notes or "")
    AuditLog().record(
        "consent_revoked",
        actor="cli",
        senior_id=args.senior_id,
        details={"notes": args.notes or ""},
    )
    console.print(f"[yellow]Consent revoked for {args.senior_id} at {record.revoked_at}[/yellow]")
    return 0


def cmd_purge(args: argparse.Namespace) -> int:
    rstore = RetentionStore()
    store = SeniorStore()
    ids = [args.senior_id] if args.senior_id else store.list_ids()
    total: list[Path] = []
    for sid in ids:
        deleted = rstore.purge(sid, dry_run=args.dry_run)
        for p in deleted:
            console.print(f"  {'[would delete]' if args.dry_run else '[deleted]'} {p}")
        total.extend(deleted)
    AuditLog().record(
        "purge_run",
        actor="cli",
        senior_id=args.senior_id,
        details={"dry_run": args.dry_run, "count": len(total)},
    )
    verb = "Would delete" if args.dry_run else "Deleted"
    console.print(f"[bold]{verb} {len(total)} file(s).[/bold]")
    return 0


def cmd_forget(args: argparse.Namespace) -> int:
    if not args.yes and not args.dry_run:
        console.print(
            f"[red]This will hard-delete ALL data for {args.senior_id}.[/red] "
            f"Re-run with --yes to confirm, or --dry-run to preview."
        )
        return 1
    targets = RetentionStore().forget(args.senior_id, dry_run=args.dry_run)
    for p in targets:
        console.print(f"  {'[would delete]' if args.dry_run else '[deleted]'} {p}")
    AuditLog().record(
        "right_to_erasure",
        actor="cli",
        senior_id=args.senior_id,
        details={"dry_run": args.dry_run, "count": len(targets)},
    )
    verb = "Would delete" if args.dry_run else "Deleted"
    console.print(f"[bold]{verb} {len(targets)} file(s) for {args.senior_id}.[/bold]")
    return 0


def cmd_audit_tail(args: argparse.Namespace) -> int:
    events = AuditLog().tail(n=args.n, senior_id=args.senior_id)
    if not events:
        console.print("[yellow]No audit events found.[/yellow]")
        return 0
    for ev in events:
        sid = ev.get("senior_id") or "-"
        console.print(
            f"[dim]{ev['ts']}[/dim] [cyan]{ev['actor']}[/cyan] "
            f"[bold]{ev['action']}[/bold] [magenta]{sid}[/magenta] {ev.get('details', {})}"
        )
    return 0


def cmd_compliance_review(args: argparse.Namespace) -> int:
    from .compliance import ComplianceReviewerAgent

    path = Path(args.file)
    if not path.exists():
        console.print(f"[red]File not found: {path}[/red]")
        return 1
    content = path.read_text(encoding="utf-8")
    reviewer = ComplianceReviewerAgent()
    result = reviewer.review_artifact(
        kind=args.kind,
        content=content,
        context=args.context or "",
    )
    verdict = result.get("verdict", "?")
    color = {"ok": "green", "warn": "yellow", "block": "red"}.get(verdict, "white")
    console.print(f"[bold {color}]Verdict: {verdict}[/bold {color}] — {result.get('summary', '')}")
    sev_color = {"high": "red", "med": "yellow", "low": "blue"}
    for c in result.get("concerns", []):
        sev = c.get("severity", "?")
        col = sev_color.get(sev, "white")
        console.print(
            f"  [{col}][{sev}] {c.get('rule')}[/{col}]: {c.get('explanation')}\n"
            f"     → {c.get('suggestion')}"
        )
    AuditLog().record(
        "compliance_review",
        actor="cli",
        senior_id=None,
        details={"file": str(path), "kind": args.kind, "verdict": verdict},
    )
    return 0


# ---- Review queue commands ----


def cmd_review_list(args: argparse.Namespace) -> int:
    entries = ReviewQueue().list(status=args.status)
    if not entries:
        console.print("[yellow]Review queue is empty.[/yellow]")
        return 0
    table = Table(title="Human review queue")
    table.add_column("ID")
    table.add_column("Created")
    table.add_column("Senior")
    table.add_column("Status")
    table.add_column("Reasons")
    for e in entries:
        table.add_row(
            e.id, e.created_at, e.senior_id, e.status, "; ".join(e.reasons),
        )
    console.print(table)
    return 0


def cmd_review_show(args: argparse.Namespace) -> int:
    entry = ReviewQueue().get(args.entry_id)
    if entry is None:
        console.print(f"[red]Entry {args.entry_id!r} not found[/red]")
        return 1
    console.print(f"[bold]Entry {entry.id}[/bold]")
    console.print(f"  senior:       {entry.senior_id}")
    console.print(f"  created_at:   {entry.created_at}")
    console.print(f"  status:       {entry.status}")
    console.print(f"  reasons:      {entry.reasons}")
    console.print(f"  scores:       {entry.scores}")
    console.print(f"  transcript:   {entry.transcript_path}")
    console.print(f"  report:       {entry.report_path}")
    if entry.decided_at:
        console.print(f"  decided_at:   {entry.decided_at}")
        console.print(f"  decided_by:   {entry.decided_by}")
    if entry.comment:
        console.print(f"  comment:      {entry.comment}")
    return 0


def _decide(args: argparse.Namespace, status: str) -> int:
    try:
        entry = ReviewQueue().decide(
            args.entry_id,
            status=status,
            decided_by=args.by or "cli",
            comment=args.comment or "",
        )
    except FileNotFoundError as e:
        console.print(f"[red]{e}[/red]")
        return 1
    AuditLog().record(
        f"review_{status}",
        actor="cli",
        senior_id=entry.senior_id,
        details={"entry_id": entry.id, "comment": entry.comment},
    )
    color = "green" if status == "approved" else "yellow"
    console.print(f"[{color}]Entry {entry.id} marked as {status}.[/{color}]")
    return 0


def cmd_review_approve(args: argparse.Namespace) -> int:
    return _decide(args, "approved")


def cmd_review_flag(args: argparse.Namespace) -> int:
    return _decide(args, "flagged")


# ---- Scheduling commands (Phase 4) ----


def cmd_schedule_set(args: argparse.Namespace) -> int:
    days = [d.strip() for d in args.days.split(",")] if args.days else None
    try:
        s = ScheduleStore().set(
            args.senior_id,
            call_time=args.time,
            timezone=args.timezone,
            days_of_week=days,
        )
    except (ValueError, FileNotFoundError) as e:
        console.print(f"[red]{e}[/red]")
        return 1
    console.print(f"[green]Schedule saved:[/green] {s.summary()}")
    return 0


def cmd_schedule_list(args: argparse.Namespace) -> int:
    schedules = ScheduleStore().list_all()
    if not schedules:
        console.print("[yellow]No call schedules configured.[/yellow]")
        return 0
    table = Table(title="Call schedules")
    table.add_column("Senior ID")
    table.add_column("Time")
    table.add_column("Timezone")
    table.add_column("Days")
    table.add_column("Enabled")
    for s in schedules:
        table.add_row(
            s.senior_id, s.call_time, s.timezone,
            s.apscheduler_day_of_week,
            "[green]yes[/green]" if s.enabled else "[red]no[/red]",
        )
    console.print(table)
    return 0


def cmd_schedule_remove(args: argparse.Namespace) -> int:
    removed = ScheduleStore().remove(args.senior_id)
    if removed:
        console.print(f"[green]Schedule removed for {args.senior_id}.[/green]")
    else:
        console.print(f"[yellow]No schedule found for {args.senior_id}.[/yellow]")
    return 0


def _toggle_schedule(senior_id: str, enabled: bool) -> int:
    try:
        s = ScheduleStore().set_enabled(senior_id, enabled)
    except FileNotFoundError as e:
        console.print(f"[red]{e}[/red]")
        return 1
    state = "[green]enabled[/green]" if enabled else "[yellow]disabled[/yellow]"
    console.print(f"Schedule for {senior_id} is now {state}.")
    return 0


def cmd_schedule_enable(args: argparse.Namespace) -> int:
    return _toggle_schedule(args.senior_id, True)


def cmd_schedule_disable(args: argparse.Namespace) -> int:
    return _toggle_schedule(args.senior_id, False)


def cmd_scheduler_start(args: argparse.Namespace) -> int:
    from .scheduling.daemon import start_daemon
    start_daemon(
        once=args.once,
        board_review_hours=args.board_review_hours,
        board_review_time=args.board_review_time,
        board_review_timezone=args.board_review_timezone,
        console=console,
    )
    return 0


# ---- Onboarding wizard ----


def cmd_onboard(args: argparse.Namespace) -> int:
    """Interactive wizard that guides through setting up a new senior."""
    from rich.prompt import Confirm, Prompt

    from .compliance.consent import DEFAULT_SCOPES, SCOPE_PROCESS_HEALTH_DATA, SCOPE_TRAIN_ON_TRANSCRIPTS
    from .notifications.email import EmailSender
    from .seniors.store import SeniorProfile

    console.rule("[bold]Hermes Onboarding Wizard[/bold]")
    console.print("This wizard sets up a new senior and verifies your configuration.\n")

    # ---- 1. Senior profile ----
    console.rule("Step 1: Senior profile")
    name = Prompt.ask("Full name")
    senior_id = name.lower().replace(" ", "-")
    age_str = Prompt.ask("Age", default="75")
    try:
        age = int(age_str)
    except ValueError:
        console.print("[red]Invalid age — must be a number.[/red]")
        return 1
    language = Prompt.ask("Language", default="pl", choices=["pl", "en", "de", "fr", "es"])
    conditions_str = Prompt.ask("Medical conditions (comma-separated, or leave blank)", default="")
    medications_str = Prompt.ask("Medications (comma-separated, or leave blank)", default="")
    phone = Prompt.ask("Phone number E.164 e.g. +48123456789 (or leave blank)", default="")
    fam_name = Prompt.ask("Family contact name")
    fam_email = Prompt.ask("Family contact email")

    store = SeniorStore()
    if store.exists(senior_id):
        from rich.prompt import Confirm as _C
        if not _C.ask(f"[yellow]Senior {senior_id!r} already exists. Overwrite?[/yellow]"):
            console.print("Aborted.")
            return 1

    profile = SeniorProfile(
        id=senior_id,
        name=name,
        age=age,
        language=language,
        conditions=[c.strip() for c in conditions_str.split(",") if c.strip()],
        medications=[m.strip() for m in medications_str.split(",") if m.strip()],
        preferences={"tone": "warm and friendly"},
        family_contact={"name": fam_name, "email": fam_email},
        notes="",
        phone_number=phone,
    )
    store.save_profile(profile)
    console.print(f"[green]✓ Profile saved:[/green] {senior_id}")

    # ---- 2. Consent ----
    console.rule("Step 2: RODO / GDPR consent")
    console.print(
        f"Under RODO Art. 6 and 9, [bold]{name}[/bold] must give explicit consent "
        "before we record, transcribe, or share their data."
    )
    scopes = list(DEFAULT_SCOPES)
    if Confirm.ask("Grant Art. 9 consent for processing health data?", default=False):
        scopes.append(SCOPE_PROCESS_HEALTH_DATA)
    if Confirm.ask("Grant consent to use transcripts for AI training (skill updates)?", default=False):
        scopes.append(SCOPE_TRAIN_ON_TRANSCRIPTS)

    ConsentStore().grant(senior_id, scopes=scopes, method="verbal")
    AuditLog().record(
        "consent_granted", actor="onboarding_wizard", senior_id=senior_id,
        details={"scopes": scopes, "method": "verbal"},
    )
    console.print(f"[green]✓ Consent recorded:[/green] {', '.join(scopes)}")

    # ---- 3. Schedule ----
    console.rule("Step 3: Call schedule")
    if Confirm.ask("Set up an automatic call schedule?", default=True):
        call_time = Prompt.ask("Daily call time (HH:MM, 24h)", default="10:00")
        tz = Prompt.ask("Timezone", default="Europe/Warsaw")
        days_str = Prompt.ask(
            "Days of week (comma-separated: mon,tue,wed,thu,fri,sat,sun)",
            default="mon,tue,wed,thu,fri",
        )
        days = [d.strip() for d in days_str.split(",")]
        try:
            ScheduleStore().set(senior_id, call_time=call_time, timezone=tz, days_of_week=days)
            console.print(f"[green]✓ Schedule:[/green] {call_time} {tz} [{days_str}]")
        except ValueError as exc:
            console.print(f"[yellow]Schedule not saved (invalid input): {exc}[/yellow]")

    # ---- 4. Test email ----
    console.rule("Step 4: Test email")
    sender = EmailSender()
    if fam_email and sender.is_configured():
        if Confirm.ask(f"Send a test email to {fam_email}?", default=True):
            sent = sender.send_report(
                to_addr=fam_email,
                senior_name=name,
                report_md=(
                    f"# Test — {name}\n\n"
                    "This is a test message from Hermes.\n\n"
                    "Configuration is working correctly."
                ),
                scores=None,
            )
            if sent:
                console.print(f"[green]✓ Test email sent to {fam_email}[/green]")
            else:
                console.print("[red]✗ Email failed — check SMTP_* env vars.[/red]")
    else:
        console.print("[yellow]Email not configured (SMTP_HOST/USER/PASSWORD missing) — skipping.[/yellow]")
        console.print("  See .env.example for Gmail / SendGrid setup.")

    # ---- 5. Dry-run call ----
    console.rule("Step 5: Dry-run call verification")
    if Confirm.ask("Run a dry-run text call to verify the LLM pipeline?", default=True):
        try:
            result = ManagerAgent().run_call_cycle(
                senior_id,
                console=console,
                voice_mode=False,
                allow_no_consent=False,
            )
            scores = result.get("scores", {})
            avg = round(sum(scores.values()) / len(scores), 1) if scores else "?"
            console.print(f"[green]✓ Dry-run complete. Avg score: {avg}/10[/green]")
        except Exception as exc:  # noqa: BLE001
            console.print(f"[red]✗ Dry-run failed: {exc}[/red]")
            return 1

    # ---- Done ----
    console.rule()
    console.print(f"\n[bold green]✓ Onboarding complete for {name}![/bold green]\n")
    console.print(f"  Start scheduler:  [cyan]hermes scheduler start[/cyan]")
    console.print(f"  Open dashboard:   [cyan]hermes dashboard[/cyan]")
    console.print(f"  Manual call:      [cyan]hermes call {senior_id}[/cyan]")
    return 0


# ---- Dashboard (Phase 4) ----


def cmd_dashboard(args: argparse.Namespace) -> int:
    import uvicorn
    from .dashboard.app import create_app
    app = create_app()
    console.print(f"[bold green]Dashboard running at http://{args.host}:{args.port}[/bold green]")
    uvicorn.run(app, host=args.host, port=args.port)
    return 0


# ---- Telephony commands (Phase 3) ----


def cmd_twilio_call(args: argparse.Namespace) -> int:
    from .telephony.runner import start_outbound_call

    try:
        result = start_outbound_call(
            args.senior_id,
            dry_run=args.dry_run,
            allow_no_consent=args.allow_no_consent,
            console=console,
        )
    except (PermissionError, RuntimeError) as e:
        console.print(f"[red]{e}[/red]")
        return 1
    if result["missing_env"]:
        console.print(
            f"[yellow]⚠ Missing env vars (real call would have failed): "
            f"{result['missing_env']}[/yellow]"
        )
    console.print(
        f"[green]Outbound staged.[/green] call_id={result['call_id']} "
        f"sid={result['twilio_call_sid']} dry_run={result['dry_run']}"
    )
    return 0


def cmd_twilio_serve(args: argparse.Namespace) -> int:
    import uvicorn

    from .telephony.server import create_app

    app = create_app(console=console)
    console.print(
        f"[green]Starting Hermes telephony server on "
        f"http://{args.host}:{args.port}[/green]"
    )
    console.print(
        "[dim]Webhook URLs Twilio should hit (after `ngrok http "
        f"{args.port}` or equivalent):[/dim]\n"
        f"  POST  /twilio/start\n  POST  /twilio/turn\n  POST  /twilio/status\n"
        "  GET   /twilio/audio/<call_sid>/<filename>\n"
        "  GET   /health"
    )
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
    return 0


def cmd_twilio_calls(args: argparse.Namespace) -> int:
    from .telephony.session import CallStateStore

    states = CallStateStore().list(status=args.status)
    if not states:
        console.print("[yellow]No telephony calls on file.[/yellow]")
        return 0
    table = Table(title="Telephony calls")
    for col in ("CallSid", "Senior", "Status", "Started", "Ended", "Turns", "Reason"):
        table.add_column(col)
    for s in states:
        table.add_row(
            s.call_sid,
            s.senior_id,
            s.status,
            s.started_at,
            s.ended_at or "",
            str(s.turn_count),
            s.end_reason or "",
        )
    console.print(table)
    return 0


def cmd_train(args: argparse.Namespace) -> int:
    """Run a self-play training loop to improve Operator skills."""
    from .training import TrainingLoop

    loop = TrainingLoop(
        rounds=args.rounds,
        seed=args.seed,
        console=console,
    )
    report = loop.run()
    console.print(f"[green]Training finished. {report['total_updates']} skill updates across {report['rounds']} rounds.[/green]")
    return 0


def cmd_company(args: argparse.Namespace) -> int:
    """Executive layer: company KPI status and the board-meeting governance loop."""
    from .company import CompanyRunner

    runner = CompanyRunner(console=console)
    action = getattr(args, "company_cmd", None)
    if action == "status":
        runner.status()
        return 0
    if action == "review":
        runner.run_board_meeting(
            persist=not args.no_save,
            owner_input=getattr(args, "owner_input", "") or "",
            interactive=getattr(args, "interactive", False) or False,
        )
        return 0
    console.print("[red]Unknown company command.[/red]")
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hermes-elderly-care",
        description="Multi-agent wellness call center (MVP — text mode).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_call = sub.add_parser("call", help="Run a full wellness call cycle for a senior.")
    p_call.add_argument("senior_id", help="ID of the senior to call (e.g., stefan-001)")
    p_call.add_argument(
        "--voice",
        action="store_true",
        help="Voice mode: Operator speaks via ElevenLabs, Senior side uses microphone + Whisper.",
    )
    p_call.add_argument(
        "--allow-no-consent",
        action="store_true",
        help="DEV ONLY: bypass the RODO consent gate. Do not use against real seniors.",
    )
    p_call.set_defaults(func=cmd_call)

    p_train = sub.add_parser("train", help="Run self-play training loop to improve Operator skills.")
    p_train.add_argument("--rounds", type=int, default=10, help="Number of training rounds (default: 10)")
    p_train.add_argument("--seed", type=int, default=None, help="Random seed for reproducibility")
    p_train.set_defaults(func=cmd_train)

    p_list = sub.add_parser("list-seniors", help="List all seniors on file.")
    p_list.set_defaults(func=cmd_list_seniors)

    p_hist = sub.add_parser("view-history", help="Show transcripts and reports for a senior.")
    p_hist.add_argument("senior_id")
    p_hist.set_defaults(func=cmd_view_history)

    p_skills = sub.add_parser("view-skills", help="List the current operator skills.")
    p_skills.set_defaults(func=cmd_view_skills)

    # ---- Compliance ----

    p_consent = sub.add_parser("consent", help="Manage a senior's RODO/GDPR consent record.")
    consent_sub = p_consent.add_subparsers(dest="consent_cmd", required=True)

    pc_show = consent_sub.add_parser("show", help="Show current consent state for a senior.")
    pc_show.add_argument("senior_id")
    pc_show.set_defaults(func=cmd_consent_show)

    pc_grant = consent_sub.add_parser("grant", help="Record that a senior has granted consent.")
    pc_grant.add_argument("senior_id")
    pc_grant.add_argument(
        "--scope",
        action="append",
        help=(
            "Scope to grant; repeat for multiple. "
            "Defaults to: transcribe, store_transcript, share_with_family. "
            "Other valid scope: record_audio."
        ),
    )
    pc_grant.add_argument("--method", default="verbal", choices=["verbal", "written", "proxy"])
    pc_grant.add_argument("--witness", help="Name of witness (required for --method proxy).")
    pc_grant.add_argument("--notes", help="Free-text notes attached to the consent record.")
    pc_grant.set_defaults(func=cmd_consent_grant)

    pc_revoke = consent_sub.add_parser("revoke", help="Revoke a previously granted consent.")
    pc_revoke.add_argument("senior_id")
    pc_revoke.add_argument("--notes", help="Reason / context for the revocation.")
    pc_revoke.set_defaults(func=cmd_consent_revoke)

    p_purge = sub.add_parser(
        "purge",
        help="Delete artifacts older than each senior's retention policy.",
    )
    p_purge.add_argument(
        "--senior-id",
        help="Only purge this senior. Omit to purge all seniors.",
    )
    p_purge.add_argument(
        "--dry-run",
        action="store_true",
        help="List files that would be deleted without removing them.",
    )
    p_purge.set_defaults(func=cmd_purge)

    p_forget = sub.add_parser(
        "forget",
        help="Right-to-erasure: hard-delete ALL data for a senior.",
    )
    p_forget.add_argument("senior_id")
    p_forget.add_argument("--dry-run", action="store_true")
    p_forget.add_argument("--yes", action="store_true", help="Confirm destructive action.")
    p_forget.set_defaults(func=cmd_forget)

    p_audit = sub.add_parser("audit", help="Show the tail of the compliance audit log.")
    p_audit.add_argument("-n", type=int, default=20, help="Number of recent events to show.")
    p_audit.add_argument("--senior-id", help="Filter by senior id.")
    p_audit.set_defaults(func=cmd_audit_tail)

    p_review = sub.add_parser(
        "compliance-review",
        help="Run the ComplianceReviewer agent over an artifact file.",
    )
    p_review.add_argument("file", help="Path to the artifact (markdown/text) to review.")
    p_review.add_argument(
        "--kind",
        default="generic",
        help="Artifact kind: operator_prompt, family_report, code_change, generic.",
    )
    p_review.add_argument("--context", help="Optional extra context for the reviewer.")
    p_review.set_defaults(func=cmd_compliance_review)

    # ---- Human review queue (AI Act high-risk oversight) ----

    p_rq = sub.add_parser("review-queue", help="Inspect and decide human-review entries.")
    rq_sub = p_rq.add_subparsers(dest="rq_cmd", required=True)

    rq_list = rq_sub.add_parser("list", help="List review queue entries.")
    rq_list.add_argument(
        "--status",
        choices=["pending", "approved", "flagged"],
        help="Filter by status.",
    )
    rq_list.set_defaults(func=cmd_review_list)

    rq_show = rq_sub.add_parser("show", help="Show a single entry.")
    rq_show.add_argument("entry_id")
    rq_show.set_defaults(func=cmd_review_show)

    rq_approve = rq_sub.add_parser("approve", help="Mark entry as approved by a human.")
    rq_approve.add_argument("entry_id")
    rq_approve.add_argument("--by", help="Reviewer name / identifier.")
    rq_approve.add_argument("--comment", help="Optional decision notes.")
    rq_approve.set_defaults(func=cmd_review_approve)

    rq_flag = rq_sub.add_parser("flag", help="Mark entry as flagged for follow-up.")
    rq_flag.add_argument("entry_id")
    rq_flag.add_argument("--by", help="Reviewer name / identifier.")
    rq_flag.add_argument("--comment", help="Optional decision notes.")
    rq_flag.set_defaults(func=cmd_review_flag)

    # ---- Scheduling (Phase 4) ----

    p_sched = sub.add_parser("schedule", help="Manage per-senior call schedules.")
    sched_sub = p_sched.add_subparsers(dest="sched_cmd", required=True)

    sc_set = sched_sub.add_parser("set", help="Create or update a senior's call schedule.")
    sc_set.add_argument("senior_id")
    sc_set.add_argument("--time", required=True, help="Call time in HH:MM (24h) format.")
    sc_set.add_argument("--timezone", default="UTC", help="Olson timezone name, e.g. Europe/Warsaw.")
    sc_set.add_argument(
        "--days",
        help=(
            "Comma-separated days: mon,tue,wed,thu,fri,sat,sun. "
            "Default: mon,tue,wed,thu,fri."
        ),
    )
    sc_set.set_defaults(func=cmd_schedule_set)

    sc_list = sched_sub.add_parser("list", help="List all configured call schedules.")
    sc_list.set_defaults(func=cmd_schedule_list)

    sc_rm = sched_sub.add_parser("remove", help="Remove a senior's call schedule.")
    sc_rm.add_argument("senior_id")
    sc_rm.set_defaults(func=cmd_schedule_remove)

    sc_en = sched_sub.add_parser("enable", help="Enable a previously disabled schedule.")
    sc_en.add_argument("senior_id")
    sc_en.set_defaults(func=cmd_schedule_enable)

    sc_dis = sched_sub.add_parser("disable", help="Disable a schedule without deleting it.")
    sc_dis.add_argument("senior_id")
    sc_dis.set_defaults(func=cmd_schedule_disable)

    p_scheduler = sub.add_parser(
        "scheduler",
        help="Run the APScheduler daemon that fires scheduled calls.",
    )
    scheduler_sub = p_scheduler.add_subparsers(dest="scheduler_cmd", required=True)
    sch_start = scheduler_sub.add_parser("start", help="Start the cron daemon.")
    sch_start.add_argument(
        "--once",
        action="store_true",
        help="Run all enabled calls immediately instead of starting a long-running daemon.",
    )
    sch_start.add_argument(
        "--board-review-hours",
        type=int,
        default=0,
        help="Also run an executive board meeting every N hours (0 = disabled).",
    )
    sch_start.add_argument(
        "--board-review-time",
        help="Run executive board meeting daily at fixed HH:MM (24h), e.g. 10:00.",
    )
    sch_start.add_argument(
        "--board-review-timezone",
        default="Europe/Warsaw",
        help="Timezone for --board-review-time, e.g. Europe/Warsaw.",
    )
    sch_start.set_defaults(func=cmd_scheduler_start)

    # ---- Telephony (Phase 3) ----

    p_tcall = sub.add_parser(
        "twilio-call",
        help="Place an outbound wellness call via Twilio (or dry-run).",
    )
    p_tcall.add_argument("senior_id")
    p_tcall.add_argument(
        "--dry-run",
        action="store_true",
        help="Force dry-run mode even if Twilio creds are present.",
    )
    p_tcall.add_argument(
        "--allow-no-consent",
        action="store_true",
        help="DEV ONLY: bypass missing consent scopes.",
    )
    p_tcall.set_defaults(func=cmd_twilio_call)

    p_tserve = sub.add_parser(
        "twilio-serve",
        help="Run the FastAPI webhook server that handles Twilio call flow.",
    )
    p_tserve.add_argument("--host", default="0.0.0.0")
    p_tserve.add_argument("--port", type=int, default=8000)
    p_tserve.set_defaults(func=cmd_twilio_serve)

    p_tcalls = sub.add_parser(
        "twilio-calls",
        help="List staged / live / completed telephony calls.",
    )
    p_tcalls.add_argument(
        "--status",
        choices=[
            "initiated", "ringing", "in_progress", "completed",
            "failed", "busy", "no-answer", "canceled", "voicemail",
        ],
        help="Filter by status.",
    )
    p_tcalls.set_defaults(func=cmd_twilio_calls)

    # ---- Onboarding wizard ----
    p_onboard = sub.add_parser(
        "onboard",
        help="Interactive wizard: create a senior, record consent, set schedule, verify email + LLM.",
    )
    p_onboard.set_defaults(func=cmd_onboard)

    # ---- Dashboard (Phase 4) ----
    p_dash = sub.add_parser(
        "dashboard",
        help="Start the family dashboard web UI.",
    )
    p_dash.add_argument("--host", default="127.0.0.1")
    p_dash.add_argument("--port", type=int, default=8080)
    p_dash.set_defaults(func=cmd_dashboard)

    # ---- Company (executive layer / autonomous org) ----
    p_company = sub.add_parser(
        "company",
        help="Executive layer: company KPI status and the board-meeting governance loop.",
    )
    company_sub = p_company.add_subparsers(dest="company_cmd", required=True)

    pco_status = company_sub.add_parser(
        "status",
        help="Show company-wide KPIs and the current strategic directive (no LLM).",
    )
    pco_status.set_defaults(func=cmd_company)

    pco_review = company_sub.add_parser(
        "review",
        help="Run the executive board meeting: Quality Director + HR + CEO directive.",
    )
    pco_review.add_argument(
        "--no-save",
        action="store_true",
        help="Run the board meeting without persisting the snapshot/directive.",
    )
    pco_review.add_argument(
        "--owner-input",
        help="Pass the owner's strategic input to the board (overrides owner_input.md).",
    )
    pco_review.add_argument(
        "--interactive",
        "-i",
        action="store_true",
        help="Prompt the owner for input before the board meeting.",
    )
    pco_review.set_defaults(func=cmd_company)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
