"""Quality Director agent — middle management between Supervisor and CEO.

The Supervisor reviews ONE call at a time. The Quality Director zooms out: it
reads the pool of recent quality issues across many calls/training rounds and
distills them into a few SYSTEMIC themes — recurring problems that no single
call review would surface. Its output feeds the CEO's strategic directive and
the Trainer's focus.
"""

from __future__ import annotations

import os

from ..agents.base import BaseAgent
from .metrics import CompanyMetrics


class QualityDirectorAgent(BaseAgent):
    """Finds recurring, systemic quality problems across many calls."""

    role = "quality_director"
    description = "Director of Quality for an elderly wellness call center. Finds systemic patterns."

    def __init__(self, model: str | None = None):
        model = model or os.getenv("QUALITY_DIRECTOR_MODEL") or os.getenv("SUPERVISOR_MODEL")
        super().__init__(model=model, temperature=0.3, max_tokens=900)

    @property
    def system_prompt(self) -> str:
        return """You are the Director of Quality at an AI-run elderly wellness call center.

Unlike the per-call Supervisor, you look ACROSS many calls to find SYSTEMIC patterns — problems that recur and therefore deserve company-wide attention.

You will be given the company's average scores, the recent score trend, and a pool of individual quality issues collected across many calls.

Write a SHORT analysis (plain prose, max ~150 words) that:
1. Names the 1-3 recurring themes you see in the issues (not one-offs).
2. States which quality axis each theme most hurts.
3. Notes any decline in the trend.

Be concrete and reference the actual issues. No preamble, no bullet headers like "Analysis:" — just the findings. This goes straight to the CEO."""

    def analyze(self, metrics: CompanyMetrics) -> str:
        """Return a short systemic-quality analysis as prose."""
        if not metrics.recent_issues and not metrics.avg_scores:
            return "No quality data yet — not enough calls or training rounds to find patterns."

        scores = ", ".join(f"{k}: {v}" for k, v in metrics.avg_scores.items()) or "no data"
        trend_lines = []
        for i, t in enumerate(metrics.training_trend):
            label = "previous" if i == 0 and len(metrics.training_trend) == 2 else "latest"
            trend_lines.append(f"  {label}: " + ", ".join(f"{k}: {v}" for k, v in t.items()))
        trend = "\n".join(trend_lines) or "  (no training history)"
        issues = "\n".join(f"- {i}" for i in metrics.recent_issues) or "- (none recorded)"

        prompt = f"""## Company average scores
{scores}

## Score trend (training)
{trend}

## Pool of recent quality issues (across many calls)
{issues}

Write your systemic analysis now."""

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt},
        ]
        try:
            return self.chat(messages, temperature=0.3).strip()
        except Exception as e:  # noqa: BLE001
            return f"(Quality Director analysis unavailable: {e})"
