"""Twilio Media Streams WebSocket handler.

Replaces the <Play> + <Record> loop with a bidirectional audio stream.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect
from rich.console import Console

from ..agents.operator import OperatorAgent
from ..compliance import AuditLog, ConsentStore, is_withdrawal
from ..conversation.transcript import has_end_token, strip_end_token
from ..seniors.store import SeniorStore
from ..voice.tts import ElevenLabsTTS
from .audio_codec import mulaw_to_pcm, pcm_to_mulaw, resample_16k_to_8k, resample_8k_to_16k
from .config import TelephonyConfig
from .session import CallState, CallStateStore
from .stream_stt import BatchSTTFallback, StreamingSTT

MAX_TURNS = 18
SILENCE_FRAMES_STOP = 50  # ~1.5s at 30ms frames


class StreamHandler:
    """Manages one Twilio Media Streams WebSocket session."""

    def __init__(
        self,
        ws: WebSocket,
        call_id: str,
        config: TelephonyConfig,
        console: Console,
    ):
        self.ws = ws
        self.call_id = call_id
        self.config = config
        self.console = console
        self.state_store = CallStateStore()
        self.senior_store = SeniorStore()
        self.consent_store = ConsentStore()
        self.audit = AuditLog()
        self.tts = ElevenLabsTTS()
        self._stream_sid: str = ""
        self._operator_speaking = False
        self._senior_speaking = False
        self._silent_frames = 0
        self._senior_buffer: list[bytes] = []
        self._operator_task: asyncio.Task[Any] | None = None

    async def run(self) -> None:
        await self.ws.accept()
        state = self.state_store.load(self.call_id)
        profile = self.senior_store.load(state.senior_id)

        stt = StreamingSTT(language=profile.language)
        fallback_stt = BatchSTTFallback(language=profile.language)
        final_transcript: list[str] = []

        def on_transcript(text: str, is_final: bool) -> None:
            if is_final:
                final_transcript.append(text)
            if is_withdrawal(text):
                asyncio.create_task(self._handle_withdrawal(state, text))

        if stt.is_configured:
            await stt.connect(on_transcript)

        # Send initial operator greeting
        await self._send_operator_turn(state, profile)

        try:
            while True:
                raw = await self.ws.receive_text()
                msg = json.loads(raw)
                event = msg.get("event", "")

                if event == "start":
                    self._stream_sid = msg.get("start", {}).get("streamSid", "")
                    self.audit.record("media_stream_started", actor="server",
                                      senior_id=state.senior_id,
                                      details={"call_sid": state.call_sid, "stream_sid": self._stream_sid})

                elif event == "media":
                    payload = msg.get("media", {}).get("payload", "")
                    if not payload:
                        continue
                    import base64
                    chunk = base64.b64decode(payload)

                    if stt.is_configured:
                        await stt.send_audio(chunk)
                    fallback_stt.feed(chunk)

                    # Simple energy-based speech detection for interruption
                    pcm = mulaw_to_pcm(chunk)
                    rms = float(abs(pcm.astype(float)).mean()) / 32768.0
                    if rms > 0.01:
                        self._senior_speaking = True
                        self._silent_frames = 0
                        self._senior_buffer.append(chunk)
                        if self._operator_speaking and self._operator_task:
                            self._operator_task.cancel()
                            self._operator_speaking = False
                            self.console.print("[yellow]Operator interrupted by senior[/yellow]")
                    elif self._senior_speaking:
                        self._silent_frames += 1
                        self._senior_buffer.append(chunk)
                        if self._silent_frames >= SILENCE_FRAMES_STOP:
                            await self._process_senior_turn(
                                state, profile, fallback_stt, final_transcript, stt
                            )
                            self._senior_speaking = False
                            self._senior_buffer.clear()
                            self._silent_frames = 0

                elif event == "stop":
                    break

        except WebSocketDisconnect:
            pass
        finally:
            if stt.is_configured:
                await stt.close()
            await self._finalize(state)

    async def _send_operator_turn(self, state: CallState, profile: Any) -> None:
        operator = OperatorAgent()
        operator.health_consent = state.health_consent
        learnings = self.senior_store.load_learnings(state.senior_id)
        system = operator.build_system_prompt(profile, learnings)
        state.operator_system_prompt = system

        text = operator.turn(system, history=[])
        text = strip_end_token(text)
        state.history.append({"role": "operator", "content": text})
        state.turn_count = 1
        state.status = "in_progress"
        self.state_store.save(state)

        await self._stream_tts(text)

    async def _process_senior_turn(
        self, state: CallState, profile: Any,
        fallback_stt: BatchSTTFallback, final_transcript: list[str],
        stt: StreamingSTT,
    ) -> None:
        text = fallback_stt.finalize()
        if not text:
            text = " ".join(final_transcript[-3:]) if final_transcript else ""
        final_transcript.clear()
        if not text:
            return

        self.console.print(f"[dim]Senior ({profile.name}): {text}[/dim]")
        state.history.append({"role": "senior", "content": text})
        state.turn_count += 1

        if is_withdrawal(text):
            await self._handle_withdrawal(state, text)
            return

        if state.turn_count >= MAX_TURNS * 2:
            state.end_reason = "max_turns"
            await self._send_goodbye(state)
            return

        operator = OperatorAgent()
        operator.health_consent = state.health_consent
        op_text = operator.turn(state.operator_system_prompt, state.history)
        state.history.append({"role": "operator", "content": op_text})

        if has_end_token(op_text):
            state.end_reason = "natural_end"
            await self._stream_tts(strip_end_token(op_text))
            self.state_store.save(state)
            await self.ws.close()
            return

        self.state_store.save(state)
        await self._stream_tts(strip_end_token(op_text))

    async def _stream_tts(self, text: str) -> None:
        self._operator_speaking = True
        try:
            for chunk in self.tts.stream_mulaw(text):
                if not self._operator_speaking:
                    break
                import base64
                payload = base64.b64encode(chunk).decode()
                msg = json.dumps({
                    "event": "media",
                    "streamSid": self._stream_sid,
                    "media": {"payload": payload},
                })
                await self.ws.send_text(msg)
                await asyncio.sleep(0.02)
        finally:
            self._operator_speaking = False

    async def _handle_withdrawal(self, state: CallState, text: str) -> None:
        self.console.print(f"[red bold]Withdrawal in stream {state.call_sid}[/red bold]")
        self.consent_store.revoke(state.senior_id, notes=f"Mid-call withdrawal: {text!r}")
        self.audit.record("consent_withdrawn_mid_call", actor="server",
                          senior_id=state.senior_id,
                          details={"call_sid": state.call_sid, "utterance": text})
        state.end_reason = "withdrawal"
        operator = OperatorAgent()
        directive = "[CONSENT WITHDRAWN BY SENIOR — END THE CALL WARMLY NOW.]"
        op_text = operator.turn(state.operator_system_prompt,
                                state.history + [{"role": "senior", "content": directive}])
        state.history.append({"role": "operator", "content": op_text})
        self.state_store.save(state)
        await self._stream_tts(strip_end_token(op_text))
        await self.ws.close()

    async def _send_goodbye(self, state: CallState) -> None:
        operator = OperatorAgent()
        op_text = operator.turn(state.operator_system_prompt,
                                state.history + [{"role": "senior", "content": "[END CALL POLITELY]"}])
        state.history.append({"role": "operator", "content": op_text})
        self.state_store.save(state)
        await self._stream_tts(strip_end_token(op_text))
        await self.ws.close()

    async def _finalize(self, state: CallState) -> None:
        from .runner import finalize_call
        try:
            finalize_call(state, self.console)
        except Exception as exc:
            self.console.print(f"[red]Post-call finalize failed: {exc}[/red]")
