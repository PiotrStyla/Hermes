"""Researcher agent - gathers information and context."""

from __future__ import annotations

import os

from .base import BaseAgent


class ResearcherAgent(BaseAgent):
    """Agent specialized in research, information gathering, and fact verification.

    Capabilities:
    - Web search and document analysis
    - Fact verification and source evaluation
    - Summarizing findings into structured context
    """

    role = "researcher"
    description = "Specialized in gathering, analyzing, and verifying information."

    def __init__(self, model: str | None = None):
        model = model or os.getenv("RESEARCHER_MODEL")
        super().__init__(model=model, temperature=0.3)

    @property
    def system_prompt(self) -> str:
        return """You are a Research Agent in a multi-agent system.

Your role:
- Gather relevant information for a given task
- Analyze and verify facts from multiple angles
- Provide structured, well-sourced context for other agents
- Flag uncertainties and knowledge gaps

Output format:
- Start with a brief summary of findings
- List key facts with confidence levels (high/medium/low)
- Note any gaps or areas needing further investigation
- Provide sources when available

Be thorough but concise. Other agents depend on your research quality."""
