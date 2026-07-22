"""Persistent company state for the autonomous AI org.

The company is modelled as a real organisation: it has a mission, a current
strategic directive (what to focus on next), a history of KPI snapshots, and an
append-only log of executive decisions. This is the shared, durable memory that
the executive agents (CEO, Quality Director, HR) read and write.

Stored at `data/company/state.json`.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DATA_DIR = Path(__file__).resolve().parents[2] / "data"
COMPANY_DIR = DATA_DIR / "company"
STATE_PATH = COMPANY_DIR / "state.json"

DEFAULT_MISSION = (
    "Provide warm, attentive daily wellness check-in calls to elderly people, "
    "keep their families informed, and continuously improve the quality of care."
)

# The four quality axes the whole company optimises for.
KPI_AXES = ("warmth", "listening", "info_quality", "brevity")
STAFFING_STAGES = ("light", "standard", "scale")
DEFAULT_STAFFING_STAGE = "standard"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Directive:
    """A strategic focus set by the CEO for the next operating period."""

    focus_metric: str = ""          # one of KPI_AXES, the weakest axis
    focus_skill: str = ""           # operator skill file to prioritise (e.g. 'farewell')
    rationale: str = ""             # why this focus, in plain language
    falsification_condition: str = ""  # warunek obalenia: when does this directive fail?
    owner_questions: list[str] = field(default_factory=list)  # questions CEO asks the owner
    set_at: str = field(default_factory=_now)
    set_by: str = "ceo"

    def is_empty(self) -> bool:
        return not (self.focus_metric or self.focus_skill)

    def to_operator_note(self) -> str:
        """Render the directive as a short instruction block for the Operator's
        prompt. Returns "" when no directive is set so callers can append safely."""
        if self.is_empty():
            return ""
        skill = f" (especially via the '{self.focus_skill}' skill)" if self.focus_skill else ""
        rationale = f" {self.rationale}" if self.rationale else ""
        return (
            "\n## Company priority this period\n\n"
            f"Leadership has set a company-wide focus on **{self.focus_metric or self.focus_skill}**"
            f"{skill}.{rationale} Give this extra attention during the call without "
            "neglecting warmth or the other essentials.\n"
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Directive":
        return cls(
            focus_metric=data.get("focus_metric", ""),
            focus_skill=data.get("focus_skill", ""),
            rationale=data.get("rationale", ""),
            falsification_condition=data.get("falsification_condition", ""),
            owner_questions=list(data.get("owner_questions", []) or []),
            set_at=data.get("set_at", _now()),
            set_by=data.get("set_by", "ceo"),
        )


@dataclass
class GrowthPlan:
    """The CMO's client-acquisition strategy for the next operating period."""

    posture: str = ""                                   # 'scale' | 'stabilize' | ''
    channels: list[str] = field(default_factory=list)   # where to find new clients
    target_segments: list[str] = field(default_factory=list)
    messaging: str = ""                                 # core value proposition
    next_steps: list[str] = field(default_factory=list)  # concrete actions
    set_at: str = field(default_factory=_now)
    set_by: str = "cmo"

    def is_empty(self) -> bool:
        return not (self.channels or self.next_steps or self.messaging)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GrowthPlan":
        return cls(
            posture=data.get("posture", ""),
            channels=list(data.get("channels", [])),
            target_segments=list(data.get("target_segments", [])),
            messaging=data.get("messaging", ""),
            next_steps=list(data.get("next_steps", [])),
            set_at=data.get("set_at", _now()),
            set_by=data.get("set_by", "cmo"),
        )


@dataclass
class Position:
    """One position in the company staffing plan."""

    title: str
    headcount: int = 1
    monthly_cost_pln: int = 0

    @property
    def monthly_total_pln(self) -> int:
        return self.headcount * self.monthly_cost_pln

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Position":
        return cls(
            title=str(data.get("title", "")),
            headcount=max(0, int(data.get("headcount", 0))),
            monthly_cost_pln=max(0, int(data.get("monthly_cost_pln", 0))),
        )


