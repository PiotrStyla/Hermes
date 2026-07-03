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

INNOVATION_TYPES = ("core", "adjacent", "moonshot")
INNOVATION_OWNERS = {
    "Quality Director",
    "CMO",
    "HR Officer",
    "Manager",
    "Supervisor",
    "Training Engineer",
    "MLOps/SRE Engineer",
    "Customer Success Specialist",
    "Compliance & DPO Officer",
}


class CEOAgent(BaseAgent):
    """Sets the company's single strategic focus for the next period."""

    role = "ceo"
    description = "Chief Executive of an elderly wellness call center. Sets strategy from KPIs."

    def __init__(self, model: str | None = None):
        model = model or os.getenv("CEO_MODEL") or os.getenv("SUPERVISOR_MODEL")
        super().__init__(model=model, temperature=0.6, max_tokens=2048)

    @property
    def system_prompt(self) -> str:
        return """You are the CEO of "Hermes", an AI-run wellness call center that phones elderly people daily, checks on their mood/health/safety, and reports to their families.

Your operators are graded each call on four axes (0-10):
- warmth — did the operator feel like a caring human?
- listening — did they reflect feelings and follow threads?
- info_quality — did they gather mood/health/safety info without sounding like a checklist?
- brevity — did the call stay ~under 5 minutes (~18 turns) and end gracefully?

Given the company's current KPIs, recent quality issues, the Quality Director's analysis, and explicit input from the owner, set ONE strategic directive for the next period. Be decisive — one focus only — but also creative and progressive: do not mechanically pick the same axis every time. Consider the owner's input a priority signal; if the owner points to a specific problem or opportunity, address it even if the raw KPIs would otherwise point elsewhere.

Respond with ONLY a JSON object, no prose, no fences:

{
  "focus_metric": "<one of: warmth | listening | info_quality | brevity>",
  "focus_skill": "<one of: greeting | mood-checkin | health-checkin | safety-check | active-listening | farewell>",
  "rationale": "2-3 sentences: why this is the priority now, referencing the data and owner input.",
  "falsification_condition": "One measurable sentence: if X does not rise by Y within Z days, this directive has failed and must be revised.",
  "owner_questions": ["3-5 strategic questions. Each question must identify a specific resource you need from the owner (decision, budget, data, priority, approval, contact) AND explain why the company cannot proceed autonomously without it. If the owner already answered the issue in their input, do not ask it again. Focus on what is truly blocking self-sufficient operation."]
}

Always include both falsification_condition and owner_questions. If the owner gave input, ask sharp, strategic follow-up questions about it — do not just repeat the input back. If the owner gave no input, use this field to ask the most important thing blocking autonomous action. Avoid repeating recent directives verbatim; if the last two directives used the same focus_metric, choose a different one this period."""

    @property
    def innovation_system_prompt(self) -> str:
        return """You are the CEO setting innovation bets for the next operating cycle.

You must propose exactly 3 initiatives:
- one CORE (improves current execution),
- one ADJACENT (expands value around current product),
- one MOONSHOT (high-upside experiment).

Each initiative must have a clear owner, measurable KPI, and a practical deadline.

Be creative and progressive: do not copy-paste the previous agenda. At least one initiative should feel like a genuine new bet or a bigger step forward. Consider the owner's input as a priority signal; if the owner flags a problem or opportunity, shape the initiatives around it.

Respond with ONLY a JSON object:
{
  "initiatives": [
    {
      "type": "core|adjacent|moonshot",
      "title": "short initiative name",
      "owner": "one board role",
      "kpi": "how success is measured",
      "deadline": "D+N or YYYY-MM-DD",
      "why_now": "one sentence"
    }
  ]
}

No prose outside JSON."""

    def decide(
        self,
        metrics: CompanyMetrics,
        quality_analysis: str = "",
        recent_ceo_directives: list[str] | None = None,
        owner_input: str = "",
    ) -> Directive:
        """Produce a strategic Directive from the company metrics."""
        prompt = self._build_prompt(metrics, quality_analysis, recent_ceo_directives, owner_input)
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt},
        ]
        try:
            raw = self.chat(messages, temperature=0.7)
            data = self._parse_json(raw)
        except Exception:  # noqa: BLE001 — never let strategy crash the company
            data = {}
        return self._to_directive(data, metrics, owner_input, recent_ceo_directives)

    def propose_innovation_agenda(
        self,
        metrics: CompanyMetrics,
        recent_decisions: list[str] | None = None,
        owner_input: str = "",
    ) -> str:
        prompt = self._build_innovation_prompt(metrics, recent_decisions, owner_input)
        messages = [
            {"role": "system", "content": self.innovation_system_prompt},
            {"role": "user", "content": prompt},
        ]
        try:
            raw = self.chat(messages, temperature=0.8, max_tokens=1600)
            data = self._parse_json(raw)
        except Exception:  # noqa: BLE001 — never let innovation planning crash governance
            data = {}
        return self._to_innovation_agenda(data, metrics)

    # ---- Internal ----

    def _build_prompt(
        self,
        metrics: CompanyMetrics,
        quality_analysis: str,
        recent_ceo_directives: list[str] | None = None,
        owner_input: str = "",
    ) -> str:
        scores = ", ".join(f"{k}: {v}" for k, v in metrics.avg_scores.items()) or "no data yet"
        trend_lines = []
        for i, t in enumerate(metrics.training_trend):
            label = "previous" if i == 0 and len(metrics.training_trend) == 2 else "latest"
            trend_lines.append(f"  {label}: " + ", ".join(f"{k}: {v}" for k, v in t.items()))
        trend = "\n".join(trend_lines) or "  (no training history)"
        issues = "\n".join(f"- {i}" for i in metrics.recent_issues[:10]) or "- (none recorded)"
        recent_directives = (
            "\n".join(f"- {d}" for d in (recent_ceo_directives or []))
            or "- (no previous directives)"
        )
        recent_focus_metrics = [
            d.split("/")[0].replace("New directive: focus on", "").strip()
            for d in (recent_ceo_directives or [])
        ]
        focus_history = ", ".join(recent_focus_metrics) or "(none yet)"
        owner_block = (
            f"## Owner input for this board meeting\n\n{owner_input}\n"
            if owner_input.strip()
            else "## Owner input\n\n(none provided — use owner_questions to ask what you need)."
        )

        return f"""## Company KPIs

Average scores (calls + training): {scores}
Seniors on file: {metrics.n_seniors} | Calls completed: {metrics.n_calls} | Training rounds: {metrics.n_training_rounds}

## Training score trend
{trend}

## Recent quality issues
{issues}

## Quality Director's analysis
{quality_analysis or "(no analysis provided)"}

## Recent CEO directives (avoid blind repetition)
{recent_directives}

## Recent directive focus metrics
{focus_history}

If the same focus_metric appears in the last two directives, you MUST choose a different one this period. The owner wants creativity and progress.

{owner_block}

Set the strategic directive now (JSON only)."""

    def _build_innovation_prompt(
        self,
        metrics: CompanyMetrics,
        recent_decisions: list[str] | None = None,
        owner_input: str = "",
    ) -> str:
        scores = ", ".join(f"{k}: {v}" for k, v in metrics.avg_scores.items()) or "no data yet"
        recent = "\n".join(f"- {d}" for d in (recent_decisions or [])[-8:]) or "- (none)"
        weakest = metrics.weakest_axis() or "unknown"
        owner_block = (
            f"## Owner input for this board meeting\n\n{owner_input}\n"
            if owner_input.strip()
            else "## Owner input\n\n(none provided — propose bold, useful initiatives anyway)."
        )
        return f"""## Current company state
Average scores: {scores}
Weakest axis: {weakest}
Seniors: {metrics.n_seniors}
Calls completed: {metrics.n_calls}
Training rounds: {metrics.n_training_rounds}

## Recent board decisions (do NOT repeat these verbatim)
{recent}

{owner_block}

Propose 3 fresh initiatives (core, adjacent, moonshot) now."""

    def _to_directive(
        self,
        data: dict[str, Any],
        metrics: CompanyMetrics,
        owner_input: str = "",
        recent_ceo_directives: list[str] | None = None,
    ) -> Directive:
        focus_metric = str(data.get("focus_metric", "")).strip()
        focus_skill = str(data.get("focus_skill", "")).strip()
        rationale = str(data.get("rationale", "")).strip()
        falsification_condition = str(data.get("falsification_condition", "")).strip()
        owner_questions = data.get("owner_questions") or []
        if isinstance(owner_questions, str):
            owner_questions = [owner_questions]
        owner_questions = [str(q).strip() for q in owner_questions if str(q).strip()]

        # Ground / fallback: if the model returned an invalid axis, use the
        # weakest measured axis so the company always has a valid directive.
        # Avoid mechanically repeating the same focus_metric as the last two
        # directives — even in the fallback path.
        recent_focus_metrics = [
            d.split("/")[0].replace("New directive: focus on", "").strip()
            for d in (recent_ceo_directives or [])
        ]
        if focus_metric not in KPI_AXES:
            focus_metric = metrics.weakest_axis() or "warmth"
        if len(recent_focus_metrics) >= 2 and all(f == focus_metric for f in recent_focus_metrics[-2:]):
            available_axes = [a for a in KPI_AXES if a != focus_metric]
            ranked = sorted(
                available_axes,
                key=lambda a: metrics.avg_scores.get(a, float("inf")),
            )
            focus_metric = ranked[0] if ranked else focus_metric
        if not focus_skill:
            focus_skill = AXIS_TO_SKILLS.get(focus_metric, ["active-listening"])[0]
        if not rationale:
            score = metrics.avg_scores.get(focus_metric)
            rationale = (
                f"'{focus_metric}' is the weakest axis"
                + (f" (avg {score})" if score is not None else "")
                + f"; prioritising the '{focus_skill}' skill to lift it."
            )
        if not owner_questions:
            if owner_input.strip():
                owner_questions = [
                    "Który z proponowanych kanałów autonomicznej akwizycji (udostępniane raporty dla rodzin, self-play A/B messagingu, wewnętrzne case study z rozmów) powinniśmy wdrożyć jako pierwszy i dlaczego?",
                    "Czy zgadzasz się, aby firma samodzielnie testowała warianty skryptów i komunikatów w symulacji, a następnie wdrażała wygraną wersję bez prośby o zgodę na każdą drobną zmianę?",
                    "Jakie są Twoje twarde limity (budżetowe, etyczne lub prawne) dla działań akwizycyjnych i komunikacyjnych prowadzonych wyłącznie przez AI bez kontaktu zewnętrznego?",
                ]
            else:
                owner_questions = [
                    "Jakie konkretne wyniki lub zmiany chciałbyś zobaczyć w ciągu najbliższych 7 dni, żeby firma mogła działać bez Twojego codziennego udziału?"
                ]
        if not falsification_condition:
            score = metrics.avg_scores.get(focus_metric, 0)
            threshold = round(float(score) + 0.3, 1)
            falsification_condition = (
                f"Jeśli '{focus_metric}' nie wzrośnie do {threshold} pkt w ciągu 14 dni, "
                "dyrektywa musi być zrewidowana."
            )
        return Directive(
            focus_metric=focus_metric,
            focus_skill=focus_skill,
            rationale=rationale,
            falsification_condition=falsification_condition,
            owner_questions=owner_questions,
            set_by="ceo",
        )

    def _to_innovation_agenda(self, data: dict[str, Any], metrics: CompanyMetrics) -> str:
        initiatives = self._normalize_initiatives(data)
        if len(initiatives) != 3:
            initiatives = self._fallback_initiatives(metrics)

        lines: list[str] = []
        for i, item in enumerate(initiatives, start=1):
            lines.append(
                f"{i}. [{item['type']}] {item['title']} | "
                f"Owner: {item['owner']} | KPI: {item['kpi']} | Deadline: {item['deadline']}"
            )
            lines.append(f"   Why now: {item['why_now']}")
        return "\n".join(lines)

    def _normalize_initiatives(self, data: dict[str, Any]) -> list[dict[str, str]]:
        out: list[dict[str, str]] = []
        for raw in data.get("initiatives", []) or []:
            kind = str(raw.get("type", "")).strip().lower()
            title = str(raw.get("title", "")).strip()
            owner = str(raw.get("owner", "")).strip()
            kpi = str(raw.get("kpi", "")).strip()
            why_now = str(raw.get("why_now", "")).strip()

            deadline_raw = raw.get("deadline")
            if deadline_raw is None and raw.get("deadline_days") is not None:
                try:
                    deadline_raw = f"D+{int(raw.get('deadline_days'))}"
                except (TypeError, ValueError):
                    deadline_raw = ""
            deadline = str(deadline_raw or "").strip()

            if kind not in INNOVATION_TYPES or not title or not kpi:
                continue
            if owner not in INNOVATION_OWNERS:
                owner = "Manager"
            if not deadline:
                deadline = "D+14"
            if not why_now:
                why_now = "Supports current strategy while improving execution speed."

            out.append(
                {
                    "type": kind,
                    "title": title,
                    "owner": owner,
                    "kpi": kpi,
                    "deadline": deadline,
                    "why_now": why_now,
                }
            )
        return out[:3]

    def _fallback_initiatives(self, metrics: CompanyMetrics) -> list[dict[str, str]]:
        weakest = metrics.weakest_axis() or "quality"
        return [
            {
                "type": "core",
                "title": f"{weakest} Recovery Sprint",
                "owner": "Quality Director",
                "kpi": f"Raise {weakest} by +0.4 within 14 days",
                "deadline": "D+14",
                "why_now": f"{weakest} is the current bottleneck for overall service quality.",
            },
            {
                "type": "adjacent",
                "title": "Family Feedback Loop v1",
                "owner": "Customer Success Specialist",
                "kpi": "Collect 20 family ratings and close top 3 pain points",
                "deadline": "D+21",
                "why_now": "Turns external feedback into faster product-learning cycles.",
            },
            {
                "type": "moonshot",
                "title": "Proactive Risk Signals Pilot",
                "owner": "MLOps/SRE Engineer",
                "kpi": "Detect 2 leading risk patterns before manual escalation",
                "deadline": "D+30",
                "why_now": "Creates a high-upside path toward proactive care operations.",
            },
        ]

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
