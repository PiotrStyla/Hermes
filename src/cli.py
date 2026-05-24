"""Command-line interface for the Hermes Elderly Care system."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

from .agents.manager import ManagerAgent
from .compliance import (
    AuditLog,
    ConsentStore,
    RetentionStore,
)
from .compliance.consent import DEFAULT_SCOPES
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

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
