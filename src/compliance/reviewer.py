"""ComplianceReviewer — advisory LLM agent over artifacts.

This is NOT an enforcer. The deterministic safeguards (consent gates, retention
purge, redaction) live elsewhere. The reviewer reads an artifact (a prompt
diff, a report, a proposed code change) and flags potential RODO/GDPR concerns
for a human to address.

Output schema:
    {
        "verdict": "ok" | "warn" | "block",
        "concerns": [{"severity": "low|med|high", "rule": str, "explanation": str, "suggestion": str}],
        "summary": str
    }
"""

from __future__ import annotations

import json
import os
import re
from typing import Any

from ..agents.base import BaseAgent


class ComplianceReviewerAgent(BaseAgent):
    """LLM-backed RODO/GDPR advisor. Outputs structured JSON, never blocks code by itself."""

    role = "compliance_reviewer"
    description = (
        "Reviews artifacts (prompts, reports, code changes) against RODO/GDPR "
        "principles and flags concerns for human review."
    )

    def __init__(self, model: str | None = None):
        model = model or os.getenv("COMPLIANCE_MODEL") or os.getenv("SUPERVISOR_MODEL")
        super().__init__(model=model, temperature=0.1, max_tokens=2000)

    @property
    def system_prompt(self) -> str:
        return """You are a RODO/GDPR Compliance Reviewer for a wellness call center serving elderly people in the EU.

You read artifacts (prompts used by other AI agents, family reports, descriptions of code changes) and flag potential compliance concerns.

## Core principles you evaluate against

1. **Lawfulness (Art. 6)** — Is there a legal basis (consent, contract, legitimate interest) for what this artifact does?
2. **Purpose limitation (Art. 5(1)(b))** — Is data used only for stated purposes?
3. **Data minimisation (Art. 5(1)(c))** — Are we collecting/sharing only what's necessary?
4. **Storage limitation (Art. 5(1)(e))** — Is there an explicit retention policy?
5. **Special categories (Art. 9)** — Health, biometrics, voice — needs explicit consent.
6. **Transparency (Art. 13/14)** — Does the senior understand what's happening?
7. **Data subject rights (Art. 15-22)** — Access, rectification, erasure, restriction.
8. **Family sharing** — Adult seniors must consent to family receiving reports. Proxy consent only for legally appointed guardians.

## Output

Return ONLY a JSON object:

{
  "verdict": "ok" | "warn" | "block",
  "concerns": [
    {
      "severity": "low" | "med" | "high",
      "rule": "Art. X / short name",
      "explanation": "what specifically is risky in the artifact",
      "suggestion": "concrete change that would resolve it"
    }
  ],
  "summary": "one-line human-readable verdict"
}

Use `verdict: "block"` ONLY for clear unlawful processing (e.g. sharing health data with no consent record). Otherwise `warn` for fixable risks, `ok` for clean artifacts.
"""

    def review_artifact(self, kind: str, content: str, context: str = "") -> dict[str, Any]:
        """Review a single artifact and return structured concerns.

        Args:
            kind: e.g. "operator_prompt", "family_report", "code_change".
            content: the artifact text itself.
            context: optional extra info (e.g. existing consent state, target audience).
        """
        prompt = f"""## Artifact kind
{kind}

## Context
{context or "(no extra context)"}

## Artifact content

{content}

Return your JSON review now."""

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt},
        ]
        raw = self._chat_json(messages)
        return self._parse_json(raw)

    # ---- helpers (duplicate of Supervisor's; small enough not to abstract yet) ----

    def _chat_json(self, messages: list[dict[str, str]]) -> str:
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                response_format={"type": "json_object"},
            )
            return response.choices[0].message.content or ""
        except Exception:
            return self.chat(messages)

    @staticmethod
    def _parse_json(text: str) -> dict[str, Any]:
        text = text.strip()
        fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, re.DOTALL)
        if fence:
            text = fence.group(1)
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            text = text[start : end + 1]
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            preview = text[:300].replace("\n", " ")
            return {
                "verdict": "warn",
                "concerns": [
                    {
                        "severity": "low",
                        "rule": "internal",
                        "explanation": f"Reviewer returned unparseable JSON: {e}",
                        "suggestion": f"Raw preview: {preview}...",
                    }
                ],
                "summary": "Reviewer output could not be parsed.",
                "_raw": text,
            }
