"""Outbound call initiator + post-call hand-off to the Manager.

`start_outbound_call` performs the consent gate, stages a CallState file, and
asks Twilio to dial. `finalize_call` is invoked by the /twilio/status webhook
when the call ends; it delegates to `ManagerAgent.finalize_call` for the same
post-call review/report pipeline used by the text/voice modes.
"""

from __future__ import annotations

import uuid
from typing import Any

from rich.console import Console

from ..agents.operator import OperatorAgent
from ..compliance import AuditLog, ConsentStatus, ConsentStore
from ..compliance.consent import (
    SCOPE_PROCESS_HEALTH_DATA,
    SCOPE_RECORD_AUDIO,
    SCOPE_STORE_TRANSCRIPT,
    SCOPE_TRAIN_ON_TRANSCRIPTS,
    SCOPE_TRANSCRIBE,
)
from ..seniors.store import SeniorStore
from .config import TelephonyConfig
from .session import CallState, CallStateStore
from .twilio_client import TwilioCallClient


# Telephony adds `transcribe` (always — we Whisper the senior's audio).
# `share_with_family` is verified by the existing Manager pipeline at report time.
REQUIRED_SCOPES = (SCOPE_TRANSCRIBE, SCOPE_STORE_TRANSCRIPT)


def start_outbound_call(
    senior_id: str,
    *,
    dry_run: bool | None = None,
    allow_no_consent: bool = False,
    console: Console | None = None,
) -> dict[str, Any]:
    """Stage a CallState and ask Twilio to dial. Returns a summary dict."""
    log = console or Console()
    config = TelephonyConfig.from_env()
    senior_store = SeniorStore()
    consent_store = ConsentStore()
    audit = AuditLog()

    profile = senior_store.load(senior_id)
    if not profile.phone_number:
        raise RuntimeError(
            f"Senior {senior_id!r} has no phone_number on file. "
            "Add 'phone_number' (E.164 format like +48...) to their profile.json."
        )

    # ---- Consent gate (same shape as Manager.run_call_cycle) ----
    consent = consent_store.load(senior_id)
    missing = [s for s in REQUIRED_SCOPES if not consent.covers(s)]
    if consent.status == ConsentStatus.REVOKED:
        msg = (
            f"Consent for {senior_id!r} was REVOKED on {consent.revoked_at}. "
            "Refusing to place a call."
        )
        audit.record("telephony_call_blocked_revoked", actor="runner", senior_id=senior_id)
        raise PermissionError(msg)
    if missing and not allow_no_consent:
        msg = (
            f"Consent for {senior_id!r} is missing scopes {missing}. "
            "Run `consent grant` or pass --allow-no-consent for dev only."
        )
        audit.record(
            "telephony_call_blocked_missing_scopes",
            actor="runner",
            senior_id=senior_id,
            details={"missing_scopes": missing},
        )
        raise PermissionError(msg)
    if missing and allow_no_consent:
        log.print(
            f"[yellow]⚠ Telephony bypass: missing scopes {missing} "
            f"(allow_no_consent=True).[/yellow]"
        )
        audit.record(
            "telephony_call_consent_bypassed",
            actor="runner",
            senior_id=senior_id,
            details={"missing_scopes": missing},
        )

    # ---- Pre-build the operator system prompt and stage state ----
    health_consent = consent.covers(SCOPE_PROCESS_HEALTH_DATA)
    training_consent = consent.covers(SCOPE_TRAIN_ON_TRANSCRIPTS)
    record_audio_consent = consent.covers(SCOPE_RECORD_AUDIO)

    learnings = senior_store.load_learnings(senior_id)
    operator = OperatorAgent()
    operator.health_consent = health_consent  # type: ignore[attr-defined]
    operator_system_prompt = operator.build_system_prompt(profile, learnings)

    state_store = CallStateStore()
    # We use a temp call_id during staging — the /twilio/start webhook
    # promotes it to the real Twilio CallSid as soon as the call connects.
    call_id = uuid.uuid4().hex[:16]
    state_store.create(
        call_sid=call_id,
        senior_id=senior_id,
        operator_system_prompt=operator_system_prompt,
        record_audio_consent=record_audio_consent,
        health_consent=health_consent,
        training_consent=training_consent,
        voice_mode=True,
    )

    # ---- Dial ----
    client = TwilioCallClient(config, dry_run=dry_run, console=log)
    audit.record(
        "telephony_call_initiated",
        actor="runner",
        senior_id=senior_id,
        details={"call_id": call_id, "dry_run": client.dry_run},
    )
    result = client.initiate_call(profile.phone_number, call_id_param=call_id)

    return {
        "call_id": call_id,
        "twilio_call_sid": result.call_sid,
        "dry_run": result.dry_run,
        "missing_env": config.missing_keys() if not client.dry_run else [],
    }


def finalize_call(state: CallState, console: Console | None = None) -> dict[str, Any]:
    """Hand the captured `history` to Manager.finalize_call (review/report/queue)."""
    from ..agents.manager import ManagerAgent

    log = console or Console()
    senior_store = SeniorStore()
    prior_call_count = len(senior_store.list_reports(state.senior_id))
    # `prior_call_count` here counts the count BEFORE this telephony call was
    # finalized (we haven't saved its report yet). The numbering is consistent
    # with Manager.run_call_cycle.
    return ManagerAgent().finalize_call(
        senior_id=state.senior_id,
        history=state.history,
        prior_call_count=prior_call_count,
        training_consent=state.training_consent,
        console=log,
    )
