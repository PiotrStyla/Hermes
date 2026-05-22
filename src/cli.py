"""Command-line interface for the Hermes Elderly Care system."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

from .agents.manager import ManagerAgent
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
    p_call.set_defaults(func=cmd_call)

    p_list = sub.add_parser("list-seniors", help="List all seniors on file.")
    p_list.set_defaults(func=cmd_list_seniors)

    p_hist = sub.add_parser("view-history", help="Show transcripts and reports for a senior.")
    p_hist.add_argument("senior_id")
    p_hist.set_defaults(func=cmd_view_history)

    p_skills = sub.add_parser("view-skills", help="List the current operator skills.")
    p_skills.set_defaults(func=cmd_view_skills)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
