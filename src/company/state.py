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


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Directive:
    """A strategic focus set by the CEO for the next operating period."""

    focus_metric: str = ""          # one of KPI_AXES, the weakest axis
    focus_skill: str = ""           # operator skill file to prioritise (e.g. 'farewell')
    rationale: str = ""             # why this focus, in plain language
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

    def record_snapshot(self, snapshot: KpiSnapshot) -> None:
        self.kpi_history.append(snapshot)

    def log_decision(self, actor: str, summary: str, rationale: str = "") -> None:
        self.decisions.append(Decision(actor=actor, summary=summary, rationale=rationale))

    # ---- Reads ----

    def latest_snapshot(self) -> KpiSnapshot | None:
        return self.kpi_history[-1] if self.kpi_history else None

    def previous_snapshot(self) -> KpiSnapshot | None:
        return self.kpi_history[-2] if len(self.kpi_history) >= 2 else None
