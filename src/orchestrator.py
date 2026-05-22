"""Multi-agent orchestrator - coordinates research, writing, and review."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

from .agents import ResearcherAgent, WriterAgent, ReviewerAgent
from .memory import SharedMemory, ContextManager


# Load environment
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

console = Console()

MAX_REVISION_ROUNDS = 3


class Orchestrator:
    """Coordinates the multi-agent workflow.

    Flow: Task → Research → Write → Review → (Revise loop) → Output
    """

    def __init__(self, persist_memory: bool = True):
        self.researcher = ResearcherAgent()
        self.writer = WriterAgent()
        self.reviewer = ReviewerAgent()

        memory_path = "memory_store/shared.json" if persist_memory else None
        self.memory = SharedMemory(persist_path=memory_path)
        self.context_mgr = ContextManager(self.memory)

    def run(self, task: str) -> str:
        """Execute the full multi-agent pipeline for a task.

        Args:
            task: The task to execute.

        Returns:
            Final polished output.
        """
        console.print(Panel(f"[bold]Task:[/bold] {task}", title="🎯 New Task"))

        # Phase 1: Research
        console.print("\n[bold blue]Phase 1: Research[/bold blue]")
        research_context = self.context_mgr.build_context_for_researcher(task)
        research = self.researcher.run(task, context=research_context)
        self.memory.put("research_output", research, source="researcher")
        console.print("[green]✓ Research complete[/green]")

        # Phase 2: Write
        console.print("\n[bold blue]Phase 2: Writing[/bold blue]")
        writer_context = self.context_mgr.build_context_for_writer(task)
        content = self.writer.run(task, context=writer_context)
        self.memory.put("writer_output", content, source="writer")
        console.print("[green]✓ Draft complete[/green]")

        # Phase 3: Review loop
        for round_num in range(1, MAX_REVISION_ROUNDS + 1):
            console.print(f"\n[bold blue]Phase 3: Review (round {round_num})[/bold blue]")
            reviewer_context = self.context_mgr.build_context_for_reviewer(task)
            review = self.reviewer.review(content, context=reviewer_context)
            self.memory.put("review_feedback", review["feedback"], source="reviewer")

            if review["decision"] == "PASS":
                console.print("[green]✓ Review PASSED[/green]")
                break

            console.print(f"[yellow]↻ Revision requested (round {round_num})[/yellow]")

            # Revise
            writer_context = self.context_mgr.build_context_for_writer(task)
            content = self.writer.run(
                f"Revise based on feedback:\n{review['feedback']}\n\nOriginal:\n{content}",
                context=writer_context,
            )
            self.memory.put("writer_output", content, source="writer")
        else:
            console.print("[yellow]⚠ Max revision rounds reached[/yellow]")

        # Output
        console.print(Panel(Markdown(content), title="📄 Final Output"))
        return content


def main():
    """CLI entry point."""
    if len(sys.argv) < 2:
        console.print("[bold]Usage:[/bold] python -m src.orchestrator \"<your task>\"")
        console.print("\n[dim]Example: python -m src.orchestrator \"Write a technical blog post about WebAssembly\"[/dim]")
        sys.exit(1)

    task = " ".join(sys.argv[1:])
    orchestrator = Orchestrator()
    orchestrator.run(task)


if __name__ == "__main__":
    main()
