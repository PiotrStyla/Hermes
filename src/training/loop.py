"""Training loop — runs N simulated conversations to improve Operator skills.

Zero telephony. Pure text-mode self-play between Operator and SeniorPersonaAgent.
Each iteration: generate scenario → converse → Supervisor review → update skills.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from ..agents.manager import ManagerAgent
from ..agents.operator import OperatorAgent
from ..agents.senior_persona import SeniorPersonaAgent
from ..agents.supervisor import SupervisorAgent
from ..conversation.transcript import format_transcript
from ..skills.loader import SkillsLoader
from ..skills.updater import SkillsUpdater
from .checklist_tracker import ChecklistTracker
from .scenario_generator import ARCHETYPES, ScenarioGenerator
from .sound_generator import SoundEventGenerator


@dataclass
class TrainingMetrics:
    round: int
    archetype: str
    scores: dict[str, int]
    skill_updates: list[str]
    duration_s: float
    issues: list[str] = field(default_factory=list)
    sound_injected: bool = False
    sound_type: str = ""
    sound_severity: str = ""
    checklist_completion: float = 0.0
    checklist_missed: list[str] = field(default_factory=list)


class TrainingLoop:
    """Orchestrates N rounds of: scenario → conversation → review → skill update."""

    def __init__(
        self,
        rounds: int = 10,
        seed: int | None = None,
        console: Console | None = None,
    ):
        self.rounds = rounds
        self.console = console or Console()
        self.generator = ScenarioGenerator(seed=seed)
        self.sound_gen = SoundEventGenerator(seed=seed, sound_probability=0.6)
        self.checklist = ChecklistTracker()
        self.operator = OperatorAgent()
        self.senior = SeniorPersonaAgent()
        self.supervisor = SupervisorAgent()
        self.manager = ManagerAgent()
        self.loader = SkillsLoader()
        self.updater = SkillsUpdater()
        self.metrics: list[TrainingMetrics] = []
        # Honour the CEO's strategic directive: the Operator trains with the
        # company's current focus area emphasised in its prompt.
        from ..company.state import CompanyState
        self.directive = CompanyState.load().directive
        self.operator.directive_note = self.directive.to_operator_note()

    def run(self) -> dict[str, Any]:
        directive_line = (
            f"\n[cyan]Directive:[/cyan] focus {self.directive.focus_metric} "
            f"via '{self.directive.focus_skill}'"
            if not self.directive.is_empty()
            else ""
        )
        self.console.print(Panel(
            f"[bold]Training loop: {self.rounds} rounds[/bold]\n"
            f"Model: {self.operator.model}\n"
            f"Archetypes: {len(ARCHETYPES)}"
            f"{directive_line}",
            title="Hermes Training"
        ))

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
        ) as progress:
            task = progress.add_task("Training...", total=self.rounds)

            for i in range(1, self.rounds + 1):
                t0 = time.monotonic()
                persona_md, profile = self.generator.generate()
                arch_name = profile.name

                # Phase 1: conversation (inline — training profiles have no disk files)
                senior_system = self.senior.build_system_prompt(persona_md)
                operator_system = self.operator.build_system_prompt(profile, "")
                history: list[dict[str, str]] = []

                # Decide if we inject a sound event (only distraction)
                sound = None
                sound_turn = 0
                if self.sound_gen.should_inject_sound():
                    sound, sound_turn = self.sound_gen.generate()
                    self.console.print(f"[cyan]🔊 Sound injected:[/cyan] {sound.name} at turn {sound_turn}")

                for turn_num in range(1, 19):  # MAX_TURNS
                    op_msg = self.operator.turn(operator_system, history)
                    history.append({"role": "operator", "content": op_msg})
                    if "<<END_CALL>>" in op_msg:
                        senior_msg = self.senior.turn(senior_system, history)
                        history.append({"role": "senior", "content": senior_msg})
                        break

                    # Inject sound event at the specified turn
                    if sound and turn_num == sound_turn:
                        sound_announcement = self.sound_gen.format_sound_announcement(sound)
                        history.append({"role": "senior", "content": sound_announcement})
                        self.console.print(f"[magenta]🔔 {sound.name}:[/magenta] {sound.description}")
                    else:
                        senior_msg = self.senior.turn(senior_system, history)
                        history.append({"role": "senior", "content": senior_msg})

                # Phase 2a: checklist evaluation
                checklist_result = self.checklist.evaluate(history)

                # Phase 2b: supervisor review
                transcript_md = format_transcript(profile.name, history)
                skills_summary = self.loader.assemble_prompt_section()
                feedback = self.supervisor.review(transcript_md, skills_summary)

                scores = feedback.get("scores", {})
                skill_updates = feedback.get("skill_updates") or []
                applied: list[str] = []

                # Phase 3: apply skill updates
                for upd in skill_updates:
                    skill_name = upd.get("skill")
                    patch = upd.get("patch")
                    if not skill_name or not patch:
                        continue
                    current = self.loader.get(skill_name)
                    if current is None:
                        continue
                    try:
                        new_content = self.manager.rewrite_skill(skill_name, current, patch)
                        self.updater.update(skill_name, new_content)
                        applied.append(skill_name)
                    except Exception:
                        pass

                elapsed = time.monotonic() - t0
                self.metrics.append(TrainingMetrics(
                    round=i,
                    archetype=arch_name,
                    scores=scores,
                    skill_updates=applied,
                    duration_s=elapsed,
                    issues=feedback.get("issues", []),
                    sound_injected=sound is not None,
                    sound_type=sound.name if sound else "",
                    sound_severity=sound.severity if sound else "",
                    checklist_completion=checklist_result.completion_pct,
                    checklist_missed=checklist_result.missed_items,
                ))

                avg = self._avg_scores()
                progress.update(
                    task,
                    advance=1,
                    description=(
                        f"Round {i}/{self.rounds} | "
                        f"Avg: W{avg.get('warmth',0)} L{avg.get('listening',0)} "
                        f"I{avg.get('info_quality',0)} B{avg.get('brevity',0)} | "
                        f"{elapsed:.1f}s"
                    ),
                )

        return self._finalize()

    def _avg_scores(self) -> dict[str, float]:
        if not self.metrics:
            return {}
        keys = ["warmth", "listening", "info_quality", "brevity"]
        return {
            k: sum(m.scores.get(k, 0) for m in self.metrics) / len(self.metrics)
            for k in keys
        }

    def _finalize(self) -> dict[str, Any]:
        self.console.print(Panel("Training complete", title="Results"))

        # Trend table
        table = Table(title="Score Trend")
        table.add_column("Round", justify="right")
        table.add_column("Archetype")
        table.add_column("W", justify="right")
        table.add_column("L", justify="right")
        table.add_column("I", justify="right")
        table.add_column("B", justify="right")
        table.add_column("Updates")
        table.add_column("Time")

        for m in self.metrics:
            s = m.scores
            table.add_row(
                str(m.round),
                m.archetype[:25],
                str(s.get("warmth", "-")),
                str(s.get("listening", "-")),
                str(s.get("info_quality", "-")),
                str(s.get("brevity", "-")),
                str(len(m.skill_updates)),
                f"{m.duration_s:.1f}s",
            )

        self.console.print(table)

        # Summary
        avg = self._avg_scores()
        first = self.metrics[0].scores if self.metrics else {}
        last = self.metrics[-1].scores if self.metrics else {}
        total_updates = sum(len(m.skill_updates) for m in self.metrics)
        total_time = sum(m.duration_s for m in self.metrics)

        self.console.print(f"\n[bold]Average scores:[/bold] " + " | ".join(
            f"{k}: {v:.1f}" for k, v in avg.items()
        ))
        if first and last:
            delta = {k: last.get(k, 0) - first.get(k, 0) for k in avg}
            self.console.print("[bold]First → Last delta:[/bold] " + " | ".join(
                f"{k}: {v:+.0f}" for k, v in delta.items()
            ))
        self.console.print(f"[bold]Total skill updates:[/bold] {total_updates}")
        self.console.print(f"[bold]Total time:[/bold] {total_time:.0f}s ({total_time/60:.1f}m)")

        # Save report
        sounds_injected = sum(1 for m in self.metrics if m.sound_injected)
        avg_checklist = (
            round(sum(m.checklist_completion for m in self.metrics) / len(self.metrics), 1)
            if self.metrics else 0.0
        )
        report = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "rounds": self.rounds,
            "model": self.operator.model,
            "average_scores": avg,
            "first_scores": first,
            "last_scores": last,
            "total_updates": total_updates,
            "total_time_s": total_time,
            "sounds_injected": sounds_injected,
            "average_checklist_completion": avg_checklist,
            "rounds_detail": [
                {
                    "round": m.round,
                    "archetype": m.archetype,
                    "scores": m.scores,
                    "skill_updates": m.skill_updates,
                    "issues": m.issues,
                    "duration_s": m.duration_s,
                    "sound_injected": m.sound_injected,
                    "sound_type": m.sound_type,
                    "sound_severity": m.sound_severity,
                    "checklist_completion": m.checklist_completion,
                    "checklist_missed": m.checklist_missed,
                }
                for m in self.metrics
            ],
        }

        report_path = Path("data/training") / f"report_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        self.console.print(f"\n[green]JSON report saved:[/green] {report_path}")

        # Markdown report for Obsidian
        md_path = report_path.with_suffix(".md")
        md_content = self._build_markdown_report(report)
        md_path.write_text(md_content, encoding="utf-8")
        self.console.print(f"[green]Markdown report saved:[/green] {md_path}")

        return report

    def _build_markdown_report(self, report: dict[str, Any]) -> str:
        """Build an Obsidian-compatible markdown training report."""
        ts = report["timestamp"]
        avg = report["average_scores"]
        first = report["first_scores"]
        last = report["last_scores"]

        lines = [
            "---",
            f"date: {ts}",
            "tags: [hermes, training, ai, emergency, sound, recovery]",
            "---",
            "",
            f"# Hermes Training Report — {ts[:19]}",
            "",
            f"- **Rounds:** {report['rounds']}",
            f"- **Model:** {report['model']}",
            f"- **Total time:** {report['total_time_s']:.0f}s ({report['total_time_s']/60:.1f}m)",
            f"- **Skill updates applied:** {report['total_updates']}",
            f"- **Sounds injected:** {report.get('sounds_injected', 0)}",
            f"- **Avg checklist completion:** {report.get('average_checklist_completion', 0)}%",
            "",
            "## Score Trend",
            "",
            "| Round | Archetype | W | L | I | B | Updates | Sound | Checklist | Time |",
            "|------:|-----------|--:|--:|--:|--:|--------:|------:|----------:|-----:|",
        ]

        for m in report["rounds_detail"]:
            s = m["scores"]
            sound = m.get("sound_type", "")[:12] if m.get("sound_injected") else "-"
            chk = f"{m.get('checklist_completion', 0)}%"
            lines.append(
                f"| {m['round']} | {m['archetype'][:25]} | "
                f"{s.get('warmth', '-')} | {s.get('listening', '-')} | "
                f"{s.get('info_quality', '-')} | {s.get('brevity', '-')} | "
                f"{len(m['skill_updates'])} | {sound} | {chk} | {m['duration_s']:.1f}s |"
            )

        lines += [
            "",
            "## Averages",
            "",
            "| Dimension | Score |",
            "|-----------|------:|",
        ]
        for k, v in avg.items():
            lines.append(f"| {k} | {v:.1f} |")

        if first and last:
            lines += [
                "",
                "## First → Last Delta",
                "",
                "| Dimension | First | Last | Δ |",
                "|-----------|------:|-----:|---:|",
            ]
            for k in avg:
                fv = first.get(k, 0)
                lv = last.get(k, 0)
                lines.append(f"| {k} | {fv} | {lv} | {lv - fv:+} |")

        lines += [
            "",
            "## Issues Found",
            "",
        ]
        for m in report["rounds_detail"]:
            for issue in m.get("issues", []):
                lines.append(f"- [Round {m['round']}] {issue}")

        lines += [
            "",
            "## Skill Updates",
            "",
        ]
        for m in report["rounds_detail"]:
            for sk in m.get("skill_updates", []):
                lines.append(f"- [Round {m['round']}] `{sk}.md`")

        return "\n".join(lines) + "\n"
