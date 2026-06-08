"""CEO agent — the top of the org chart.

The CEO reads the company-wide KPI picture (from `MetricsAggregator`) plus the
Quality Director's systemic analysis, and sets ONE strategic directive for the
next operating period: which quality axis and which operator skill the company
should prioritise, with a plain-language rationale. The directive is the lever
that governs the otherwise-unsupervised self-improvement loop.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any

from ..agents.base import BaseAgent
from .metrics import CompanyMetrics
from .state import KPI_AXES, Directive


# Map each quality axis to the operator skills most responsible for it, so the
# CEO's focus_metric can be grounded in a concrete skill to improve.
AXIS_TO_SKILLS = {
    "warmth": ["greeting", "active-listening", "mood-checkin"],
    "listening": ["active-listening", "mood-checkin"],
    "info_quality": ["health-checkin", "safety-check"],
    "brevity": ["farewell", "greeting"],
}


class CEOAgent(BaseAgent):
    """Sets the company's single strategic focus for the next period."""

    role = "ceo"
    description = "Chief Executive of an elderly wellness call center. Sets strategy from KPIs."

    def __init__(self, model: str | None = None):
        model = model or os.getenv("CEO_MODEL") or os.getenv("SUPERVISOR_MODEL")
        super().__init__(model=model, temperature=0.3, max_tokens=900)

    @property
    def system_prompt(self) -> str:
        return """You are the CEO of "Hermes", an AI-run wellness call center that phones elderly people daily, checks on their mood/health/safety, and reports to their families.

Your operators are graded each call on four axes (0-10):
- warmth — did the operator feel like a caring human?
- listening — did they reflect feelings and follow threads?
- info_quality — did they gather mood/health/safety info without sounding like a checklist?
- brevity — did the call stay ~under 5 minutes (~18 turns) and end gracefully?

Given the company's current KPIs, recent quality issues, and the Quality Director's analysis, set ONE strategic directive for the next period: the single weakest axis to fix and the single operator skill to prioritise improving.

Respond with ONLY a JSON object, no prose, no fences:

{
  "focus_metric": "<one of: warmth | listening | info_quality | brevity>",
  "focus_skill": "<one of: greeting | mood-checkin | health-checkin | safety-check | active-listening | farewell>",
  "rationale": "2-3 sentences: why this is the priority now, referencing the data."
}

Pick the focus_metric that is genuinely weakest or declining. Pick a focus_skill that plausibly moves that metric. Be decisive — one focus only."""

    def decide(
        self,
        metrics: CompanyMetrics,
        quality_analysis: str = "",
    ) -> Directive:
        """Produce a strategic Directive from the company metrics."""
        prompt = self._build_prompt(metrics, quality_analysis)
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt},
        ]
        try:
            raw = self.chat(messages, temperature=0.3)
            data = self._parse_json(raw)
        except Exception:  # noqa: BLE001 — never let strategy crash the company
            data = {}
        return self._to_directive(data, metrics)

    # ---- Internal ----

    def _build_prompt(self, metrics: CompanyMetrics, quality_analysis: str) -> str:
        scores = ", ".join(f"{k}: {v}" for k, v in metrics.avg_scores.items()) or "no data yet"
        trend_lines = []
        for i, t in enumerate(metrics.training_trend):
            label = "previous" if i == 0 and len(metrics.training_trend) == 2 else "latest"
            trend_lines.append(f"  {label}: " + ", ".join(f"{k}: {v}" for k, v in t.items()))
        trend = "\n".join(trend_lines) or "  (no training history)"
        issues = "\n".join(f"- {i}" for i in metrics.recent_issues[:10]) or "- (none recorded)"

        return f"""## Company KPIs

Average scores (calls + training): {scores}
Seniors on file: {metrics.n_seniors} | Calls completed: {metrics.n_calls} | Training rounds: {metrics.n_training_rounds}

## Training score trend
{trend}

## Recent quality issues
{issues}

## Quality Director's analysis
{quality_analysis or "(no analysis provided)"}

Set the strategic directive now (JSON only)."""

    def _to_directive(self, data: dict[str, Any], metrics: CompanyMetrics) -> Directive:
        focus_metric = str(data.get("focus_metric", "")).strip()
        focus_skill = str(data.get("focus_skill", "")).strip()
        rationale = str(data.get("rationale", "")).strip()

        # Ground / fallback: if the model returned an invalid axis, use the
        # weakest measured axis so the company always has a valid directive.
        if focus_metric not in KPI_AXES:
            focus_metric = metrics.weakest_axis() or "warmth"
        if not focus_skill:
            focus_skill = AXIS_TO_SKILLS.get(focus_metric, ["active-listening"])[0]
        if not rationale:
            score = metrics.avg_scores.get(focus_metric)
            rationale = (
                f"'{focus_metric}' is the weakest axis"
                + (f" (avg {score})" if score is not None else "")
                + f"; prioritising the '{focus_skill}' skill to lift it."
            )
        return Directive(
            focus_metric=focus_metric,
            focus_skill=focus_skill,
            rationale=rationale,
            set_by="ceo",
        )

    @staticmethod
    def _parse_json(text: str) -> dict[str, Any]:
        text = text.strip()
        fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, re.DOTALL)
        if fence:
            text = fence.group(1)
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end != -1 and end > start:
            text = text[start : end + 1]
        return json.loads(text)
