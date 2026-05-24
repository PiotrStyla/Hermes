"""Operator agent — conducts the wellness call.

The Operator's behavior is shaped entirely by markdown skill files in
`data/skills/operator/`. The Supervisor proposes patches to those files
after each call, the Manager applies them, and the next call uses the
updated skills automatically.
"""

from __future__ import annotations

import os

from .base import BaseAgent
from ..seniors.store import SeniorProfile
from ..skills.loader import SkillsLoader


_LANGUAGE_NAMES = {
    "en": "English",
    "pl": "Polish (polski)",
    "de": "German (Deutsch)",
    "fr": "French (français)",
    "es": "Spanish (español)",
    "it": "Italian (italiano)",
}


def _language_name(code: str) -> str:
    return _LANGUAGE_NAMES.get(code.lower(), code)


class OperatorAgent(BaseAgent):
    """The friendly voice on the call.

    Reads the senior's profile, learnings, and all operator skills,
    then conducts a turn-based conversation.
    """

    role = "operator"
    description = "Warm, attentive operator conducting a daily wellness check-in."

    def __init__(self, model: str | None = None):
        model = model or os.getenv("OPERATOR_MODEL")
        super().__init__(model=model, temperature=0.7, max_tokens=400)
        self.skills_loader = SkillsLoader()
        # Defaults to True so unit tests / direct usage don't accidentally
        # restrict the operator. ManagerAgent overrides this from consent state.
        self.health_consent: bool = True

    def build_system_prompt(self, profile: SeniorProfile, learnings: str) -> str:
        skills_block = self.skills_loader.assemble_prompt_section()
        learnings_block = learnings.strip() if learnings.strip() else "(no prior notes)"
        language_name = _language_name(profile.language)
        health_block = (
            ""
            if self.health_consent
            else (
                "\n## Health data restriction\n\n"
                "The senior has NOT consented to processing of special-category "
                "health data (RODO Art. 9). You MUST NOT ask about specific medications, "
                "diagnoses, symptoms, pain, or anything clinical. Keep the conversation "
                "to mood, daily routine, and general well-being. If they bring up health "
                "themselves, acknowledge warmly but do not probe.\n"
            )
        )

        return f"""You are a warm, professional wellness-check operator working for a service that families subscribe to so their elderly relatives get a daily kind phone call.

## Language

**You MUST speak only in {language_name}**, naturally and idiomatically, addressing the senior the way a native speaker would address an elderly person they care about. Use the appropriate level of formality for that culture (e.g., in Polish use "Pan/Pani" + first name unless the profile says otherwise).

You are about to call this senior:

{profile.to_summary()}

Things we have learned about THIS specific person from previous calls:

{learnings_block}

You must follow these skills, which together describe HOW you should behave:

{skills_block}
{health_block}

## Output rules

- Reply with exactly ONE conversational turn (1-3 short sentences typically).
- Do NOT include stage directions, narration, or labels like "Operator:". Just the words you would say.
- Speak as if on a real phone call. Natural, warm, human.
- Track the conversation phase yourself (disclosure → greeting → mood → health → safety → farewell) but never name these phases out loud.
- **Turn 1 MUST satisfy the `disclosure` skill** (identify yourself, say you are an AI assistant, state the purpose, mention they can stop the call any time). Anything else on turn 1 must come AFTER that.
- When you have gathered mood + health + safety info OR you reach the farewell trigger, say goodbye warmly and include the literal token <<END_CALL>> at the very end of your message. The call will then end.
"""

    def turn(self, system_prompt: str, history: list[dict[str, str]]) -> str:
        """Generate the next operator utterance given conversation history.

        history is a list of {role: 'operator'|'senior', content: str}.
        """
        messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]

        # Map our roles to OpenAI roles: operator=assistant, senior=user.
        for turn in history:
            role = "assistant" if turn["role"] == "operator" else "user"
            messages.append({"role": role, "content": turn["content"]})

        # If there is no history yet, prompt for the opening line.
        if not history:
            messages.append({
                "role": "user",
                "content": "(The call has just been answered. Say hello.)",
            })

        return self.chat(messages)
