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
    ) -> dict[str, Any]:
        """Run one full cycle: call → review → skill updates → learnings → report.

        Set `voice_mode=True` to use ElevenLabs TTS for the Operator and the
        microphone + Whisper for the Senior side instead of the persona LLM.

        Returns a summary dict with paths to artifacts created.
        """
        # Lazy imports to break a circular dependency:
        # conversation.session -> agents.operator -> agents/__init__ -> manager.
        from ..conversation.session import CallSession
        from ..conversation.transcript import format_transcript
        from ..reports.generator import ReportGenerator

        console = console or Console()
        store = SeniorStore()
        loader = SkillsLoader()
        updater = SkillsUpdater()

        if not store.exists(senior_id):
            raise FileNotFoundError(f"Senior {senior_id!r} does not exist.")

        profile = store.load(senior_id)

        # --- Phase 1: the call ---
        title = "Phase 1: Call" + (" (voice)" if voice_mode else "")
        console.print(Panel(f"[bold]Calling {profile.name} ({profile.id})[/bold]", title=title))
        operator = OperatorAgent()
        senior_agent = None if voice_mode else SeniorPersonaAgent()
        session = CallSession(
            operator=operator,
            senior=senior_agent,
            store=store,
            console=console,
            voice_mode=voice_mode,
        )
        history = session.run(profile)

        transcript_md = format_transcript(profile.name, history)
        transcript_path = store.save_transcript(senior_id, transcript_md)
        console.print(f"[green]Transcript saved:[/green] {transcript_path}")

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

        # --- Phase 5: family report ---
        console.print(Panel("Generating family report", title="Phase 5: Report"))
        reporter = ReportGenerator()
        report_md = reporter.generate(profile, transcript_md, feedback)
        report_path = store.save_report(senior_id, report_md)
        console.print(f"[green]Report saved:[/green] {report_path}")

        return {
            "transcript_path": str(transcript_path),
            "report_path": str(report_path),
            "scores": scores,
            "skill_updates_applied": applied,
            "senior_notes_added": senior_notes,
        }
