"""Base agent class for the multi-agent system."""

from __future__ import annotations

import os
from typing import Any

import httpx
from openai import OpenAI


class BaseAgent:
    """Base class for all agents in the multi-agent system.

    Each agent has its own personality (soul), model, and tool set.
    Agents communicate through a shared memory store.
    """

    role: str = "base"
    description: str = "Base agent"

    def __init__(
        self,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ):
        self.model = model or os.getenv("DEFAULT_MODEL", "anthropic/claude-opus-4.6")
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.client = self._create_client()
        self.conversation_history: list[dict[str, str]] = []

    def _create_client(self) -> OpenAI:
        """Create OpenAI-compatible client pointing to OpenRouter."""
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY not set in environment")

        return OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
            default_headers={
                "HTTP-Referer": "https://github.com/PiotrStyla/Hermes",
                "X-Title": "Hermes Multi-Agent System",
            },
        )

    @property
    def system_prompt(self) -> str:
        """System prompt defining this agent's role and behavior."""
        return f"You are a {self.role} agent. {self.description}"

    def run(self, task: str, context: dict[str, Any] | None = None) -> str:
        """Execute a task and return the result.

        Args:
            task: The task description to execute.
            context: Optional context from other agents or shared memory.

        Returns:
            The agent's response/output as a string.
        """
        messages = [{"role": "system", "content": self.system_prompt}]

        if context:
            context_str = "\n".join(f"[{k}]: {v}" for k, v in context.items())
            messages.append({
                "role": "user",
                "content": f"Context from other agents:\n{context_str}",
            })

        messages.append({"role": "user", "content": task})

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )

        result = response.choices[0].message.content or ""
        self.conversation_history.append({"task": task, "result": result})
        return result

    def reset(self) -> None:
        """Clear conversation history."""
        self.conversation_history.clear()
