"""Manager agent — orchestrates the full call cycle and applies improvements.

The Manager owns the flow:
  1. Run the call (CallSession).
  2. Save the transcript.
  3. Ask the Supervisor for feedback.
  4. Decide which skill_updates to apply, then ask an LLM to rewrite each
     affected skill incorporating the patch.
  5. Persist senior-specific learnings.
  6. Hand the transcript to the Report Generator.
"""

from __future__ import annotations

import os
from typing import Any

from rich.console import Console
from rich.panel import Panel

from .base import BaseAgent
from .operator import OperatorAgent
from .senior_persona import SeniorPersonaAgent
from .supervisor import SupervisorAgent
from ..seniors.store import SeniorStore
from ..skills.loader import SkillsLoader
from ..skills.updater import SkillsUpdater


# Score below this on any axis → trigger a skill rewrite.
QUALITY_THRESHOLD = 7


class ManagerAgent(BaseAgent):
    """Orchestrator. Also acts as an LLM that rewrites skills when patching them."""

    role = "manager"
    description = "Manager of the wellness call center. Orchestrates calls and improvements."

    def __init__(self, model: str | None = None):
        model = model or os.getenv("MANAGER_MODEL")
        super().__init__(model=model, temperature=0.4, max_tokens=2000)

    # ---- Skill rewriting ----

    def rewrite_skill(self, skill_name: str, current_content: str, patch: str) -> str:
        """Rewrite a skill markdown file incorporating the supervisor's patch."""
        prompt = f"""You are updating an operator skill markdown file used in a wellness call center for elderly people.

## Current skill: {skill_name}.md

{current_content}

## Patch from supervisor (a concrete improvement to incorporate)

{patch}

## Your task

Rewrite the FULL skill file incorporating the patch. Keep the same general structure (headings, examples, avoid sections). Keep what was already good. Only change what the patch requires.

Output ONLY the new markdown content. No commentary, no fences."""

        return self.chat(
            [{"role": "user", "content": prompt}],
            temperature=0.4,
            max_tokens=1500,
        ).strip()

    # ---- Full call cycle ----

    def run_call_cycle(
        self,
        senior_id: str,
        console: Console | None = None,
        voice_mode: bool = False,
        allow_no_consent: bool = False,
    ) -> dict[str, Any]:
        """Run one full cycle: call → review → skill updates → learnings → report.

        Set `voice_mode=True` to use ElevenLabs TTS for the Operator and the
        microphone + Whisper for the Senior side instead of the persona LLM.

        Set `allow_no_consent=True` to bypass the consent gate in development
        (refuses to run if RODO scopes are missing or revoked otherwise).

        Returns a summary dict with paths to artifacts created.
        """
        # Lazy imports to break a circular dependency:
        # conversation.session -> agents.operator -> agents/__init__ -> manager.
        from ..conversation.session import CallSession
        from ..conversation.transcript import format_transcript
        from ..reports.generator import ReportGenerator
        from ..compliance import (
            AuditLog,
            ConsentStatus,
            ConsentStore,
            ReviewQueue,
            redact_pii,
        )
        from ..compliance.consent import (
            SCOPE_PROCESS_HEALTH_DATA,
            SCOPE_SHARE_WITH_FAMILY,
            SCOPE_STORE_TRANSCRIPT,
            SCOPE_TRAIN_ON_TRANSCRIPTS,
            SCOPE_TRANSCRIBE,
        )

        console = console or Console()
        store = SeniorStore()
        loader = SkillsLoader()
        updater = SkillsUpdater()
        audit = AuditLog()
        consent_store = ConsentStore()

        if not store.exists(senior_id):
            raise FileNotFoundError(f"Senior {senior_id!r} does not exist.")

        profile = store.load(senior_id)

        # --- Phase 0: consent gate ---
        consent = consent_store.load(senior_id)
        required_scopes = [SCOPE_STORE_TRANSCRIPT, SCOPE_SHARE_WITH_FAMILY]
        if voice_mode:
            required_scopes.append(SCOPE_TRANSCRIBE)
        missing = [s for s in required_scopes if not consent.covers(s)]

        if consent.status == ConsentStatus.REVOKED:
            audit.record(
                "call_blocked",
                actor="manager",
                senior_id=senior_id,
                details={"reason": "consent_revoked"},
            )
            raise RuntimeError(
                f"Consent for {senior_id!r} was REVOKED on {consent.revoked_at}. "
                f"Refusing to run a call."
            )
        if missing and not allow_no_consent:
            audit.record(
                "call_blocked",
                actor="manager",
                senior_id=senior_id,
                details={"reason": "consent_missing", "missing_scopes": missing},
            )
            raise RuntimeError(
                f"Consent missing scopes for {senior_id!r}: {missing}. "
                f"Grant via `python -m src consent grant {senior_id}` or pass "
                f"--allow-no-consent for dev."
            )
        if missing and allow_no_consent:
            console.print(
                f"[yellow]⚠ Running without consent scopes {missing} "
                f"(allow_no_consent=True). Do NOT use against real seniors.[/yellow]"
            )
            audit.record(
                "call_consent_bypassed",
                actor="manager",
                senior_id=senior_id,
                details={"missing_scopes": missing, "voice_mode": voice_mode},
            )

        health_consent = consent.covers(SCOPE_PROCESS_HEALTH_DATA)
        training_consent = consent.covers(SCOPE_TRAIN_ON_TRANSCRIPTS)

        audit.record(
            "call_started",
            actor="manager",
            senior_id=senior_id,
            details={
                "voice_mode": voice_mode,
                "consent_status": consent.status.value,
                "health_consent": health_consent,
                "training_consent": training_consent,
            },
        )

        # Snapshot prior call count BEFORE this call runs (used later to decide
        # if this call falls within the onboarding human-review window).
        prior_call_count = len(store.list_reports(senior_id))

        # --- Phase 1: the call ---
        title = "Phase 1: Call" + (" (voice)" if voice_mode else "")
        console.print(Panel(f"[bold]Calling {profile.name} ({profile.id})[/bold]", title=title))
        from ..company.state import CompanyState
        operator = OperatorAgent()
        operator.health_consent = health_consent  # type: ignore[attr-defined]
        operator.directive_note = CompanyState.load().directive.to_operator_note()
        senior_agent = None if voice_mode else SeniorPersonaAgent()
        session = CallSession(
            operator=operator,
            senior=senior_agent,
            store=store,
            console=console,
            voice_mode=voice_mode,
        )
        history = session.run(profile)

        return self.finalize_call(
            senior_id=senior_id,
            history=history,
            prior_call_count=prior_call_count,
            training_consent=training_consent,
            console=console,
        )

    def finalize_call(
        self,
        senior_id: str,
        history: list[dict[str, str]],
        prior_call_count: int,
        training_consent: bool,
        console: Console | None = None,
    ) -> dict[str, Any]:
        """Run the post-call pipeline: transcript → review → skills → report → queue.

        This is the part of `run_call_cycle` that runs *after* the conversation
        has been captured. The telephony layer calls it directly because it
        already produced the history via Twilio webhooks.
        """
        from ..conversation.transcript import format_transcript
        from ..reports.generator import ReportGenerator
        from ..compliance import (
            AuditLog,
            ConsentStatus,
            ConsentStore,
            ReviewQueue,
            redact_pii,
        )

        console = console or Console()
        store = SeniorStore()
        loader = SkillsLoader()
        updater = SkillsUpdater()
        audit = AuditLog()
        consent_store = ConsentStore()

        profile = store.load(senior_id)

        transcript_md = format_transcript(profile.name, history)
        transcript_path = store.save_transcript(senior_id, transcript_md)
        console.print(f"[green]Transcript saved:[/green] {transcript_path}")
        audit.record(
            "transcript_saved",
            actor="manager",
            senior_id=senior_id,
            details={"path": str(transcript_path), "turns": len(history)},
        )

        # --- Phase 2: supervisor review ---
        console.print(Panel("Supervisor reviewing transcript", title="Phase 2: Review"))
        supervisor = SupervisorAgent()
        skills_summary = loader.assemble_prompt_section()
        feedback = supervisor.review(transcript_md, skills_summary)

        scores = feedback.get("scores", {})
        score_line = " | ".join(f"{k}: {v}" for k, v in scores.items())
        console.print(f"[bold]Scores:[/bold] {score_line}")
        for issue in feedback.get("issues", []):
            console.print(f"  [yellow]Issue:[/yellow] {issue}")

        # --- Phase 3: apply skill updates ---
        skill_updates = feedback.get("skill_updates") or []
        applied: list[str] = []
        if skill_updates and not training_consent:
            console.print(
                "[yellow]⚠ Skipping skill updates: senior has not granted "
                "`train_on_transcripts` consent. Run "
                "`consent grant <id> --scope transcribe --scope store_transcript "
                "--scope share_with_family --scope train_on_transcripts` "
                "(grant overwrites all scopes — include existing ones).[/yellow]"
            )
            audit.record(
                "skill_updates_skipped",
                actor="manager",
                senior_id=senior_id,
                details={"reason": "missing_training_consent", "count": len(skill_updates)},
            )
            skill_updates = []
        if skill_updates:
            console.print(Panel("Applying skill updates", title="Phase 3: Self-improvement"))
        for upd in skill_updates:
            skill_name = upd.get("skill")
            patch = upd.get("patch")
            if not skill_name or not patch:
                continue
            current = loader.get(skill_name)
            if current is None:
                console.print(f"  [yellow]Skipped unknown skill: {skill_name}[/yellow]")
                continue
            try:
                new_content = self.rewrite_skill(skill_name, current, patch)
                updater.update(skill_name, new_content)
                applied.append(skill_name)
                console.print(f"  [green]Updated skill:[/green] {skill_name}.md")
            except Exception as e:  # noqa: BLE001
                console.print(f"  [red]Failed to update {skill_name}: {e}[/red]")

        # --- Phase 4: persist senior-specific learnings ---
        senior_notes = feedback.get("senior_notes") or []
        if senior_notes:
            note_block = "\n".join(f"- {n}" for n in senior_notes)
            store.append_learning(senior_id, note_block)
            console.print(f"[green]Saved {len(senior_notes)} learning(s) about {profile.name}.[/green]")

        # --- Phase 5: family report (with PII redaction before persistence) ---
        console.print(Panel("Generating family report", title="Phase 5: Report"))
        reporter = ReportGenerator()
        report_md_raw = reporter.generate(profile, transcript_md, feedback)
        report_md = redact_pii(report_md_raw)
        report_path = store.save_report(senior_id, report_md)
        console.print(f"[green]Report saved:[/green] {report_path}")
        audit.record(
            "report_generated",
            actor="manager",
            senior_id=senior_id,
            details={
                "path": str(report_path),
                "redacted_chars": len(report_md_raw) - len(report_md),
            },
        )
        # --- Phase 5b: email report to family ---
        from ..notifications.email import EmailSender
        family_email = profile.family_contact.get("email", "")
        sent = EmailSender().send_report(
            to_addr=family_email,
            senior_name=profile.name,
            report_md=report_md,
            scores=scores,
        )
        if sent:
            console.print(f"[green]Report emailed to:[/green] {family_email}")
            audit.record(
                "report_emailed",
                actor="manager",
                senior_id=senior_id,
                details={"to": family_email},
            )
        elif family_email and not EmailSender().is_configured():
            console.print("[yellow]Email not configured (SMTP_HOST/USER/PASSWORD not set) — skipping.[/yellow]")

        # --- Phase 6: human-in-the-loop review queue (AI Act high-risk) ---
        # Re-read consent: if it was revoked mid-call, force a review entry.
        post_consent = consent_store.load(senior_id)
        withdrew_consent = post_consent.status == ConsentStatus.REVOKED
        reasons = ReviewQueue.needs_review(
            prior_call_count=prior_call_count,
            scores=scores,
            withdrew_consent=withdrew_consent,
            quality_threshold=QUALITY_THRESHOLD,
        )
        review_entry_id: str | None = None
        if reasons:
            entry = ReviewQueue().enqueue(
                senior_id=senior_id,
                transcript_path=transcript_path,
                report_path=report_path,
                scores=scores,
                reasons=reasons,
            )
            review_entry_id = entry.id
            console.print(Panel(
                f"[bold yellow]Human review required[/bold yellow]\n"
                f"Entry id: {entry.id}\nReasons:\n  - " + "\n  - ".join(reasons),
                title="Phase 6: Review queue",
            ))
            audit.record(
                "review_enqueued",
                actor="manager",
                senior_id=senior_id,
                details={"entry_id": entry.id, "reasons": reasons},
            )

        store.save_call_record(
            senior_id,
            scores=scores,
            report_path=report_path,
            transcript_path=transcript_path,
        )

        audit.record(
            "call_completed",
            actor="manager",
            senior_id=senior_id,
            details={
                "scores": scores,
                "skill_updates_applied": applied,
                "review_entry_id": review_entry_id,
            },
        )

        return {
            "transcript_path": str(transcript_path),
            "report_path": str(report_path),
            "scores": scores,
            "skill_updates_applied": applied,
            "senior_notes_added": senior_notes,
            "review_entry_id": review_entry_id,
            "review_reasons": reasons,
        }
