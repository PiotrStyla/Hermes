"""CallSession — runs one full Operator <-> Senior conversation."""

from __future__ import annotations

from rich.console import Console

from ..agents.operator import OperatorAgent
from ..agents.senior_persona import SeniorPersonaAgent
from ..seniors.store import SeniorProfile, SeniorStore
from .transcript import has_end_token, strip_end_token


# 5 minutes ≈ ~20 turns. We cap at 18 to leave room for a graceful goodbye.
MAX_TURNS = 18


class CallSession:
    """Runs one wellness call between the Operator and a Senior persona.

    Returns the full conversation history as a list of {role, content} dicts.
    """

    def __init__(
        self,
        operator: OperatorAgent | None = None,
        senior: SeniorPersonaAgent | None = None,
        store: SeniorStore | None = None,
        console: Console | None = None,
    ):
        self.operator = operator or OperatorAgent()
        self.senior = senior or SeniorPersonaAgent()
        self.store = store or SeniorStore()
        self.console = console or Console()

    def run(self, profile: SeniorProfile) -> list[dict[str, str]]:
        persona_md = self.store.load_persona(profile.id)
        learnings = self.store.load_learnings(profile.id)

        operator_system = self.operator.build_system_prompt(profile, learnings)
        senior_system = self.senior.build_system_prompt(persona_md)

        history: list[dict[str, str]] = []

        for turn_index in range(MAX_TURNS):
            # Operator speaks.
            op_message = self.operator.turn(operator_system, history)
            history.append({"role": "operator", "content": op_message})
            self.console.print(
                f"[bold cyan]Operator:[/bold cyan] {strip_end_token(op_message).strip()}"
            )

            if has_end_token(op_message):
                # Let the senior say a brief goodbye, then exit.
                senior_goodbye = self.senior.turn(senior_system, history)
                history.append({"role": "senior", "content": senior_goodbye})
                self.console.print(
                    f"[bold magenta]{profile.name}:[/bold magenta] "
                    f"{strip_end_token(senior_goodbye).strip()}"
                )
                break

            # Senior responds.
            senior_message = self.senior.turn(senior_system, history)
            history.append({"role": "senior", "content": senior_message})
            self.console.print(
                f"[bold magenta]{profile.name}:[/bold magenta] "
                f"{strip_end_token(senior_message).strip()}"
            )
        else:
            # Hit MAX_TURNS without operator saying goodbye — force a wrap-up turn.
            self.console.print(
                "[yellow]Max turns reached — forcing operator wrap-up.[/yellow]"
            )
            wrap_history = history + [{
                "role": "senior",
                "content": "(internal) Time is up — say a warm goodbye now and include <<END_CALL>>.",
            }]
            op_close = self.operator.turn(operator_system, wrap_history)
            history.append({"role": "operator", "content": op_close})
            self.console.print(
                f"[bold cyan]Operator:[/bold cyan] {strip_end_token(op_close).strip()}"
            )

        return history
