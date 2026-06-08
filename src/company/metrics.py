"""Company-wide metrics aggregation.

Reads the artefacts the company already produces — per-senior `call_records.json`
and the self-play `data/training/report_*.json` files — and rolls them up into a
single company KPI picture plus a pool of recent quality issues. Pure logic, no
LLM calls, so it is fully unit-testable.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..seniors.store import SeniorStore
from .state import KPI_AXES, KpiSnapshot


DATA_DIR = Path(__file__).resolve().parents[2] / "data"
TRAINING_DIR = DATA_DIR / "training"


@dataclass
class CompanyMetrics:
    """Aggregated, company-level view of activity and quality."""

    n_seniors: int = 0
    n_calls: int = 0
    n_training_reports: int = 0
    n_training_rounds: int = 0
    # Average quality across the most recent calls/training combined.
    avg_scores: dict[str, float] = field(default_factory=dict)
    # Per-senior latest scores, for the board view.
    per_senior_latest: dict[str, dict[str, int]] = field(default_factory=dict)
    # Most recent supervisor issues across all calls (deduped, capped).
    recent_issues: list[str] = field(default_factory=list)
    # Latest two training-report average-score sets (trend signal).
    training_trend: list[dict[str, float]] = field(default_factory=list)

    def weakest_axis(self) -> str | None:
        """Return the lowest-scoring KPI axis, or None if no data."""
        if not self.avg_scores:
            return None
        return min(self.avg_scores, key=lambda k: self.avg_scores[k])

    def to_snapshot(self) -> KpiSnapshot:
        return KpiSnapshot(
            avg_scores=dict(self.avg_scores),
            n_calls=self.n_calls,
            n_seniors=self.n_seniors,
            n_training_rounds=self.n_training_rounds,
        )


class MetricsAggregator:
    """Rolls per-senior + training artefacts into a `CompanyMetrics`."""

    def __init__(
        self,
        store: SeniorStore | None = None,
        training_dir: Path = TRAINING_DIR,
        max_issues: int = 20,
    ):
        self.store = store or SeniorStore()
        self.training_dir = training_dir
        self.max_issues = max_issues

    def aggregate(self) -> CompanyMetrics:
        senior_ids = self.store.list_ids()
        per_senior_latest: dict[str, dict[str, int]] = {}
        all_score_sets: list[dict[str, float]] = []
        n_calls = 0

        for sid in senior_ids:
            records = self.store.list_call_records(sid)
            n_calls += len(records)
            if records:
                latest = records[-1].get("scores", {}) or {}
                if latest:
                    per_senior_latest[sid] = {k: int(v) for k, v in latest.items()}
                for rec in records:
                    scores = rec.get("scores", {}) or {}
                    if scores:
                        all_score_sets.append({k: float(v) for k, v in scores.items()})

        training_reports = self._load_training_reports()
        n_training_rounds = sum(int(r.get("rounds", 0)) for r in training_reports)
        training_trend = [
            {k: float(v) for k, v in (r.get("average_scores", {}) or {}).items()}
            for r in training_reports[-2:]
        ]
        for r in training_reports:
            avg = r.get("average_scores", {}) or {}
            if avg:
                all_score_sets.append({k: float(v) for k, v in avg.items()})

        avg_scores = self._mean_scores(all_score_sets)
        recent_issues = self._collect_issues(senior_ids, training_reports)

        return CompanyMetrics(
            n_seniors=len(senior_ids),
            n_calls=n_calls,
            n_training_reports=len(training_reports),
            n_training_rounds=n_training_rounds,
            avg_scores=avg_scores,
            per_senior_latest=per_senior_latest,
            recent_issues=recent_issues,
            training_trend=training_trend,
        )

    # ---- Internal ----

    def _load_training_reports(self) -> list[dict[str, Any]]:
        if not self.training_dir.exists():
            return []
        reports: list[dict[str, Any]] = []
        for path in sorted(self.training_dir.glob("report_*.json")):
            try:
                reports.append(json.loads(path.read_text(encoding="utf-8")))
            except Exception:  # noqa: BLE001 — skip corrupt reports
                continue
        return reports

    @staticmethod
    def _mean_scores(score_sets: list[dict[str, float]]) -> dict[str, float]:
        if not score_sets:
            return {}
        out: dict[str, float] = {}
        for axis in KPI_AXES:
            vals = [s[axis] for s in score_sets if axis in s]
            if vals:
                out[axis] = round(sum(vals) / len(vals), 1)
        return out

    def _collect_issues(
        self,
        senior_ids: list[str],
        training_reports: list[dict[str, Any]],
    ) -> list[str]:
        """Pull recent supervisor issues from training reports (per-call issues
        are not persisted to disk today, so training reports are the source).
        Deduped, most-recent-first, capped at `max_issues`."""
        issues: list[str] = []
        for report in reversed(training_reports):  # newest first
            for rd in reversed(report.get("rounds_detail", []) or []):
                for issue in rd.get("issues", []) or []:
                    if issue not in issues:
                        issues.append(issue)
                        if len(issues) >= self.max_issues:
                            return issues
        return issues
