"""Company runner — orchestrates the executive "board meeting".

One board meeting is the company's governance loop:

  1. Aggregate company-wide KPIs from existing artefacts.   (MetricsAggregator)
  2. Quality Director finds systemic quality themes.        (QualityDirectorAgent)
  3. HR reviews the Operator's performance over time.       (HRAgent)
  4. CEO sets ONE strategic directive from all of the above.(CEOAgent)
  5. Persist the snapshot + directive + decisions.          (CompanyState)

The resulting directive is the lever that governs the self-improvement loop:
the Trainer/Manager can read `CompanyState.directive` to know what to prioritise
instead of drifting unsupervised (which previously let brevity decay).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from .business_plan import BusinessPlanAgent
from .ceo import CEOAgent
from .cmo import CMOAgent
from .hr import HRAgent, OperatorScorecard
from .metrics import CompanyMetrics, MetricsAggregator
from .quality_director import QualityDirectorAgent
from .state import COMPANY_DIR, CompanyState, Directive, GrowthPlan, StaffingPlan


@dataclass
class BoardMeetingResult:
    """Everything produced by one board meeting."""

    metrics: CompanyMetrics
    quality_analysis: str = ""
    hr_verdict: str = ""
    scorecard: OperatorScorecard | None = None
    directive: Directive | None = None
    growth_plan: GrowthPlan | None = None
    innovation_agenda: str = ""
    owner_input: str = ""


class CompanyRunner:
    """Runs the executive governance loop over the company's data."""

    def __init__(
        self,
        console: Console | None = None,
        ceo: CEOAgent | None = None,
        quality_director: QualityDirectorAgent | None = None,
        hr: HRAgent | None = None,
        cmo: CMOAgent | None = None,
        aggregator: MetricsAggregator | None = None,
        reports_dir: Path | None = None,
    ):
        self.console = console or Console()
        self.aggregator = aggregator or MetricsAggregator()
        self.reports_dir = reports_dir or (COMPANY_DIR / "reports")
        # Agents are created lazily so `status` (no LLM) works without API keys.
        self._ceo = ceo
        self._quality_director = quality_director
        self._hr = hr
        self._cmo = cmo
        self._business_planner = None

    @property
    def ceo(self) -> CEOAgent:
        if self._ceo is None:
            self._ceo = CEOAgent()
        return self._ceo

    @property
    def business_planner(self) -> BusinessPlanAgent:
        if self._business_planner is None:
            self._business_planner = BusinessPlanAgent()
        return self._business_planner

    @property
    def cmo(self) -> CMOAgent:
        if self._cmo is None:
            self._cmo = CMOAgent()
        return self._cmo

    @property
    def quality_director(self) -> QualityDirectorAgent:
        if self._quality_director is None:
            self._quality_director = QualityDirectorAgent()
        return self._quality_director

    @property
    def hr(self) -> HRAgent:
        if self._hr is None:
            self._hr = HRAgent()
        return self._hr

    # ---- Read-only status ----

    def status(self, state: CompanyState | None = None) -> CompanyMetrics:
        """Print the current company dashboard (no LLM calls). Returns metrics."""
        state = state or CompanyState.load()
        metrics = self.aggregator.aggregate()
        self._print_status(state, metrics)
        return metrics

    # ---- Full governance loop ----

    def run_board_meeting(
        self,
        persist: bool = True,
        owner_input: str = "",
        interactive: bool = False,
        training_rounds: int = 0,
    ) -> BoardMeetingResult:
        """Run the full executive loop and (optionally) persist the outcome."""
        state = CompanyState.load()

        self.console.print(Panel(
            "[bold cyan]Hermes — Board Meeting[/bold cyan]",
            title="Company",
            border_style="bright_white",
        ))
        metrics = self.aggregator.aggregate()
        self._print_status(state, metrics)

        owner_input = self._gather_owner_input(owner_input, interactive)
        if owner_input:
            self.console.print(Panel(owner_input, title="Owner input"))

        # 2. Quality Director
        self.console.print(Panel(
            "[blue]Quality Director — systemic analysis[/blue]",
            title="Agenda 1",
            border_style="blue",
        ))
        quality_analysis = self.quality_director.analyze(metrics, owner_input=owner_input)
        self.console.print(quality_analysis)

        # 3. HR
        self.console.print(Panel(
            "[cyan]HR — operator performance review[/cyan]",
            title="Agenda 2",
            border_style="cyan",
        ))
        scorecard = OperatorScorecard.from_metrics(metrics)
        hr_verdict = self.hr.review_operator(scorecard, owner_input=owner_input)
        self.console.print(
            f"[dim]Recommendation: {scorecard.recommendation} | "
            f"weakest: {scorecard.weakest_axis or 'n/a'}[/dim]"
        )
        self.console.print(hr_verdict)

        # 4. CEO directive
        self.console.print(Panel(
            "[green]CEO — strategic directive[/green]",
            title="Agenda 3",
            border_style="green",
        ))
        recent_ceo_directives = [
            f"{d.summary}: {d.rationale[:120]}"
            for d in state.decisions
            if d.actor == "ceo" and d.summary.startswith("New directive:")
        ][-3:]
        directive = self.ceo.decide(
            metrics,
            quality_analysis,
            recent_ceo_directives=recent_ceo_directives,
            owner_input=owner_input,
        )
        self.console.print(
            f"[bold green]Focus metric:[/bold green] {directive.focus_metric}\n"
            f"[bold green]Focus skill:[/bold green] {directive.focus_skill}\n"
            f"[bold green]Rationale:[/bold green] {directive.rationale}"
        )
        if directive.falsification_condition:
            self.console.print(
                f"[bold red]Warunek obalenia:[/bold red] {directive.falsification_condition}"
            )
        if directive.owner_questions:
            self.console.print(Panel(
                "\n".join(f"- {q}" for q in directive.owner_questions),
                title="[bold yellow]CEO questions for the owner[/bold yellow]",
                border_style="yellow",
            ))

        # 4b. CEO innovation agenda
        self.console.print(Panel(
            "[magenta]CEO — innovation agenda[/magenta]",
            title="Agenda 3b",
            border_style="magenta",
        ))
        recent_decisions = [
            f"{d.actor}: {d.summary}"
            for d in state.decisions[-8:]
        ]
        innovation_agenda = self.ceo.propose_innovation_agenda(
            metrics,
            recent_decisions=recent_decisions,
            owner_input=owner_input,
        )
        self.console.print(innovation_agenda)

        # 5. CMO growth plan — where new clients come from
        self.console.print(Panel(
            "[yellow]CMO — client acquisition plan[/yellow]",
            title="Agenda 4",
            border_style="yellow",
        ))
        growth_plan = self.cmo.plan(metrics, owner_input=owner_input)
        self._print_growth_plan(growth_plan)

        # 6. Persist
        if persist:
            state.record_snapshot(metrics.to_snapshot())
            state.set_directive(directive)
            state.set_growth_plan(growth_plan)
            if owner_input.strip():
                state.log_decision(
                    actor="owner",
                    summary="Owner input for this board meeting",
                    rationale=owner_input[:500],
                )
            state.log_decision(
                actor="quality_director",
                summary="Systemic quality analysis",
                rationale=quality_analysis[:500],
            )
            state.log_decision(
                actor="hr",
                summary=f"Operator review — recommendation: {scorecard.recommendation}",
                rationale=hr_verdict[:500],
            )
            state.log_decision(
                actor="ceo",
                summary="Innovation agenda: core + adjacent + moonshot",
                rationale=innovation_agenda[:500],
            )
            path = state.save()
            report_path = self._save_board_report(
                BoardMeetingResult(
                    metrics=metrics,
                    quality_analysis=quality_analysis,
                    hr_verdict=hr_verdict,
                    scorecard=scorecard,
                    directive=directive,
                    growth_plan=growth_plan,
                    innovation_agenda=innovation_agenda,
                    owner_input=owner_input,
                ),
                state,
            )
            self.console.print(f"\n[green]Board meeting saved to:[/green] {path}")
            self.console.print(f"[green]Board report saved to:[/green] {report_path}")

            # Close the loop: the directive we just set drives a fresh round of
            # operator self-play training, so the next board meeting sees new
            # data instead of re-analysing a frozen snapshot.
            if training_rounds > 0:
                self._run_training(training_rounds, directive)

        return BoardMeetingResult(
            metrics=metrics,
            quality_analysis=quality_analysis,
            hr_verdict=hr_verdict,
            scorecard=scorecard,
            directive=directive,
            growth_plan=growth_plan,
            innovation_agenda=innovation_agenda,
            owner_input=owner_input,
        )

    def _run_training(self, rounds: int, directive: Directive) -> None:
        """Run a self-play training loop driven by the freshly-set directive.

        The directive is already persisted to CompanyState at this point, so
        TrainingLoop picks it up and emphasises the focus skill in the operator
        prompt. This produces a new training report, giving the next board
        meeting fresh data to analyse — closing the strategy→action→data loop.
        """
        self.console.print(Panel(
            f"[bold]Closing the loop:[/bold] {rounds} training round(s) on "
            f"focus [cyan]{directive.focus_metric or 'n/a'}[/cyan] via "
            f"'[cyan]{directive.focus_skill or 'n/a'}[/cyan]'",
            title="Agenda 5 — Directive → Training",
            border_style="bright_magenta",
        ))
        try:
            from ..training import TrainingLoop

            TrainingLoop(rounds=rounds, console=self.console).run()
        except Exception as exc:  # noqa: BLE001 — training must never crash governance
            self.console.print(f"[red]Training round failed: {exc}[/red]")

    def _gather_owner_input(self, provided: str, interactive: bool) -> str:
        """Resolve owner input from CLI arg, file, or interactive prompt."""
        if provided.strip():
            return provided.strip()

        owner_input_file = COMPANY_DIR / "owner_input.md"
        if owner_input_file.exists():
            try:
                text = owner_input_file.read_text(encoding="utf-8").strip()
                if text:
                    return text
            except OSError:
                pass

        if interactive:
            return Prompt.ask(
                "\n[bold]Owner input for the board[/bold] (what should the board focus on?)",
                default="",
            ).strip()

        return ""

    def _save_board_report(self, result: BoardMeetingResult, state: CompanyState) -> Path:
        self.reports_dir.mkdir(parents=True, exist_ok=True)

        report_dt = datetime.now().astimezone()
        if result.directive and result.directive.set_at:
            try:
                report_dt = datetime.fromisoformat(result.directive.set_at)
            except ValueError:
                report_dt = datetime.now().astimezone()

        report_path = self.reports_dir / f"board_{report_dt.strftime('%Y-%m-%d_%H-%M')}.md"
        scores = result.metrics.avg_scores
        score_lines = [
            f"- {axis}: {scores.get(axis, '—')}"
            for axis in ("warmth", "listening", "info_quality", "brevity")
        ]

        channels = result.growth_plan.channels if result.growth_plan else []
        steps = result.growth_plan.next_steps if result.growth_plan else []

        channel_lines = [f"  - {c}" for c in channels] or ["  - (none)"]
        step_lines = [f"  {i + 1}. {s}" for i, s in enumerate(steps)] or ["  - (none)"]

        owner_questions = (
            result.directive.owner_questions
            if result.directive and result.directive.owner_questions
            else []
        )
        question_lines = [f"  - {q}" for q in owner_questions] or ["  - (none)"]
        owner_input_lines = [f"  - {line}" for line in (result.owner_input or "").splitlines() if line.strip()] or ["  - (none)"]

        directive = result.directive
        fc = directive.falsification_condition if directive else ""
        weakest = result.metrics.weakest_axis() or "n/a"
        weakest_score = result.metrics.avg_scores.get(weakest, "—")
        best = max(result.metrics.avg_scores, key=lambda k: result.metrics.avg_scores[k]) if result.metrics.avg_scores else "n/a"
        best_score = result.metrics.avg_scores.get(best, "—")
        streszczenie = (
            f"Raport z posiedzenia zarządu Hermes ({report_dt.strftime('%Y-%m-%d')}). "
            f"Najsłabszy KPI: **{weakest}** ({weakest_score}), najsilniejszy: **{best}** ({best_score}). "
            f"Dyrektywa CEO: focus na **{directive.focus_metric if directive else 'n/a'}** "
            f"(skill: {directive.focus_skill if directive else 'n/a'}). "
            f"Warunek obalenia: {fc or 'n/a'}."
        )

        content = [
            "# Executive Board Report",
            "",
            f"- Date: {report_dt.isoformat()}",
            f"- Seniors: {result.metrics.n_seniors}",
            f"- Calls completed: {result.metrics.n_calls}",
            f"- Training rounds: {result.metrics.n_training_rounds}",
            "",
            "## Streszczenie",
            streszczenie,
            "",
            "## KPI Snapshot",
            *score_lines,
            "",
            "## Owner Input",
            *owner_input_lines,
            "",
            "## CEO Directive",
            f"- Focus metric: {directive.focus_metric if directive else 'n/a'}",
            f"- Focus skill: {directive.focus_skill if directive else 'n/a'}",
            f"- Rationale: {directive.rationale if directive else 'n/a'}",
            f"- **Warunek obalenia:** {fc or 'n/a'}",
            "",
            "## Questions for the Owner",
            *question_lines,
            "",
            "## Quality Director",
            result.quality_analysis or "(no analysis)",
            "",
            "## HR Verdict",
            result.hr_verdict or "(no verdict)",
            "",
            "## Growth Plan",
            f"- Posture: {result.growth_plan.posture if result.growth_plan else 'n/a'}",
            "- Channels:",
            *channel_lines,
            "- Next steps:",
            *step_lines,
            "",
            "## Innovation Agenda",
            result.innovation_agenda or "(no innovation agenda)",
            "",
            "## Staffing",
            f"- Stage: {state.staffing_plan.stage}",
            f"- Payroll: {state.staffing_plan.total_monthly_payroll_pln} PLN",
            f"- Budget: {state.staffing_plan.monthly_budget_pln} PLN",
            f"- Remaining: {state.staffing_plan.remaining_budget_pln} PLN",
            "",
            "---",
            "",
            "## Podpis",
            f"Dokument wygenerowany automatycznie przez Hermes AI Board · {report_dt.strftime('%Y-%m-%d %H:%M')} UTC",
            "",
        ]
        report_path.write_text("\n".join(content), encoding="utf-8")
        return report_path

    # ---- Rendering ----

    @staticmethod
    def _score_color(score: float) -> str:
        if score >= 8.0:
            return "green"
        if score >= 7.0:
            return "yellow"
        return "red"

    def _print_status(self, state: CompanyState, metrics: CompanyMetrics) -> None:
        table = Table(title="Company KPIs")
        table.add_column("Metric")
        table.add_column("Value", justify="right")
        scores = metrics.avg_scores or {}
        for axis in ("warmth", "listening", "info_quality", "brevity"):
            raw = scores.get(axis)
            if raw is not None:
                color = self._score_color(float(raw))
                table.add_row(
                    f"[{color}]{axis}[/{color}]",
                    f"[bold {color}]{raw}[/bold {color}]",
                )
            else:
                table.add_row(axis, "—")
        table.add_row("seniors", str(metrics.n_seniors))
        table.add_row("calls completed", str(metrics.n_calls))
        table.add_row("training rounds", str(metrics.n_training_rounds))
        self.console.print(table)
        self._print_staffing_plan(state.staffing_plan)

        d = state.directive
        if not d.is_empty():
            self.console.print(Panel(
                f"[bold]Focus metric:[/bold] {d.focus_metric}\n"
                f"[bold]Focus skill:[/bold] {d.focus_skill}\n"
                f"[bold]Rationale:[/bold] {d.rationale}\n"
                f"[dim]set {d.set_at} by {d.set_by}[/dim]",
                title="Current Directive",
            ))
        else:
            self.console.print("[yellow]No directive set yet. Run `company review`.[/yellow]")

        if not state.growth_plan.is_empty():
            self._print_growth_plan(state.growth_plan)

    def _print_staffing_plan(self, plan: StaffingPlan) -> None:
        table = Table(title="Staffing plan")
        table.add_column("Position")
        table.add_column("Headcount", justify="right")
        table.add_column("Cost / FTE (PLN)", justify="right")
        table.add_column("Monthly total (PLN)", justify="right")
        for pos in plan.positions:
            table.add_row(
                pos.title,
                str(pos.headcount),
                str(pos.monthly_cost_pln),
                str(pos.monthly_total_pln),
            )
        self.console.print(table)

        status_color = "green" if plan.is_balanced else "red"
        self.console.print(
            f"[bold]Stage:[/bold] {plan.stage} | "
            f"[bold]Payroll:[/bold] {plan.total_monthly_payroll_pln} PLN | "
            f"[bold]Budget:[/bold] {plan.monthly_budget_pln} PLN | "
            f"[bold {status_color}]Remaining:[/bold {status_color}] {plan.remaining_budget_pln} PLN"
        )

    def _print_growth_plan(self, plan: GrowthPlan) -> None:
        channels = "\n".join(f"  - {c}" for c in plan.channels) or "  (none)"
        segments = "\n".join(f"  - {s}" for s in plan.target_segments) or "  (none)"
        steps = "\n".join(f"  {i+1}. {s}" for i, s in enumerate(plan.next_steps)) or "  (none)"
        self.console.print(Panel(
            f"[bold]Posture:[/bold] {plan.posture or 'n/a'}\n\n"
            f"[bold]Channels (where to find clients):[/bold]\n{channels}\n\n"
            f"[bold]Target segments:[/bold]\n{segments}\n\n"
            f"[bold]Messaging:[/bold] {plan.messaging}\n\n"
            f"[bold]Next steps:[/bold]\n{steps}",
            title="Growth Plan (CMO)",
        ))

    # ---- Business Plan ----

    def generate_business_plan(self, owner_input: str = "") -> Path:
        """Manager commissions a full business plan from all department heads.

        Gathers:
        - Quality Director: systemic quality analysis
        - HR: operator performance review
        - CMO: growth / acquisition plan
        - CEO (now Manager): innovation agenda
        - DPO: compliance summary (from docs/compliance/)
        - BusinessPlanAgent: synthesizes everything into one document
        """
        state = CompanyState.load()
        metrics = self.aggregator.aggregate()

        self.console.print(Panel(
            "[bold cyan]Hermes — Business Plan Generation[/bold cyan]\n"
            "[dim]Manager commissions all department heads[/dim]",
            title="Company",
            border_style="bright_white",
        ))
        self._print_status(state, metrics)

        owner_input = self._gather_owner_input(owner_input, interactive=False)
        if owner_input:
            self.console.print(Panel(owner_input, title="Owner input"))

        # 1. Quality Director
        self.console.print(Panel(
            "[blue]Quality Director — systemic analysis[/blue]",
            title="Input 1", border_style="blue",
        ))
        quality_analysis = self.quality_director.analyze(metrics, owner_input=owner_input)
        self.console.print(quality_analysis[:500] + "..." if len(quality_analysis) > 500 else quality_analysis)

        # 2. HR
        self.console.print(Panel(
            "[cyan]HR — operator performance review[/cyan]",
            title="Input 2", border_style="cyan",
        ))
        scorecard = OperatorScorecard.from_metrics(metrics)
        hr_verdict = self.hr.review_operator(scorecard, owner_input=owner_input)
        self.console.print(hr_verdict[:500] + "..." if len(hr_verdict) > 500 else hr_verdict)

        # 3. CMO growth plan
        self.console.print(Panel(
            "[yellow]CMO — client acquisition plan[/yellow]",
            title="Input 3", border_style="yellow",
        ))
        growth_plan = self.cmo.plan(metrics, owner_input=owner_input)
        growth_summary = (
            f"Posture: {growth_plan.posture}\n"
            f"Channels: {', '.join(growth_plan.channels)}\n"
            f"Target segments: {', '.join(growth_plan.target_segments)}\n"
            f"Messaging: {growth_plan.messaging}\n"
            f"Next steps: {'; '.join(growth_plan.next_steps)}"
        )
        self.console.print(growth_summary[:500] + "..." if len(growth_summary) > 500 else growth_summary)

        # 4. Innovation agenda
        self.console.print(Panel(
            "[magenta]Innovation agenda[/magenta]",
            title="Input 4", border_style="magenta",
        ))
        recent_decisions = [f"{d.actor}: {d.summary}" for d in state.decisions[-8:]]
        innovation_agenda = self.ceo.propose_innovation_agenda(
            metrics, recent_decisions=recent_decisions, owner_input=owner_input,
        )
        self.console.print(innovation_agenda[:500] + "..." if len(innovation_agenda) > 500 else innovation_agenda)

        # 5. Compliance summary from docs/compliance/
        self.console.print(Panel(
            "[red]DPO — compliance summary[/red]",
            title="Input 5", border_style="red",
        ))
        compliance_summary = self._gather_compliance_summary()
        self.console.print(compliance_summary[:500] + "..." if len(compliance_summary) > 500 else compliance_summary)

        # 6. Synthesize — BusinessPlanAgent
        self.console.print(Panel(
            "[bold green]Manager — synthesizing business plan[/bold green]",
            title="Synthesis", border_style="green",
        ))
        plan_content = self.business_planner.generate(
            state=state,
            metrics=metrics,
            quality_analysis=quality_analysis,
            hr_verdict=hr_verdict,
            growth_plan_summary=growth_summary,
            innovation_agenda=innovation_agenda,
            compliance_summary=compliance_summary,
            owner_input=owner_input,
        )

        path = self.business_planner.save_plan(plan_content)
        self.console.print(f"\n[green]Business plan saved to:[/green] {path}")

        # Log decision
        state.log_decision(
            actor="manager",
            summary="Business plan generated",
            rationale=f"Full business plan with inputs from QD, HR, CMO, DPO. Saved to {path}",
        )
        state.save()

        return path

    @staticmethod
    def _gather_compliance_summary() -> str:
        """Read compliance docs and summarize for the business plan."""
        docs_dir = Path(__file__).resolve().parents[2] / "docs" / "compliance"
        if not docs_dir.exists():
            return "Brak dokumentów compliance. DPO musi wygenerować dokumenty RODO/GDPR."

        parts = []
        risk_path = docs_dir / "risk_assessment.md"
        if risk_path.exists():
            content = risk_path.read_text(encoding="utf-8")
            # Extract just the risk table section
            if "## 2. Zidentyfikowane ryzyka" in content:
                start = content.find("## 2. Zidentyfikowane ryzyka")
                end = content.find("## 3. Macierz ryzyk")
                if end == -1:
                    end = len(content)
                parts.append("### Risk Assessment\n" + content[start:end].strip())

        privacy_path = docs_dir / "privacy_policy.md"
        if privacy_path.exists():
            parts.append("### Privacy Policy\nPrivacy policy (PL) wygenerowana. Wymaga uzupełnienia NIP/KRS po rejestracji firmy.")

        retention_path = docs_dir / "retention_policy.md"
        if retention_path.exists():
            parts.append("### Retention Policy\nPolityka retencji zdefiniowana: transkrypcje 90d, notatki 1r, raporty 2r, audyt 3r.")

        dpia_path = docs_dir / "dpia.md"
        if dpia_path.exists():
            parts.append("### DPIA\nDPIA przeprowadzone. Werdykt: warunkowa akceptacja po remediacji (health_consent, rejestracja, DPA).")

        reg_path = docs_dir / "registration_checklist.md"
        if reg_path.exists():
            parts.append("### Rejestracja firmy\nChecklista rejestracji JDG przygotowana. Wymaga działania właściciela (CEIDG, Profil Zaufany).")

        parts.append("### Status zgód seniorów")
        parts.append("- jadwiga-001: pełne zgody (transcribe, store, share, health_data, train) — PL")
        parts.append("- stefan-001: pełne zgody (transcribe, store, share, health_data, train) — PL")
        parts.append("- health_consent default: False (RODO Art. 9 compliant)")

        parts.append("### Otwarte pozycje compliance")
        parts.append("- [WYMAGA WŁAŚCICIELA] Rejestracja firmy (JDG w CEIDG)")
        parts.append("- [WYMAGA WŁAŚCICIELA] DPA z OpenRouter (Art. 28)")
        parts.append("- [WYMAGA WŁAŚCICIELA] Weryfikacja transferu danych poza EOG (SCCs)")

        return "\n\n".join(parts) if parts else "Brak dokumentów compliance."
