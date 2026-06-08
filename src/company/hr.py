"""HR agent — people operations for the AI workforce.

In this org the "employee" is the Operator. HR tracks the Operator's
performance over time (score trends across calls + training), computes a
plain competency read per quality axis, and issues a short performance verdict
with a recommendation (keep / coach / retrain). It complements the CEO (strategy)
and Quality Director (systemic quality) with a people-management lens.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from ..agents.base import BaseAgent
from .metrics import CompanyMetrics
from .state import KPI_AXES


# Competency bands for a 0-10 axis score.
def _band(score: float) -> str:
    if score >= 8.5:
        return "excellent"
    if score >= 7.0:
        return "solid"
    if score >= 5.5:
        return "needs coaching"
    return "underperforming"


@dataclass
class OperatorScorecard:
    """A deterministic competency read computed from metrics (no LLM)."""

    avg_scores: dict[str, float] = field(default_factory=dict)
    bands: dict[str, str] = field(default_factory=dict)
    trend_delta: dict[str, float] = field(default_factory=dict)  # latest - previous (training)
    weakest_axis: str = ""
    recommendation: str = ""  # keep | coach | retrain

    @classmethod
    def from_metrics(cls, metrics: CompanyMetrics) -> "OperatorScorecard":
        bands = {a: _band(metrics.avg_scores[a]) for a in KPI_AXES if a in metrics.avg_scores}
        trend_delta: dict[str, float] = {}
        if len(metrics.training_trend) == 2:
            prev, latest = metrics.training_trend
            for a in KPI_AXES:
                if a in prev and a in latest:
                    trend_delta[a] = round(latest[a] - prev[a], 1)
        weakest = metrics.weakest_axis() or ""
        rec = cls._recommend(metrics, weakest, trend_delta)
        return cls(
            avg_scores=dict(metrics.avg_scores),
            bands=bands,
            trend_delta=trend_delta,
            weakest_axis=weakest,
            recommendation=rec,
        )

    @staticmethod
    def _recommend(
        metrics: CompanyMetrics,
        weakest: str,
        trend_delta: dict[str, float],
    ) -> str:
        if not metrics.avg_scores:
            return "keep"
        low = metrics.avg_scores.get(weakest, 10.0) if weakest else 10.0
        declining = any(d <= -1.0 for d in trend_delta.values())
        if low < 5.5:
            return "retrain"
        if low < 7.0 or declining:
            return "coach"
        return "keep"


class HRAgent(BaseAgent):
    """Reviews the Operator's performance and writes a short verdict."""

    role = "hr"
    description = "Head of People for an elderly wellness call center. Reviews operator performance."

    def __init__(self, model: str | None = None):
        model = model or os.getenv("HR_MODEL") or os.getenv("SUPERVISOR_MODEL")
        super().__init__(model=model, temperature=0.3, max_tokens=600)

    @property
    def system_prompt(self) -> str:
        return """You are the Head of People at an AI-run elderly wellness call center.

The "employee" you review is the Operator agent. You are given a competency scorecard derived from its call + training scores across four axes (warmth, listening, info_quality, brevity), the recent trend, and a system recommendation (keep / coach / retrain).

Write a SHORT performance verdict (max ~100 words, plain prose) addressed to the Manager: name the operator's strongest and weakest area, comment on the trend, and endorse or adjust the recommendation. Be fair and specific. No preamble."""

    def review_operator(self, scorecard: OperatorScorecard) -> str:
        """Return a short HR verdict prose for the given scorecard."""
        if not scorecard.avg_scores:
            return "No performance data yet — operator has not completed enough calls to review."

        scores = ", ".join(f"{k}: {v} ({scorecard.bands.get(k, '?')})"
                            for k, v in scorecard.avg_scores.items())
        trend = ", ".join(f"{k}: {d:+}" for k, d in scorecard.trend_delta.items()) or "(no trend data)"
        prompt = f"""## Operator scorecard

Scores: {scores}
Trend (latest vs previous training): {trend}
Weakest axis: {scorecard.weakest_axis or 'n/a'}
System recommendation: {scorecard.recommendation}

Write your performance verdict now."""

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt},
        ]
        try:
            return self.chat(messages, temperature=0.3).strip()
        except Exception as e:  # noqa: BLE001
            return f"(HR verdict unavailable: {e}; system recommendation: {scorecard.recommendation})"