@dataclass
class StaffingPlan:
    """Headcount and payroll plan for the current operating period."""

    stage: str = DEFAULT_STAFFING_STAGE
    monthly_budget_pln: int = 0
    positions: list[Position] = field(default_factory=list)
    set_at: str = field(default_factory=_now)
    set_by: str = "board"

    @property
    def total_monthly_payroll_pln(self) -> int:
        return sum(p.monthly_total_pln for p in self.positions)

    @property
    def remaining_budget_pln(self) -> int:
        return self.monthly_budget_pln - self.total_monthly_payroll_pln

    @property
    def is_balanced(self) -> bool:
        return self.remaining_budget_pln >= 0

    def upsert_position(self, title: str, headcount: int, monthly_cost_pln: int) -> None:
        self.stage = "custom"
        normalized = title.strip().casefold()
        for pos in self.positions:
            if pos.title.casefold() == normalized:
                pos.headcount = max(0, headcount)
                pos.monthly_cost_pln = max(0, monthly_cost_pln)
                return
        self.positions.append(
            Position(
                title=title.strip(),
                headcount=max(0, headcount),
                monthly_cost_pln=max(0, monthly_cost_pln),
            )
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "StaffingPlan":
        stage = str(data.get("stage", DEFAULT_STAFFING_STAGE)).strip().lower()
        if stage not in (*STAFFING_STAGES, "custom"):
            stage = DEFAULT_STAFFING_STAGE
        return cls(
            stage=stage,
            monthly_budget_pln=max(0, int(data.get("monthly_budget_pln", 0))),
            positions=[Position.from_dict(p) for p in data.get("positions", [])],
            set_at=data.get("set_at", _now()),
            set_by=data.get("set_by", "board"),
        )

    @classmethod
    def preset(cls, stage: str = DEFAULT_STAFFING_STAGE, set_by: str = "board") -> "StaffingPlan":
        stage_normalized = stage.strip().lower()
        if stage_normalized not in STAFFING_STAGES:
            stage_normalized = DEFAULT_STAFFING_STAGE

        if stage_normalized == "light":
            budget = 162_000
            positions = [
                Position(title="Compliance & DPO Officer", headcount=1, monthly_cost_pln=13_000),
                Position(title="Quality Director", headcount=1, monthly_cost_pln=22_000),
                Position(title="Manager", headcount=1, monthly_cost_pln=18_000),
                Position(title="Supervisor", headcount=1, monthly_cost_pln=16_000),
                Position(title="Operator", headcount=1, monthly_cost_pln=12_000),
                Position(title="Training Engineer", headcount=1, monthly_cost_pln=17_000),
                Position(title="MLOps/SRE Engineer", headcount=1, monthly_cost_pln=15_000),
                Position(title="Customer Success Specialist", headcount=1, monthly_cost_pln=10_000),
                Position(title="Cybersecurity Officer", headcount=1, monthly_cost_pln=9_000),
                Position(title="Sprzedawca", headcount=1, monthly_cost_pln=14_000),
                Position(title="Księgowy", headcount=1, monthly_cost_pln=7_000),
            ]
        elif stage_normalized == "scale":
            budget = 312_000
            positions = [
                Position(title="Compliance & DPO Officer", headcount=1, monthly_cost_pln=13_000),
                Position(title="Quality Director", headcount=1, monthly_cost_pln=22_000),
                Position(title="HR Officer", headcount=1, monthly_cost_pln=16_000),
                Position(title="CMO", headcount=1, monthly_cost_pln=20_000),
                Position(title="Manager", headcount=1, monthly_cost_pln=18_000),
                Position(title="Supervisor", headcount=2, monthly_cost_pln=16_000),
                Position(title="Operator", headcount=4, monthly_cost_pln=12_000),
                Position(title="Training Engineer", headcount=2, monthly_cost_pln=17_000),
                Position(title="MLOps/SRE Engineer", headcount=2, monthly_cost_pln=15_000),
                Position(title="Customer Success Specialist", headcount=2, monthly_cost_pln=10_000),
                Position(title="Cybersecurity Officer", headcount=2, monthly_cost_pln=9_000),
                Position(title="Sprzedawca", headcount=2, monthly_cost_pln=14_000),
                Position(title="Księgowy", headcount=1, monthly_cost_pln=7_000),
            ]
        else:
            budget = 202_000
            positions = [
                Position(title="Compliance & DPO Officer", headcount=1, monthly_cost_pln=13_000),
                Position(title="Quality Director", headcount=1, monthly_cost_pln=22_000),
                Position(title="HR Officer", headcount=1, monthly_cost_pln=16_000),
                Position(title="CMO", headcount=1, monthly_cost_pln=20_000),
                Position(title="Manager", headcount=1, monthly_cost_pln=18_000),
                Position(title="Supervisor", headcount=1, monthly_cost_pln=16_000),
                Position(title="Operator", headcount=2, monthly_cost_pln=12_000),
                Position(title="Training Engineer", headcount=1, monthly_cost_pln=17_000),
                Position(title="MLOps/SRE Engineer", headcount=1, monthly_cost_pln=15_000),
                Position(title="Customer Success Specialist", headcount=1, monthly_cost_pln=10_000),
                Position(title="Cybersecurity Officer", headcount=1, monthly_cost_pln=9_000),
                Position(title="Sprzedawca", headcount=1, monthly_cost_pln=14_000),
                Position(title="Księgowy", headcount=1, monthly_cost_pln=7_000),
            ]

        return cls(
            stage=stage_normalized,
            monthly_budget_pln=budget,
            positions=positions,
            set_by=set_by,
        )


def _default_staffing_plan() -> StaffingPlan:
    return StaffingPlan.preset(DEFAULT_STAFFING_STAGE, set_by="board")


@dataclass
class KpiSnapshot:
    """A point-in-time picture of company-wide quality + activity."""

    date: str = field(default_factory=_now)
    avg_scores: dict[str, float] = field(default_factory=dict)
    n_calls: int = 0
    n_seniors: int = 0
    n_training_rounds: int = 0

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "KpiSnapshot":
        return cls(
            date=data.get("date", _now()),
            avg_scores=dict(data.get("avg_scores", {})),
            n_calls=int(data.get("n_calls", 0)),
            n_seniors=int(data.get("n_seniors", 0)),
            n_training_rounds=int(data.get("n_training_rounds", 0)),
        )


@dataclass
class Decision:
    """One entry in the company's append-only decision log."""

    date: str = field(default_factory=_now)
    actor: str = ""        # e.g. 'ceo', 'quality_director', 'hr'
    summary: str = ""
    rationale: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Decision":
        return cls(
            date=data.get("date", _now()),
            actor=data.get("actor", ""),
            summary=data.get("summary", ""),
            rationale=data.get("rationale", ""),
        )


@dataclass
class CompanyState:
    """Durable company memory. Load → mutate → save."""

    mission: str = DEFAULT_MISSION
    founded: str = field(default_factory=_now)
    directive: Directive = field(default_factory=Directive)
    growth_plan: GrowthPlan = field(default_factory=GrowthPlan)
    staffing_plan: StaffingPlan = field(default_factory=_default_staffing_plan)
    kpi_history: list[KpiSnapshot] = field(default_factory=list)
    decisions: list[Decision] = field(default_factory=list)

    # ---- Persistence ----

    @classmethod
    def load(cls, path: Path = STATE_PATH) -> "CompanyState":
        if not path.exists():
            return cls()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001 — corrupt file → start fresh, don't crash the company
            return cls()
        return cls(
            mission=data.get("mission", DEFAULT_MISSION),
            founded=data.get("founded", _now()),
            directive=Directive.from_dict(data.get("directive", {})),
            growth_plan=GrowthPlan.from_dict(data.get("growth_plan", {})),
            staffing_plan=(
                StaffingPlan.from_dict(data.get("staffing_plan", {}))
                if "staffing_plan" in data
                else _default_staffing_plan()
            ),
            kpi_history=[KpiSnapshot.from_dict(d) for d in data.get("kpi_history", [])],
            decisions=[Decision.from_dict(d) for d in data.get("decisions", [])],
        )

    def save(self, path: Path = STATE_PATH) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "mission": self.mission,
            "founded": self.founded,
            "directive": asdict(self.directive),
            "growth_plan": asdict(self.growth_plan),
            "staffing_plan": asdict(self.staffing_plan),
            "kpi_history": [asdict(s) for s in self.kpi_history],
            "decisions": [asdict(d) for d in self.decisions],
        }
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return path

    # ---- Mutations ----

    def set_growth_plan(self, plan: GrowthPlan) -> None:
        self.growth_plan = plan
        self.log_decision(
            actor=plan.set_by,
            summary=f"Growth plan ({plan.posture or 'n/a'}): "
                    f"{len(plan.channels)} channel(s), {len(plan.next_steps)} next step(s)",
            rationale=plan.messaging,
        )

    def set_directive(self, directive: Directive) -> None:
        self.directive = directive
        self.log_decision(
            actor=directive.set_by,
            summary=f"New directive: focus on {directive.focus_metric or 'n/a'}"
                    f" / skill '{directive.focus_skill or 'n/a'}'",
            rationale=directive.rationale,
        )

    def set_staffing_plan(self, plan: StaffingPlan) -> None:
        self.staffing_plan = plan
        status = "balanced" if plan.is_balanced else "over budget"
        self.log_decision(
            actor=plan.set_by,
            summary=(
                f"Staffing plan updated ({plan.stage}, {status}): {len(plan.positions)} position(s), "
                f"payroll {plan.total_monthly_payroll_pln} PLN / budget {plan.monthly_budget_pln} PLN"
            ),
            rationale=f"Remaining budget: {plan.remaining_budget_pln} PLN",
        )

    def apply_staffing_stage(self, stage: str, set_by: str = "board") -> StaffingPlan:
        plan = StaffingPlan.preset(stage=stage, set_by=set_by)
        self.set_staffing_plan(plan)
        return plan

    def record_snapshot(self, snapshot: KpiSnapshot) -> None:
        self.kpi_history.append(snapshot)

    def log_decision(self, actor: str, summary: str, rationale: str = "") -> None:
        self.decisions.append(Decision(actor=actor, summary=summary, rationale=rationale))

    # ---- Reads ----

    def latest_snapshot(self) -> KpiSnapshot | None:
        return self.kpi_history[-1] if self.kpi_history else None

    def previous_snapshot(self) -> KpiSnapshot | None:
        return self.kpi_history[-2] if len(self.kpi_history) >= 2 else None
