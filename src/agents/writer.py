"""Writer agent - creates content based on research."""

from __future__ import annotations

import os

from .base import BaseAgent


class WriterAgent(BaseAgent):
    """Agent specialized in content creation, structuring, and formatting.

    Capabilities:
    - Drafting content based on research context
    - Structuring information clearly
    - Adapting tone and style to requirements
    """

    role = "writer"
    description = "Specialized in creating well-structured, clear content."

    def __init__(self, model: str | None = None):
        model = model or os.getenv("WRITER_MODEL")
        super().__init__(model=model, temperature=0.7)

    @property
    def system_prompt(self) -> str:
        return """You are a Writer Agent in a multi-agent system.

Your role:
- Create content based on research provided by the Research Agent
- Structure information clearly and logically
- Adapt tone and style to the task requirements
- Produce polished, ready-to-use output

Guidelines:
- Use all provided research context
- Be clear and concise
- Structure with headings, lists, and paragraphs as appropriate
- Flag any areas where research seems insufficient

You receive verified research as input. Transform it into polished output."""
