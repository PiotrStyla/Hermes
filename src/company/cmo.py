"""CMO agent — Chief Marketing Officer / client acquisition strategist.

The CMO answers the question the internal quality org never asks: *where do new
clients come from?* It reads the company's state (how many seniors we serve, how
good our quality is) and produces a GrowthPlan — acquisition channels, target
segments, core messaging, and concrete next steps.

Crucially it ties growth to quality: if call quality is weak it recommends a
"stabilize" posture (fix the product before scaling); if quality is solid it
recommends a "scale" posture and leans into acquisition. A deterministic
fallback guarantees a usable plan even with no LLM credits.
"""

from __future__ import annotations

import json
import os
import re
import statistics
from typing import Any

from ..agents.base import BaseAgent
from .metrics import CompanyMetrics
from .state import GrowthPlan


# Quality bar above which the company should lean into growth.
SCALE_QUALITY_THRESHOLD = 7.5

# Grounded default channels for the Polish elderly-care market (fallback).
_DEFAULT_CHANNELS = [
    "Przychodnie POZ i lekarze rodzinni (ulotki, polecenia)",
    "Domy i kluby seniora oraz Uniwersytety Trzeciego Wieku",
    "Parafie i organizacje kościelne",
    "Grupy i fora dla opiekunów rodzinnych (Facebook, lokalne)",
    "Partnerstwa z MOPS/OPS i programami NFZ dla seniorów",
    "Program poleceń dla rodzin obecnych klientów",
]
_DEFAULT_SEGMENTS = [
    "Dorosłe dzieci seniorów mieszkające daleko od rodziców",
    "Samotni seniorzy 75+ mieszkający samodzielnie",
]


class CMOAgent(BaseAgent):
    """Produces a client-acquisition strategy grounded in current quality."""

    role = "cmo"
    description = "Chief Marketing Officer for an elderly wellness call center. Plans client acquisition."

    def __init__(self, model: str | None = None):
        model = model or os.getenv("CMO_MODEL") or os.getenv("SUPERVISOR_MODEL")
        super().__init__(model=model, temperature=0.5, max_tokens=1100)

    @property
    def system_prompt(self) -> str:
        return """You are the CMO of "Hermes", an AI-run wellness call center. Families subscribe so their elderly relative gets a warm daily check-in call; the family receives reports.

Your job is client ACQUISITION: decide where new clients come from. You are given the company's current size (seniors served, calls completed) and its care-quality scores (0-10 on warmth, listening, info_quality, brevity).

Tie growth to quality:
- If average quality is below 7.5, recommend a "stabilize" posture: fix the product first, acquire cautiously.
- If quality is solid (>= 7.5), recommend a "scale" posture: lean into acquisition.

Think about a realistic market (Poland: GP clinics, senior clubs, parishes, caregiver forums, MOPS/NFZ partnerships, referrals). But also be creative: at least one channel or segment should be a fresh, non-obvious bet.

Respond with ONLY a JSON object, no prose, no fences:

{
  "posture": "scale" | "stabilize",
  "channels": ["concrete acquisition channel", "..."],
  "target_segments": ["who we target", "..."],
  "messaging": "1-2 sentence core value proposition for that audience",
  "next_steps": ["concrete action to take next", "..."]
}

Consider the owner's input as a priority signal. Be concrete and realistic, but also progressive. 3-5 channels, 2-3 segments, 3-4 next steps."""

    def plan(self, metrics: CompanyMetrics, owner_input: str = "") -> GrowthPlan:
        """Produce a GrowthPlan from the company metrics."""
        prompt = self._build_prompt(metrics, owner_input)
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt},
        ]
        try:
            raw = self.chat(messages, temperature=0.6)
            data = self._parse_json(raw)
        except Exception:  # noqa: BLE001 — never let growth strategy crash the company
            data = {}
        return self._to_plan(data, metrics)

    # ---- Internal ----

    def _build_prompt(self, metrics: CompanyMetrics, owner_input: str = "") -> str:
        scores = ", ".join(f"{k}: {v}" for k, v in metrics.avg_scores.items()) or "no data yet"
        owner_block = (
            f"## Owner input for this board meeting\n\n{owner_input}\n"
            if owner_input.strip()
            else "## Owner input\n\n(none provided)."
        )
        return f"""## Company size
Seniors served: {metrics.n_seniors}
Calls completed: {metrics.n_calls}

## Care quality (0-10)
{scores}
Average quality: {self._avg_quality(metrics) if metrics.avg_scores else 'n/a'}

{owner_block}

Produce the client-acquisition plan now (JSON only)."""

    @staticmethod
    def _avg_quality(metrics: CompanyMetrics) -> float:
        vals = list(metrics.avg_scores.values())
        return round(statistics.mean(vals), 1) if vals else 0.0

    def _to_plan(self, data: dict[str, Any], metrics: CompanyMetrics) -> GrowthPlan:
        avg_q = self._avg_quality(metrics) if metrics.avg_scores else 0.0
        default_posture = "scale" if avg_q >= SCALE_QUALITY_THRESHOLD else "stabilize"

        posture = str(data.get("posture", "")).strip().lower()
        if posture not in ("scale", "stabilize"):
            posture = default_posture

        channels = [str(c).strip() for c in data.get("channels", []) if str(c).strip()]
        segments = [str(s).strip() for s in data.get("target_segments", []) if str(s).strip()]
        next_steps = [str(s).strip() for s in data.get("next_steps", []) if str(s).strip()]
        messaging = str(data.get("messaging", "")).strip()

        # Deterministic fallbacks so the plan is always usable.
        if not channels:
            channels = list(_DEFAULT_CHANNELS)
            if posture == "stabilize":
                # When stabilising, lean on low-volume, high-trust channels only.
                channels = channels[:2] + [_DEFAULT_CHANNELS[5]]
        if not segments:
            segments = list(_DEFAULT_SEGMENTS)
        if not messaging:
            messaging = (
                "Codzienny, ciepły telefon do Twojego rodzica i jasny raport dla Ciebie "
                "— spokój ducha, gdy nie możesz być obok."
            )
        if not next_steps:
            if posture == "stabilize":
                next_steps = [
                    f"Najpierw podnieś jakość (śr. {avg_q}/10) zanim ruszysz z akwizycją na szerszą skalę.",
                    "Uruchom program poleceń wśród obecnych rodzin.",
                    "Przygotuj pilotaż z jedną przychodnią POZ.",
                ]
            else:
                next_steps = [
                    "Nawiąż kontakt z 3 domami/klubami seniora w okolicy.",
                    "Przygotuj ulotkę i skrypt dla lekarzy rodzinnych.",
                    "Uruchom program poleceń z benefitem dla polecającej rodziny.",
                    "Przetestuj jeden płatny kanał (lokalny Facebook dla opiekunów).",
                ]

        return GrowthPlan(
            posture=posture,
            channels=channels,
            target_segments=segments,
            messaging=messaging,
            next_steps=next_steps,
            set_by="cmo",
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
