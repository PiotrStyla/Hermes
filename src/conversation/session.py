"""CallSession — runs one full Operator <-> Senior conversation.

Two modes:
- text  (default) : Senior is played by SeniorPersonaAgent (LLM).
- voice           : Operator is voiced by ElevenLabs TTS, Senior is the
                    actual user speaking into the microphone (Whisper STT).
"""

from __future__ import annotations

from rich.console import Console

from ..agents.operator import OperatorAgent
from ..agents.senior_persona import SeniorPersonaAgent
from ..seniors.store import SeniorProfile, SeniorStore
from .transcript import has_end_token, strip_end_token


# 5 minutes ≈ ~20 turns. We cap at 18 to leave room for a graceful goodbye.
MAX_TURNS = 18


class CallSession:
    """Runs one wellness call between the Operator and a Senior.

    Returns the full conversation history as a list of {role, content} dicts.
    """

    def __init__(
        self,
        operator: OperatorAgent | None = None,
        senior: SeniorPersonaAgent | None = None,
        store: SeniorStore | None = None,
        console: Console | None = None,
        voice_mode: bool = False,
    ):
        self.operator = operator or OperatorAgent()
        self.senior = senior  # only used in text mode
        self.store = store or SeniorStore()
        self.console = console or Console()
        self.voice_mode = voice_mode

        # Lazily initialized voice components (only when voice_mode is True).
        self._tts = None
        self._stt = None
        self._mic = None

        if self.voice_mode:
            self._init_voice()
        elif self.senior is None:
            # Text mode falls back to the persona LLM.
            self.senior = SeniorPersonaAgent()

    # ---- Voice setup ----

    def _init_voice(self) -> None:
        from ..voice import ElevenLabsTTS, Microphone, WhisperSTT

        self._tts = ElevenLabsTTS()
        self._stt = WhisperSTT()
        self._mic = Microphone()

    # ---- Turn helpers ----

    def _print_operator(self, text: str) -> None:
        self.console.print(
            f"[bold cyan]Operator:[/bold cyan] {strip_end_token(text).strip()}"
        )

    def _print_senior(self, profile: SeniorProfile, text: str) -> None:
        self.console.print(
            f"[bold magenta]{profile.name}:[/bold magenta] "
            f"{strip_end_token(text).strip()}"
        )

    def _operator_turn(
        self, operator_system: str, history: list[dict[str, str]]
    ) -> str:
        op_message = self.operator.turn(operator_system, history)
        self._print_operator(op_message)
        if self.voice_mode and self._tts is not None:
            # Don't speak the END_CALL token out loud.
            self._tts.speak(strip_end_token(op_message).strip())
        return op_message

    def _senior_turn(
        self,
        profile: SeniorProfile,
        senior_system: str | None,
        history: list[dict[str, str]],
    ) -> str:
        if self.voice_mode:
            return self._senior_turn_voice(profile)
        assert self.senior is not None and senior_system is not None
        senior_message = self.senior.turn(senior_system, history)
        self._print_senior(profile, senior_message)
        return senior_message

    def _senior_turn_voice(self, profile: SeniorProfile) -> str:
        """Record from microphone and transcribe via Whisper."""
        assert self._mic is not None and self._stt is not None
        self.console.print(
            f"[dim]🎙️  Listening for {profile.name}... (speak, then pause)[/dim]"
        )
        audio = self._mic.record_until_silence()
        text = self._stt.transcribe(
            audio,
            sample_rate=self._mic.sample_rate,
            language=profile.language or None,
        )
        if not text:
            text = "(silence)"
        self._print_senior(profile, text)
        return text

    # ---- Main loop ----

    def run(self, profile: SeniorProfile) -> list[dict[str, str]]:
        persona_md = self.store.load_persona(profile.id) if not self.voice_mode else ""
        learnings = self.store.load_learnings(profile.id)

        operator_system = self.operator.build_system_prompt(profile, learnings)
        senior_system = (
            self.senior.build_system_prompt(persona_md)
            if (not self.voice_mode and self.senior is not None)
            else None
        )

        history: list[dict[str, str]] = []

        for _ in range(MAX_TURNS):
            op_message = self._operator_turn(operator_system, history)
            history.append({"role": "operator", "content": op_message})

            if has_end_token(op_message):
                # Let the senior say a brief goodbye, then exit.
                goodbye = self._senior_turn(profile, senior_system, history)
                history.append({"role": "senior", "content": goodbye})
                break

            senior_message = self._senior_turn(profile, senior_system, history)
            history.append({"role": "senior", "content": senior_message})
        else:
            # Hit MAX_TURNS without operator saying goodbye — force a wrap-up.
            self.console.print(
                "[yellow]Max turns reached — forcing operator wrap-up.[/yellow]"
            )
            wrap_history = history + [{
                "role": "senior",
                "content": "(internal) Time is up — say a warm goodbye now and include <<END_CALL>>.",
            }]
            op_close = self._operator_turn(operator_system, wrap_history)
            history.append({"role": "operator", "content": op_close})

        return history
