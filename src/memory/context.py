"""Context manager for building and retrieving agent context."""

from __future__ import annotations

from typing import Any

from .shared import SharedMemory


class ContextManager:
    """Manages context flow between agents.

    Determines what context each agent should receive based on
    the current task phase and previous agent outputs.
    """

    def __init__(self, memory: SharedMemory):
        self.memory = memory

    def build_context_for_researcher(self, task: str) -> dict[str, Any]:
        """Build context for the researcher agent."""
        return {
            "task": task,
            "previous_research": self.memory.get("research_output"),
        }

    def build_context_for_writer(self, task: str) -> dict[str, Any]:
        """Build context for the writer agent."""
        return {
            "task": task,
            "research": self.memory.get("research_output"),
            "review_feedback": self.memory.get("review_feedback"),
        }

    def build_context_for_reviewer(self, task: str) -> dict[str, Any]:
        """Build context for the reviewer agent."""
        return {
            "task": task,
            "research": self.memory.get("research_output"),
            "content": self.memory.get("writer_output"),
        }
