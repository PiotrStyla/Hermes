"""FastAPI webhook server for Twilio outbound wellness calls.

Endpoints (all called by Twilio over HTTPS in production):

  POST /twilio/start    First TwiML when the call connects (or hits voicemail).
  POST /twilio/turn     Called after each <Record> with the senior's audio.
  POST /twilio/status   Status callbacks (initiated/ringing/answered/completed).
  GET  /twilio/audio/<call_sid>/<filename>   Serves the operator's TTS MP3.

Ngrok or any HTTPS reverse proxy must point at this server's port.

Security:
- Twilio signs every webhook with HMAC-SHA1 in `X-Twilio-Signature`. We verify
  it when `TWILIO_AUTH_TOKEN` is set; in dry-run / dev we skip with a warning.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import FileResponse, PlainTextResponse, Response
from rich.console import Console

from ..agents.operator import OperatorAgent
from ..compliance import AuditLog, ConsentStore
from ..compliance.consent import (
    SCOPE_PROCESS_HEALTH_DATA,
    SCOPE_RECORD_AUDIO,
    SCOPE_TRAIN_ON_TRANSCRIPTS,
)
from ..seniors.store import SeniorStore
from .config import TelephonyConfig
from .session import CallStateStore
from .stt import WhisperFileSTT, download_twilio_recording
from .tts import TwilioTTS
from .turn_handler import build_initial_turn, handle_senior_turn
from .twilio_client import TwilioCallClient


def create_app(
    config: TelephonyConfig | None = None,
    console: Console | None = None,
) -> FastAPI:
    """Build the FastAPI app. One instance per process."""
    cfg = config or TelephonyConfig.from_env()
    log = console or Console()
    app = FastAPI(title="Hermes Telephony", version="0.3.0")

    # Long-lived helpers (no per-request work).
    state_store = CallStateStore()
    senior_store = SeniorStore()
    consent_store = ConsentStore()
    audit = AuditLog()
    tts = TwilioTTS()
    stt = WhisperFileSTT()
    twilio_client = TwilioCallClient(cfg, console=log)

    # ---- Twilio request signature verification ----

    async def _verify_twilio(request: Request) -> None:
        if twilio_client.dry_run or not cfg.auth_token:
            return  # dev / dry-run: skip
        from twilio.request_validator import RequestValidator

        validator = RequestValidator(cfg.auth_token)
        signature = request.headers.get("X-Twilio-Signature", "")
        # Twilio signs the original request URL (incl. scheme + host they hit).
        url = str(request.url)
        form = dict(await request.form())
        if not validator.validate(url, form, signature):
            raise HTTPException(status_code=403, detail="Invalid Twilio signature")

    # ---- POST /twilio/start ----

    @app.post("/twilio/start", response_class=Response)
    async def twilio_start(request: Request, call_id: str) -> Response:
        await _verify_twilio(request)
        form = await request.form()
        twilio_call_sid = form.get("CallSid", "")
        answered_by = form.get("AnsweredBy", "")
        if not twilio_call_sid:
            raise HTTPException(400, "Missing CallSid")

        # If we hit voicemail / answering machine, hang up gracefully.
        if answered_by.startswith("machine_") or answered_by == "fax":
            audit.record(
                "telephony_voicemail_aborted",
                actor="server",
                senior_id=None,
                details={"call_sid": twilio_call_sid, "answered_by": answered_by},
            )
            return Response(content=_hangup_twiml(), media_type="application/xml")

        # `call_id` is our internal id we passed when initiating; load the
        # pre-staged senior + consent context from the local state file.
        try:
            staged = state_store.load(call_id)
        except FileNotFoundError:
            log.print(f"[red]Unknown call_id={call_id!r} from Twilio[/red]")
            raise HTTPException(404, "Unknown call_id")

        # Promote the staged record to the actual Twilio CallSid so subsequent
        # webhooks (which only know CallSid) can find it.
        staged.call_sid = twilio_call_sid
        state_store.save(staged)

        operator = OperatorAgent()
        operator.health_consent = staged.health_consent  # type: ignore[attr-defined]
        result = build_initial_turn(
            staged, operator, tts, cfg, state_store, audit
        )
        return Response(content=result.twiml, media_type="application/xml")

    # ---- POST /twilio/turn ----

    @app.post("/twilio/turn", response_class=Response)
    async def twilio_turn(request: Request, call_sid: str) -> Response:
        await _verify_twilio(request)
        form = await request.form()
        recording_url = form.get("RecordingUrl", "")
        recording_sid = form.get("RecordingSid", "")
        try:
            state = state_store.load(call_sid)
        except FileNotFoundError:
            raise HTTPException(404, "Unknown call_sid")

        senior_profile = senior_store.load(state.senior_id)

        if not recording_url:
            # No recording — likely silence timeout. End politely.
            return Response(content=_hangup_twiml(), media_type="application/xml")

        # Download audio, transcribe, optionally clean up per RODO scope.
        rec_path = state_store.call_dir(call_sid) / "rec" / f"turn_{state.turn_count + 1:03d}.wav"
        try:
            download_twilio_recording(
                recording_url, cfg.account_sid, cfg.auth_token, rec_path
            )
            transcript = stt.transcribe_file(rec_path, language=senior_profile.language)
        except Exception as exc:  # noqa: BLE001
            log.print(f"[red]STT/download failure: {exc}[/red]")
            audit.record(
                "telephony_stt_failure",
                actor="server",
                senior_id=state.senior_id,
                details={"call_sid": call_sid, "error": str(exc)},
            )
            return Response(content=_hangup_twiml(), media_type="application/xml")

        # Cleanup per consent
        if recording_sid:
            state.twilio_recording_sids.append(recording_sid)
            if not state.record_audio_consent:
                twilio_client.delete_recording(recording_sid)
                try:
                    rec_path.unlink(missing_ok=True)
                except OSError:
                    pass
            else:
                state.rec_files.append(str(rec_path))

        operator = OperatorAgent()
        operator.health_consent = state.health_consent  # type: ignore[attr-defined]
        result = handle_senior_turn(
            state, transcript, operator, tts, cfg,
            state_store, consent_store, audit, log,
        )
        return Response(content=result.twiml, media_type="application/xml")

    # ---- POST /twilio/status ----

    @app.post("/twilio/status", response_class=PlainTextResponse)
    async def twilio_status(request: Request) -> str:
        await _verify_twilio(request)
        form = await request.form()
        call_sid = form.get("CallSid", "")
        call_status = form.get("CallStatus", "")
        if not call_sid:
            return "missing CallSid"

        if not state_store.exists(call_sid):
            log.print(f"[yellow]Status for unknown call_sid={call_sid}[/yellow]")
            return "ok"

        state = state_store.load(call_sid)
        if call_status in ("completed", "failed", "busy", "no-answer", "canceled"):
            state_store.mark_ended(state, reason=state.end_reason or call_status, status=call_status)
            audit.record(
                f"telephony_call_{call_status}",
                actor="server",
                senior_id=state.senior_id,
                details={"call_sid": call_sid, "turns": state.turn_count},
            )
            # Hand off to Manager for review/report (synchronous — fast enough).
            try:
                from .runner import finalize_call

                finalize_call(state, log)
            except Exception as exc:  # noqa: BLE001
                log.print(f"[red]Post-call finalize failed: {exc}[/red]")
        return "ok"

    # ---- GET /twilio/audio/<sid>/<file> ----

    @app.get("/twilio/audio/{call_sid}/{filename}")
    async def twilio_audio(call_sid: str, filename: str) -> FileResponse:
        path: Path = state_store.call_dir(call_sid) / "tts" / filename
        if not path.exists() or ".." in filename:
            raise HTTPException(404, "audio not found")
        return FileResponse(path, media_type="audio/mpeg")

    # ---- Health ----

    @app.get("/health")
    async def health() -> dict[str, object]:
        return {
            "ok": True,
            "twilio_dry_run": twilio_client.dry_run,
            "missing_env": cfg.missing_keys(),
            "scopes_known": [
                SCOPE_RECORD_AUDIO,
                SCOPE_PROCESS_HEALTH_DATA,
                SCOPE_TRAIN_ON_TRANSCRIPTS,
            ],
        }

    return app


def _hangup_twiml() -> str:
    from twilio.twiml.voice_response import VoiceResponse

    vr = VoiceResponse()
    vr.hangup()
    return str(vr)
