"""Tests for the company executive layer — pure-logic parts (no LLM/network).

Covers CompanyState persistence, MetricsAggregator roll-up, and the
deterministic OperatorScorecard. LLM-driven agents (CEO/QD/HR prose) require a
live client and are left for integration testing.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.company.metrics import CompanyMetrics, MetricsAggregator
from src.company.ceo import CEOAgent
from src.company.hr import OperatorScorecard
from src.company.cmo import CMOAgent, SCALE_QUALITY_THRESHOLD
from src.company.runner import BoardMeetingResult, CompanyRunner
from src.company.state import (
    CompanyState,
    Directive,
    GrowthPlan,
    KpiSnapshot,
    Position,
    StaffingPlan,
)
from src.seniors.store import SeniorStore


# ---- CompanyState persistence ----

class TestCompanyState:
    def test_load_missing_returns_default(self, tmp_path: Path) -> None:
        state = CompanyState.load(tmp_path / "nope.json")
        assert state.mission
        assert state.directive.is_empty()
        assert state.kpi_history == []

    def test_save_then_load_roundtrip(self, tmp_path: Path) -> None:
        path = tmp_path / "state.json"
        state = CompanyState()
        state.set_directive(Directive(focus_metric="brevity", focus_skill="farewell", rationale="too long"))
        state.record_snapshot(KpiSnapshot(avg_scores={"brevity": 6.1}, n_calls=3, n_seniors=2))
        state.save(path)

        loaded = CompanyState.load(path)
        assert loaded.directive.focus_metric == "brevity"
        assert loaded.directive.focus_skill == "farewell"
        assert loaded.latest_snapshot().n_calls == 3
        # set_directive also logs a decision.
        assert any(d.actor == "ceo" for d in loaded.decisions)

    def test_corrupt_file_falls_back_to_default(self, tmp_path: Path) -> None:
        path = tmp_path / "state.json"
        path.write_text("{not valid json", encoding="utf-8")
        state = CompanyState.load(path)
        assert state.directive.is_empty()

    def test_previous_snapshot(self, tmp_path: Path) -> None:
        state = CompanyState()
        assert state.previous_snapshot() is None
        state.record_snapshot(KpiSnapshot(n_calls=1))
        assert state.previous_snapshot() is None
        state.record_snapshot(KpiSnapshot(n_calls=2))
        assert state.previous_snapshot().n_calls == 1
        assert state.latest_snapshot().n_calls == 2


# ---- MetricsAggregator ----

def _make_senior(base: Path, sid: str, score_sets: list[dict]) -> None:
    d = base / sid
    d.mkdir(parents=True)
    (d / "profile.json").write_text(json.dumps({"id": sid, "name": sid, "age": 70}), encoding="utf-8")
    records = [{"date": f"2026-01-0{i+1}T10:00:00", "scores": s} for i, s in enumerate(score_sets)]
    (d / "call_records.json").write_text(json.dumps(records), encoding="utf-8")


def _make_training_report(tdir: Path, name: str, avg: dict, rounds: int, issues: list[str]) -> None:
    tdir.mkdir(parents=True, exist_ok=True)
    payload = {
        "rounds": rounds,
        "average_scores": avg,
        "rounds_detail": [{"round": 1, "issues": issues}],
    }
    (tdir / name).write_text(json.dumps(payload), encoding="utf-8")


class TestMetricsAggregator:
    def test_empty_company(self, tmp_path: Path) -> None:
        store = SeniorStore(base_dir=tmp_path / "seniors")
        agg = MetricsAggregator(store=store, training_dir=tmp_path / "training")
        m = agg.aggregate()
        assert m.n_seniors == 0
        assert m.n_calls == 0
        assert m.avg_scores == {}
        assert m.weakest_axis() is None

    def test_rolls_up_seniors_and_training(self, tmp_path: Path) -> None:
        seniors = tmp_path / "seniors"
        training = tmp_path / "training"
        _make_senior(seniors, "a-001", [
            {"warmth": 8, "listening": 8, "info_quality": 6, "brevity": 6},
        ])
        _make_senior(seniors, "b-001", [
            {"warmth": 9, "listening": 7, "info_quality": 7, "brevity": 5},
        ])
        _make_training_report(training, "report_1.json",
                              {"warmth": 8, "listening": 7, "info_quality": 6, "brevity": 6},
                              rounds=10, issues=["call too long"])

        agg = MetricsAggregator(store=SeniorStore(base_dir=seniors), training_dir=training)
        m = agg.aggregate()
        assert m.n_seniors == 2
        assert m.n_calls == 2
        assert m.n_training_reports == 1
        assert m.n_training_rounds == 10
        # brevity is the weakest axis given the inputs.
        assert m.weakest_axis() == "brevity"
        assert "a-001" in m.per_senior_latest
        assert "call too long" in m.recent_issues

    def test_to_snapshot(self, tmp_path: Path) -> None:
        seniors = tmp_path / "seniors"
        _make_senior(seniors, "a-001", [{"warmth": 8, "brevity": 6}])
        agg = MetricsAggregator(store=SeniorStore(base_dir=seniors), training_dir=tmp_path / "t")
        snap = agg.aggregate().to_snapshot()
        assert isinstance(snap, KpiSnapshot)
        assert snap.n_seniors == 1

    def test_rolling_window_ignores_ancient_training(self, tmp_path: Path) -> None:
        seniors = tmp_path / "seniors"
        training = tmp_path / "training"
        _make_senior(seniors, "a-001", [{"warmth": 8, "listening": 8, "info_quality": 8, "brevity": 8}])
        # Old reports with low info_quality; newer reports with high info_quality.
        _make_training_report(training, "report_1.json", {"warmth": 5, "info_quality": 2}, rounds=10, issues=["old"])
        _make_training_report(training, "report_2.json", {"warmth": 5, "info_quality": 2}, rounds=10, issues=["old"])
        _make_training_report(training, "report_3.json", {"warmth": 5, "info_quality": 2}, rounds=10, issues=["old"])
        _make_training_report(training, "report_4.json", {"warmth": 9, "info_quality": 9}, rounds=10, issues=["new"])
        _make_training_report(training, "report_5.json", {"warmth": 9, "info_quality": 9}, rounds=10, issues=["new"])
        _make_training_report(training, "report_6.json", {"warmth": 9, "info_quality": 9}, rounds=10, issues=["new"])

        agg = MetricsAggregator(
            store=SeniorStore(base_dir=seniors),
            training_dir=training,
            training_window=3,
        )
        m = agg.aggregate()
        # Windowed KPI should be pulled up by the recent reports, not dragged down by the old ones.
        assert m.avg_scores["info_quality"] >= 8.0
        # But the full historical count is still preserved.
        assert m.n_training_reports == 6
        assert m.n_training_rounds == 60


# ---- OperatorScorecard (deterministic recommendation) ----

class TestOperatorScorecard:
    def test_keep_when_all_solid(self) -> None:
        m = CompanyMetrics(avg_scores={"warmth": 8, "listening": 8, "info_quality": 7.5, "brevity": 7.2})
        sc = OperatorScorecard.from_metrics(m)
        assert sc.recommendation == "keep"

    def test_coach_when_an_axis_below_seven(self) -> None:
        m = CompanyMetrics(avg_scores={"warmth": 8, "listening": 8, "info_quality": 7, "brevity": 6.2})
        sc = OperatorScorecard.from_metrics(m)
        assert sc.recommendation == "coach"
        assert sc.weakest_axis == "brevity"

    def test_retrain_when_axis_very_low(self) -> None:
        m = CompanyMetrics(avg_scores={"warmth": 5, "listening": 4.8, "info_quality": 6, "brevity": 6})
        sc = OperatorScorecard.from_metrics(m)
        assert sc.recommendation == "retrain"

    def test_coach_on_decline_even_if_scores_ok(self) -> None:
        m = CompanyMetrics(
            avg_scores={"warmth": 8, "listening": 8, "info_quality": 7.5, "brevity": 7.5},
            training_trend=[
                {"warmth": 9, "brevity": 9},
                {"warmth": 8, "brevity": 7.5},  # brevity dropped 1.5
            ],
        )
        sc = OperatorScorecard.from_metrics(m)
        assert sc.trend_delta["brevity"] == -1.5
        assert sc.recommendation == "coach"

    def test_empty_metrics_keep(self) -> None:
        sc = OperatorScorecard.from_metrics(CompanyMetrics())
        assert sc.recommendation == "keep"
        assert sc.avg_scores == {}


# ---- Directive → Operator loop closure ----

class TestDirectiveOperatorNote:
    def test_empty_directive_produces_no_note(self) -> None:
        assert Directive().to_operator_note() == ""

    def test_note_mentions_metric_and_skill(self) -> None:
        note = Directive(
            focus_metric="brevity",
            focus_skill="farewell",
            rationale="Calls run too long.",
        ).to_operator_note()
        assert "brevity" in note
        assert "farewell" in note
        assert "Calls run too long." in note
        assert note.startswith("\n## Company priority")

    def test_operator_prompt_includes_directive(self, sample_senior_profile) -> None:
        from src.agents.operator import OperatorAgent

        op = OperatorAgent()
        op.directive_note = Directive(
            focus_metric="info_quality", focus_skill="health-checkin",
            rationale="Weakest axis.",
        ).to_operator_note()
        prompt = op.build_system_prompt(sample_senior_profile, learnings="")
        assert "Company priority this period" in prompt
        assert "info_quality" in prompt

    def test_operator_prompt_clean_without_directive(self, sample_senior_profile) -> None:
        from src.agents.operator import OperatorAgent

        op = OperatorAgent()  # directive_note defaults to ""
        prompt = op.build_system_prompt(sample_senior_profile, learnings="")
        assert "Company priority this period" not in prompt


# ---- GrowthPlan persistence ----

class TestGrowthPlanState:
    def test_empty_plan(self) -> None:
        assert GrowthPlan().is_empty()
        assert not GrowthPlan(channels=["x"]).is_empty()

    def test_growth_plan_roundtrip(self, tmp_path: Path) -> None:
        path = tmp_path / "state.json"
        state = CompanyState()
        state.set_growth_plan(GrowthPlan(
            posture="scale",
            channels=["GP clinics", "senior clubs"],
            target_segments=["adult children"],
            messaging="Peace of mind.",
            next_steps=["Call 3 clinics"],
        ))
        state.save(path)

        loaded = CompanyState.load(path)
        assert loaded.growth_plan.posture == "scale"
        assert "GP clinics" in loaded.growth_plan.channels
        assert any(d.actor == "cmo" for d in loaded.decisions)


class TestStaffingPlanState:
    def test_default_staffing_has_new_roles_and_balanced_budget(self) -> None:
        state = CompanyState()
        plan = state.staffing_plan

        titles = {p.title for p in plan.positions}
        assert "Compliance & DPO Officer" in titles
        assert "MLOps/SRE Engineer" in titles
        assert "Customer Success Specialist" in titles
        assert "Cybersecurity Officer" in titles
        assert "Księgowy" in titles
        assert plan.monthly_budget_pln == 220_000
        assert plan.total_monthly_payroll_pln == 215_000
        assert plan.remaining_budget_pln == 5_000
        assert plan.is_balanced

    def test_staffing_roundtrip(self, tmp_path: Path) -> None:
        path = tmp_path / "state.json"
        state = CompanyState()
        state.set_staffing_plan(StaffingPlan(
            monthly_budget_pln=50_000,
            positions=[
                Position(title="Cybersecurity Officer", headcount=1, monthly_cost_pln=9_000),
                Position(title="Księgowy", headcount=1, monthly_cost_pln=7_000),
            ],
            set_by="board",
        ))
        state.save(path)

        loaded = CompanyState.load(path)
        assert loaded.staffing_plan.monthly_budget_pln == 50_000
        assert loaded.staffing_plan.total_monthly_payroll_pln == 16_000
        assert loaded.staffing_plan.remaining_budget_pln == 34_000
        assert any(d.actor == "board" and "Staffing plan updated" in d.summary for d in loaded.decisions)

    @pytest.mark.parametrize(
        ("stage", "budget", "payroll"),
        [
            ("light", 180_000, 167_000),
            ("standard", 220_000, 215_000),
            ("scale", 320_000, 306_000),
        ],
    )
    def test_stage_presets_are_balanced(self, stage: str, budget: int, payroll: int) -> None:
        plan = StaffingPlan.preset(stage)
        assert plan.stage == stage
        assert plan.monthly_budget_pln == budget
        assert plan.total_monthly_payroll_pln == payroll
        assert plan.is_balanced

    def test_upsert_switches_stage_to_custom(self) -> None:
        plan = StaffingPlan.preset("standard")
        assert plan.stage == "standard"
        plan.upsert_position("Operator", 3, 12_000)
        assert plan.stage == "custom"

    def test_apply_staffing_stage_updates_state(self) -> None:
        state = CompanyState()
        state.apply_staffing_stage("light", set_by="board")
        assert state.staffing_plan.stage == "light"
        assert state.staffing_plan.monthly_budget_pln == 180_000
        assert any("light" in d.summary for d in state.decisions)


# ---- CMOAgent deterministic fallback (no network) ----

class TestCMOFallback:
    def test_stabilize_when_quality_low(self) -> None:
        cmo = CMOAgent()
        m = CompanyMetrics(
            n_seniors=2, n_calls=5,
            avg_scores={"warmth": 6, "listening": 6, "info_quality": 5, "brevity": 6},
        )
        # data={} simulates an LLM failure → pure fallback path.
        plan = cmo._to_plan({}, m)
        assert plan.posture == "stabilize"
        assert plan.channels  # never empty
        assert plan.next_steps
        assert plan.messaging

    def test_scale_when_quality_high(self) -> None:
        cmo = CMOAgent()
        m = CompanyMetrics(
            n_seniors=10, n_calls=100,
            avg_scores={"warmth": 9, "listening": 8.5, "info_quality": 8, "brevity": 8},
        )
        plan = cmo._to_plan({}, m)
        assert plan.posture == "scale"
        assert len(plan.channels) >= 3

    def test_threshold_boundary(self) -> None:
        cmo = CMOAgent()
        scores = {a: SCALE_QUALITY_THRESHOLD for a in ("warmth", "listening", "info_quality", "brevity")}
        plan = cmo._to_plan({}, CompanyMetrics(avg_scores=scores))
        assert plan.posture == "scale"

    def test_respects_valid_llm_output(self) -> None:
        cmo = CMOAgent()
        m = CompanyMetrics(avg_scores={"warmth": 9, "listening": 9, "info_quality": 9, "brevity": 9})
        data = {
            "posture": "scale",
            "channels": ["Partnership with NFZ"],
            "target_segments": ["seg"],
            "messaging": "msg",
            "next_steps": ["step"],
        }
        plan = cmo._to_plan(data, m)
        assert plan.channels == ["Partnership with NFZ"]
        assert plan.messaging == "msg"

    def test_invalid_posture_falls_back(self) -> None:
        cmo = CMOAgent()
        m = CompanyMetrics(avg_scores={"warmth": 6, "listening": 6, "info_quality": 6, "brevity": 6})
        plan = cmo._to_plan({"posture": "nonsense"}, m)
        assert plan.posture == "stabilize"


class TestBoardReportGeneration:
    def test_save_board_report_writes_markdown(self, tmp_path: Path) -> None:
        runner = CompanyRunner(reports_dir=tmp_path / "reports")
        result = BoardMeetingResult(
            metrics=CompanyMetrics(
                n_seniors=2,
                n_calls=7,
                n_training_rounds=260,
                avg_scores={
                    "warmth": 8.3,
                    "listening": 7.7,
                    "info_quality": 6.6,
                    "brevity": 7.2,
                },
            ),
            quality_analysis="Systemic issue: info_quality.",
            hr_verdict="Recommendation: coach.",
            directive=Directive(
                focus_metric="info_quality",
                focus_skill="health-checkin",
                rationale="Weakest axis.",
                set_at="2026-06-19T10:00:00+02:00",
            ),
            growth_plan=GrowthPlan(
                posture="scale",
                channels=["GP clinics"],
                next_steps=["Contact 3 clinics"],
            ),
            innovation_agenda="1. [core] Recovery Sprint | Owner: Quality Director | KPI: +0.4 | Deadline: D+14",
        )

        report_path = runner._save_board_report(result, CompanyState())
        assert report_path.exists()
        assert report_path.name == "board_2026-06-19_10-00.md"

        content = report_path.read_text(encoding="utf-8")
        assert "# Executive Board Report" in content
        assert "## KPI Snapshot" in content
        assert "- info_quality: 6.6" in content
        assert "## CEO Directive" in content
        assert "- Focus metric: info_quality" in content
        assert "## Growth Plan" in content
        assert "GP clinics" in content
        assert "## Innovation Agenda" in content
        assert "Recovery Sprint" in content


class TestCEOInnovation:
    def test_build_prompt_includes_recent_directives(self) -> None:
        ceo = CEOAgent()
        prompt = ceo._build_prompt(
            CompanyMetrics(avg_scores={"warmth": 8.0}),
            quality_analysis="qa",
            recent_ceo_directives=["New directive: focus on brevity / skill 'farewell'"],
        )
        assert "Recent CEO directives" in prompt
        assert "focus on brevity" in prompt

    def test_innovation_fallback_produces_three_tracks(self) -> None:
        ceo = CEOAgent()
        metrics = CompanyMetrics(avg_scores={"warmth": 8.0, "info_quality": 6.1})
        agenda = ceo._to_innovation_agenda({}, metrics)
        assert "[core]" in agenda
        assert "[adjacent]" in agenda
        assert "[moonshot]" in agenda

    def test_directive_fallback_asks_autonomy_questions_with_owner_input(self) -> None:
        ceo = CEOAgent()
        metrics = CompanyMetrics(avg_scores={"warmth": 8, "listening": 8, "info_quality": 6, "brevity": 7})
        directive = ceo._to_directive({}, metrics, owner_input="Firma ma być całkowicie autonomiczna.")
        assert len(directive.owner_questions) >= 3
        assert all("?" in q for q in directive.owner_questions)
        assert any("autonomic" in q or "samodzielnie" in q or "AI" in q or "zewnętrzn" in q for q in directive.owner_questions)

    def test_directive_fallback_is_generic_without_owner_input(self) -> None:
        ceo = CEOAgent()
        metrics = CompanyMetrics(avg_scores={"warmth": 8, "listening": 8, "info_quality": 6, "brevity": 7})
        directive = ceo._to_directive({}, metrics)
        assert len(directive.owner_questions) >= 1
        assert "bez Twojego codziennego udziału" in directive.owner_questions[0]

    def test_directive_fallback_avoids_third_repeat(self) -> None:
        ceo = CEOAgent()
        metrics = CompanyMetrics(avg_scores={"warmth": 8, "listening": 8, "info_quality": 6, "brevity": 7})
        recent = [
            "New directive: focus on info_quality / skill 'health-checkin'",
            "New directive: focus on info_quality / skill 'health-checkin'",
        ]
        directive = ceo._to_directive({}, metrics, recent_ceo_directives=recent)
        assert directive.focus_metric != "info_quality"
        # The second-weakest axis should be chosen (brevity at 7).
        assert directive.focus_metric == "brevity"
