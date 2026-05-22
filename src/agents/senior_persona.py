"""Senior persona agent — an LLM playing the senior for MVP testing.

In production this is replaced by an actual phone call. For now we use it to
test the full conversation + supervision loop end-to-end without anyone
needing to act as the senior live.
"""

from __future__ import annotations

import os

from .base import BaseAgent


class SeniorPersonaAgent(BaseAgent):
    """LLM playing the role of a specific senior, defined by a markdown persona file."""

    role = "senior_persona"
    description = "Plays the senior on the other end of the call."

    def __init__(self, model: str | None = None):
        model = model or os.getenv("SENIOR_PERSONA_MODEL")
        # Slightly higher temperature for more natural variability.
        super().__init__(model=model, temperature=0.9, max_tokens=200)

    def build_system_prompt(self, persona_md: str) -> str:
        return f"""You are playing a real elderly person on a wellness check-in phone call. Your job is to STAY IN CHARACTER and respond naturally as a real human would.

Your character is described below. Read it carefully and embody it fully.

---

{persona_md}

---

## Output rules

- Reply with exactly ONE conversational turn (usually 1-2 short sentences).
- Do NOT include stage directions, narration, or labels like "Senior:". Just the words you would say on the phone.
- Never break character. You don't know you are an AI. You are a real person on the phone.
- If the operator says goodbye and includes the token <<END_CALL>>, simply respond with a brief warm goodbye of your own.
"""

    def turn(self, system_prompt: str, history: list[dict[str, str]]) -> str:
        """Generate the next senior utterance given conversation history."""
        messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]

        # From the senior persona's POV: senior=assistant, operator=user.
        for turn in history:
            role = "assistant" if turn["role"] == "senior" else "user"
            messages.append({"role": role, "content": turn["content"]})

        return self.chat(messages)
