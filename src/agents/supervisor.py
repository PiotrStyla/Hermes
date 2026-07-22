"""Supervisor agent — reviews completed transcripts and proposes improvements."""

from __future__ import annotations

import json
import os
import re
from typing import Any

from .base import BaseAgent
from ..llm import apply_prompt_cache


class SupervisorAgent(BaseAgent):
    """Reads a completed call transcript and returns structured JSON feedback.

    Output schema:
        {
            "scores": {"warmth": 1-10, "listening": 1-10, "info_quality": 1-10, "brevity": 1-10},
            "strengths": [str, ...],
            "issues": [str, ...],
            "skill_updates": [{"skill": str, "patch": str}, ...],
            "senior_notes": [str, ...]
        }
    """

    role = "supervisor"
    description = "Quality assurance specialist for elderly wellness calls."

    def __init__(self, model: str | None = None):
        model = model or os.getenv("SUPERVISOR_MODEL")
        super().__init__(model=model, temperature=0.2, max_tokens=4000)

    @property
    def system_prompt(self) -> str:
        return """You are a Supervisor in a wellness call center for elderly people.

Your job is to review a completed call transcript between an Operator and a Senior, and produce structured feedback that will be used to (a) update the Operator's skills before the next call and (b) inform the report sent to the senior's family.

## What to evaluate

- **Warmth** — Did the Operator feel like a real, caring human?
- **Listening** — Did the Operator reflect what the Senior said and follow emotional threads?
- **Info quality** — Did the Operator gather the necessary info on mood, health (with reference to known conditions/medications), and safety, WITHOUT sounding like a checklist?
- **Brevity** — Did the call stay roughly under 5 minutes (~18 turns) and end gracefully?

## What to output

Respond with **ONLY a JSON object** matching this schema. No prose before or after.

```json
{
  "scores": {
    "warmth": 1-10,
    "listening": 1-10,
    "info_quality": 1-10,
    "brevity": 1-10
  },
  "strengths": ["short bullet", "..."],
  "issues": ["specific actionable issue", "..."],
  "skill_updates": [
    {
      "skill": "<exact skill filename without .md, one of: greeting | mood-checkin | health-checkin | safety-check | active-listening | farewell>",
      "patch": "Concrete, specific change to make to this skill. One paragraph max."
    }
  ],
  "senior_notes": [
    "Short fact-style note about THIS senior to remember for next time, e.g., 'Knee pain worse in mornings this week.'"
  ]
}
```

## Rules

- Be specific. "Improve warmth" is useless. "Operator missed an opportunity to ask about Tomek when Stefan mentioned grandchildren" is useful.
- Only propose skill_updates for genuinely needed changes. If the call was good (every score >= 7 and no critical issues), return an empty `skill_updates` array.
- senior_notes should be terse facts that would help future calls feel personal.
- Output MUST be valid JSON. No markdown fences, no commentary."""

    def review(
        self,
        transcript_md: str,
        operator_skills_summary: str,
    ) -> dict[str, Any]:
        """Review a transcript and return parsed JSON feedback."""
        prompt = f"""## Transcript to review

{transcript_md}

## Current operator skills (for reference when proposing patches)

{operator_skills_summary}

Return your JSON evaluation now."""

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt},
        ]

        raw = self._chat_json(messages)
        result = self._parse_json(raw)

        # Retry once if the first attempt produced zero scores from a parse error.
        if result.get("_raw"):
            retry_messages = messages + [
                {"role": "assistant", "content": raw},
                {"role": "user", "content": (
                    "Your previous response was not valid JSON. "
                    "Please return ONLY a valid JSON object matching the schema. "
                    "Ensure all commas are present between array and object elements. "
                    "Do not include any text outside the JSON object."
                )},
            ]
            raw_retry = self._chat_json(retry_messages)
            result = self._parse_json(raw_retry)

        return result

    def _chat_json(self, messages: list[dict[str, Any]]) -> str:
        """Send a chat completion that asks the model to return strict JSON.

        Tries response_format=json_object first (most providers); if the model
        rejects it, falls back to plain chat (the prompt itself still asks for
        JSON-only output).

        The Supervisor's `system_prompt` (rubric + JSON schema) is identical
        across every transcript, so we cache it on Anthropic models.
        """
        cached = apply_prompt_cache(messages, self.model, ttl="1h")
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=cached,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                response_format={"type": "json_object"},
            )
            return response.choices[0].message.content or ""
        except Exception:
            return self.chat(messages, cache_system_prompt=True, cache_ttl="1h")

    @staticmethod
    def _parse_json(text: str) -> dict[str, Any]:
        """Extract JSON from a model reply, tolerating wrapping fences or stray text."""
        text = text.strip()

        # Strip optional ```json fences.
        fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, re.DOTALL)
        if fence:
            text = fence.group(1)

        # Find the first { ... last } if there is leading/trailing prose.
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            text = text[start : end + 1]

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Attempt to repair common JSON issues.
        repaired = SupervisorAgent._repair_json(text)
        if repaired:
            try:
                return json.loads(repaired)
            except json.JSONDecodeError:
                pass

        # If the JSON looks truncated, try closing open brackets.
        closed = SupervisorAgent._close_truncated_json(text)
        if closed and closed != repaired:
            try:
                return json.loads(closed)
            except json.JSONDecodeError:
                pass

        preview = text[:300].replace("\n", " ")
        return {
            "scores": {"warmth": 0, "listening": 0, "info_quality": 0, "brevity": 0},
            "strengths": [],
            "issues": [
                f"Supervisor returned unparseable JSON",
                f"Raw preview: {preview}...",
            ],
            "skill_updates": [],
            "senior_notes": [],
            "_raw": text,
        }

    @staticmethod
    def _repair_json(text: str) -> str | None:
        """Try to fix common JSON syntax issues produced by LLMs.

        Handles:
        - Trailing commas before } or ]
        - Missing commas between items (newline + quote without preceding comma)
        """
        # Remove trailing commas before closing brackets/braces.
        fixed = re.sub(r",\s*([}\]])", r"\1", text)

        # Add missing commas: a closing quote or bracket followed by
        # whitespace and an opening quote or brace, without a comma.
        fixed = re.sub(r'("\s*)\n(\s*["])', r'\1,\n\2', fixed)
        fixed = re.sub(r'(\]\s*)\n(\s*["])', r'\1,\n\2', fixed)
        fixed = re.sub(r'(\}\s*)\n(\s*["])', r'\1,\n\2', fixed)
        fixed = re.sub(r'("\s*)\n(\s*\{)', r'\1,\n\2', fixed)

        if fixed != text:
            return fixed
        return None

    @staticmethod
    def _close_truncated_json(text: str) -> str | None:
        """Attempt to close unclosed brackets/braces in a truncated JSON string."""
        opens = text.count("{") - text.count("}")
        brackets = text.count("[") - text.count("]")
        if opens <= 0 and brackets <= 0:
            return None
        # Try closing — but only if the text looks like it was cut off.
        fixed = text.rstrip()
        # Remove any trailing incomplete fragment (e.g., a partial string).
        fixed = re.sub(r'["\'][^"\']*$', '', fixed)
        fixed += ']' * max(brackets, 0) + '}' * max(opens, 0)
        return fixed
