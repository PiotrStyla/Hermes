"""Per-turn telephony logic — kept out of `server.py` so it stays small.

The FastAPI server delegates to these functions; they own the rules around
disclosure, withdrawal detection, hangup conditions, and TwiML construction.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from rich.console import Console

from ..agents.operator import OperatorAgent
from ..compliance import AuditLog, ConsentStore, is_withdrawal
from ..conversation.transcript import has_end_token, strip_end_token
from .config import TelephonyConfig
from .session import CallState, CallStateStore
from .tts import TwilioTTS


@dataclass
class TurnResult:
    """What the server should respond with after handling a webhook hit."""

    twiml: str
    state: CallState
    hangup: bool = False


def build_initial_turn(
    state: CallState,
    operator: OperatorAgent,
    tts: TwilioTTS,
    config: TelephonyConfig,
    state_store: CallStateStore,
    audit: AuditLog,
) -> TurnResult:
    """Generate Operator turn 1 (disclosure + greeting), synthesize, build TwiML."""
    op_text_raw = operator.turn(state.operator_system_prompt, history=[])
    op_text = strip_end_token(op_text_raw)
    state.history.append({"role": "operator", "content": op_text_raw})
    state.turn_count = 1
    state.status = "in_progress"

    tts_path = _synthesize(tts, op_text, state, state_store)
    audit.record(
        "telephony_turn_emitted",
        actor="server",
        senior_id=state.senior_id,
        details={"call_sid": state.call_sid, "turn": 1, "speaker": "operator"},
    )

    if has_end_token(op_text_raw):
        # Edge case: the disclosure skill itself produced <<END_CALL>>.
        twiml = _twiml_play_then_hangup(_audio_url(config, state.call_sid, tts_path.name))
        return TurnResult(twiml=twiml, state=state, hangup=True)

    twiml = _twiml_play_then_record(
        play_url=_audio_url(config, state.call_sid, tts_path.name),
        record_action_url=_turn_action_url(config, state.call_sid),
        max_seconds=config.record_max_seconds,
        silence_timeout=config.record_silence_timeout,
    )
    state_store.save(state)
    return TurnResult(twiml=twiml, state=state)


def handle_senior_turn(
    state: CallState,
    senior_text: str,
    operator: OperatorAgent,
    tts: TwilioTTS,
    config: TelephonyConfig,
    state_store: CallStateStore,
    consent_store: ConsentStore,
    audit: AuditLog,
    console: Console,
) -> TurnResult:
    """Append senior turn, run withdrawal check, generate next operator turn."""
    state.history.append({"role": "senior", "content": senior_text})
    state.turn_count += 1

    # RODO Art. 7(3): mid-call withdrawal.
    if is_withdrawal(senior_text):
        console.print(
            f"[red bold]⚠ Withdrawal phrase in call {state.call_sid}; revoking + ending.[/red bold]"
        )
        consent_store.revoke(
            state.senior_id,
            notes=f"Mid-call withdrawal during telephony session: {senior_text!r}",
        )
        audit.record(
            "consent_withdrawn_mid_call",
            actor="server",
            senior_id=state.senior_id,
            details={"call_sid": state.call_sid, "utterance": senior_text},
        )
        # Inject a sentinel turn so the Operator produces an apologetic goodbye.
        directive = "[CONSENT WITHDRAWN BY SENIOR — END THE CALL WARMLY NOW.]"
        op_text_raw = operator.turn(
            state.operator_system_prompt,
            state.history + [{"role": "senior", "content": directive}],
        )
        state.history.append({"role": "operator", "content": op_text_raw})
        state.end_reason = "withdrawal"
        tts_path = _synthesize(tts, strip_end_token(op_text_raw), state, state_store)
        twiml = _twiml_play_then_hangup(
            _audio_url(config, state.call_sid, tts_path.name)
        )
        state_store.save(state)
        return TurnResult(twiml=twiml, state=state, hangup=True)

    # Normal next operator turn.
    op_text_raw = operator.turn(state.operator_system_prompt, state.history)
    state.history.append({"role": "operator", "content": op_text_raw})

    audit.record(
        "telephony_turn_emitted",
        actor="server",
        senior_id=state.senior_id,
        details={
            "call_sid": state.call_sid,
            "turn": state.turn_count,
            "speaker": "operator",
        },
    )

    op_text = strip_end_token(op_text_raw)
    tts_path = _synthesize(tts, op_text, state, state_store)
    audio_url = _audio_url(config, state.call_sid, tts_path.name)

    if has_end_token(op_text_raw):
        state.end_reason = state.end_reason or "natural_end"
        twiml = _twiml_play_then_hangup(audio_url)
        state_store.save(state)
        return TurnResult(twiml=twiml, state=state, hangup=True)

    twiml = _twiml_play_then_record(
        play_url=audio_url,
        record_action_url=_turn_action_url(config, state.call_sid),
        max_seconds=config.record_max_seconds,
        silence_timeout=config.record_silence_timeout,
    )
    state_store.save(state)
    return TurnResult(twiml=twiml, state=state)


# ---- Internals ----


def _synthesize(
    tts: TwilioTTS, text: str, state: CallState, state_store: CallStateStore
) -> Path:
    call_dir = state_store.call_dir(state.call_sid)
    out_path = call_dir / "tts" / f"turn_{state.turn_count:03d}.mp3"
    tts.synthesize_to_file(text, out_path)
    state.tts_files.append(str(out_path))
    return out_path


def _audio_url(config: TelephonyConfig, call_sid: str, filename: str) -> str:
    base = config.public_base_url or "http://localhost:8000"
    return f"{base}/twilio/audio/{call_sid}/{filename}"


def _turn_action_url(config: TelephonyConfig, call_sid: str) -> str:
    base = config.public_base_url or "http://localhost:8000"
    return f"{base}/twilio/turn?call_sid={call_sid}"


def _twiml_play_then_record(
    play_url: str,
    record_action_url: str,
    max_seconds: int,
    silence_timeout: int,
) -> str:
    # Lazy import so tests / dry-run don't need the Twilio SDK installed.
    from twilio.twiml.voice_response import VoiceResponse

    vr = VoiceResponse()
    vr.play(play_url)
    vr.record(
        action=record_action_url,
        method="POST",
        max_length=max_seconds,
        timeout=silence_timeout,
        trim="trim-silence",
        play_beep=False,
        finish_on_key="",
    )
    # Twilio re-enters here only if <Record> times out without any audio.
    vr.say("I didn't catch that. We'll talk again soon. Goodbye.")
    vr.hangup()
    return str(vr)


def _twiml_play_then_hangup(play_url: str) -> str:
    from twilio.twiml.voice_response import VoiceResponse

    vr = VoiceResponse()
    vr.play(play_url)
    vr.hangup()
    return str(vr)
