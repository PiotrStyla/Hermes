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
from .scenario_generator import ARCHETYPES, ScenarioGenerator


@dataclass
class TrainingMetrics:
    round: int
    archetype: str
    scores: dict[str, int]
    skill_updates: list[str]
    duration_s: float
    issues: list[str] = field(default_factory=list)


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
        self.operator = OperatorAgent()
        self.supervisor = SupervisorAgent()
        self.manager = ManagerAgent()
        self.loader = SkillsLoader()
        self.updater = SkillsUpdater()
        self.metrics: list[TrainingMetrics] = []

    def run(self) -> dict[str, Any]:
        self.console.print(Panel(
            f"[bold]Training loop: {self.rounds} rounds[/bold]\n"
            f"Model: {self.operator.model}\n"
            f"Archetypes: {len(ARCHETYPES)}",
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
                senior = SeniorPersonaAgent()
                senior_system = senior.build_system_prompt(persona_md)
                operator_system = self.operator.build_system_prompt(profile, "")
                history: list[dict[str, str]] = []

                for _ in range(18):  # MAX_TURNS
                    op_msg = self.operator.turn(operator_system, history)
                    history.append({"role": "operator", "content": op_msg})
                    if "<<END_CALL>>" in op_msg:
                        senior_msg = senior.turn(senior_system, history)
                        history.append({"role": "senior", "content": senior_msg})
                        break
                    senior_msg = senior.turn(senior_system, history)
                    history.append({"role": "senior", "content": senior_msg})

                # Phase 2: supervisor review
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
        report = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "rounds": self.rounds,
            "model": self.operator.model,
            "average_scores": avg,
            "first_scores": first,
            "last_scores": last,
            "total_updates": total_updates,
            "total_time_s": total_time,
            "rounds_detail": [
                {
                    "round": m.round,
                    "archetype": m.archetype,
                    "scores": m.scores,
                    "skill_updates": m.skill_updates,
                    "issues": m.issues,
                    "duration_s": m.duration_s,
                }
                for m in self.metrics
            ],
        }

        report_path = Path("data/training") / f"report_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        self.console.print(f"\n[green]Report saved:[/green] {report_path}")

        return report
