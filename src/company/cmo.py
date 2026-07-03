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

# Autonomous fallback channels — owner-approved: ready-to-paste posts, training data only, PL only.
_DEFAULT_CHANNELS = [
    "Gotowe posty na fora senioralne (treści helpful z treningów self-play, PL, do wklejenia)",
    "Gotowe posty na X/Twitter (insighty wellness z treningów, PL, anonymized, do wklejenia)",
    "Gotowe posty na LinkedIn dla dorosłych dzieci seniorów (tone profesjonalny, PL, do wklejenia)",
    "Referral prompt w skrypcie zamykającym rozmowę (operator prosi zadowolone rodziny o polecenie)",
    "Udostępniane automatyczne raporty dla rodzin (rodzina przekazuje rodzeństwu)",
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
        super().__init__(model=model, temperature=0.5, max_tokens=2048)

    @property
    def system_prompt(self) -> str:
        return """You are the CMO of "Hermes", an AI-run wellness call center. Families subscribe so their elderly relative gets a warm daily check-in call; the family receives reports.

Your job is client ACQUISITION: decide where new clients come from. You are given the company's current size (seniors served, calls completed) and its care-quality scores (0-10 on warmth, listening, info_quality, brevity).

Tie growth to quality:
- If average quality is below 7.5, recommend a "stabilize" posture: fix the product first, acquire cautiously.
- If quality is solid (>= 7.5), recommend a "scale" posture: lean into acquisition.

CRITICAL OPERATING CONSTRAINTS (from owner):
- The company operates with NO access to email, phone, printer, or human social networks that require manual posting.
- NO API ACCESS: the AI generates ready-to-paste post copy (text snippets). The owner manually publishes when they choose. The AI does NOT post directly.
- CONTENT SOURCE: only data from daily self-play training simulations may be used for content. NO real call data, NO real senior data. Composite/illustrative scenarios from training are allowed.
- LANGUAGE: Polish only. No English content.
- NO COMPANY REGISTRATION DATA: do not cite company name, NIP, KRS, or any legal entity details in posts. If a forum requires legal verification, skip that forum.
- FULL AUTONOMY granted for A/B testing scripts and messaging in simulation — no need to ask owner permission for each variant.
- ETHICS: maximum standards — no manipulative techniques, full transparency to families and seniors.
- LEGAL: fully RODO/GDPR compliant, Polish law, strict data protection for elderly individuals.
- BUDGET: no budget constraints on AI-executed actions.

Priority acquisition order (from owner): internet forums > X (Twitter) > LinkedIn > product-led growth from existing families.

Propose channels that the AI can execute autonomously:
- Ready-to-paste forum posts in Polish senior-care communities (helpful, non-sales content from training insights),
- Ready-to-paste X/Twitter posts in Polish sharing anonymized training insights and wellness tips,
- Ready-to-paste LinkedIn posts in Polish targeting adult children of seniors (professional, trust-building tone),
- Product-led referrals (shareable family reports, referral prompts in closing scripts),
- Internal self-play A/B tests of all messaging before generating final post copy.

3-5 channels, 2-3 segments, 3-4 next steps — ALL autonomously executable without owner involvement.

Respond with ONLY a JSON object, no prose, no fences:

{
  "posture": "scale" | "stabilize",
  "channels": ["concrete autonomous acquisition channel", "..."],
  "target_segments": ["who we target", "..."],
  "messaging": "1-2 sentence core value proposition for that audience",
  "next_steps": ["concrete action the company can execute autonomously", "..."]
}

Consider the owner's input as a priority signal."""

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
                channels = channels[:2] + [_DEFAULT_CHANNELS[3]]
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
                    "Wygeneruj ulepszony skrypt operatora i przetestuj go w self-play.",
                    "Zidentyfikuj 3 najlepsze momenty z treningów self-play i stwórz z nich gotowe posty na fora (PL).",
                ]
            else:
                next_steps = [
                    "Wygeneruj 5 gotowych postów na fora senioralne (PL, helpful content z treningów self-play, do wklejenia).",
                    "Wygeneruj 3 gotowe posty na X/Twitter i 2 na LinkedIn (PL, insighty wellness z treningów, do wklejenia).",
                    "Przeprowadź self-play A/B test 3 wariantów messagingu w symulacji przed generowaniem finalnych postów.",
                    "Wygeneruj nową wersję skryptu zamykającego rozmowę z naturalnym prośbą o polecenie.",
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
