"""Reviewer agent - evaluates quality and suggests improvements."""

from __future__ import annotations

import os
from typing import Any

from .base import BaseAgent


class ReviewerAgent(BaseAgent):
    """Agent specialized in quality assurance, reviewing, and improvement suggestions.

    Capabilities:
    - Evaluating content for accuracy, clarity, and completeness
    - Identifying errors, inconsistencies, or gaps
    - Providing actionable improvement suggestions
    - Deciding if output meets quality threshold
    """

    role = "reviewer"
    description = "Specialized in quality review and constructive feedback."

    def __init__(self, model: str | None = None):
        model = model or os.getenv("REVIEWER_MODEL")
        super().__init__(model=model, temperature=0.2)

    @property
    def system_prompt(self) -> str:
        return """You are a Reviewer Agent in a multi-agent system.

Your role:
- Evaluate content produced by the Writer Agent
- Check against the original research for accuracy
- Identify errors, inconsistencies, or gaps
- Provide specific, actionable improvement suggestions
- Make a clear PASS/REVISE decision

Output format:
- Overall assessment: PASS or REVISE
- Score: 1-10
- Strengths: What works well
- Issues: Specific problems found (if any)
- Suggestions: Concrete improvements (if REVISE)

Be constructive but rigorous. Quality is your responsibility."""

    def review(self, content: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """Review content and return structured feedback.

        Returns:
            Dict with keys: decision, score, feedback
        """
        result = self.run(
            f"Review the following content:\n\n{content}",
            context=context,
        )

        # Parse decision from the response
        decision = "PASS" if "PASS" in result.upper().split("\n")[0] else "REVISE"

        return {
            "decision": decision,
            "feedback": result,
            "raw_response": result,
        }
