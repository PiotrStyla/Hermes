"""Base agent class for the multi-agent system."""

from __future__ import annotations

import os
import time
from typing import Any

from openai import OpenAI, APIStatusError

from ..llm import apply_prompt_cache


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
        max_tokens: int = 1024,
    ):
        self.model = model or os.getenv("DEFAULT_MODEL", "deepseek/deepseek-v4-flash")
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

        max_retries = 3

        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                )
                result = response.choices[0].message.content or ""
                self.conversation_history.append({"task": task, "result": result})
                return result
            except APIStatusError as e:
                if e.status_code == 429 and attempt < max_retries - 1:
                    wait = 30 * (attempt + 1)
                    print(f"  Rate limited, retrying in {wait}s...")
                    time.sleep(wait)
                    continue
                raise

    def chat(
        self,
        messages: list[dict[str, Any]],
        temperature: float | None = None,
        max_tokens: int | None = None,
        cache_system_prompt: bool = False,
        cache_ttl: str = "1h",
    ) -> str:
        """Send a list of messages and return the assistant reply.

        Used for multi-turn conversations where the caller manages history.

        When `cache_system_prompt=True`, the system message is rewritten into
        Anthropic-style structured blocks with `cache_control` markers (the
        helper is a no-op for non-Anthropic models, so it's always safe to
        enable). Use `cache_ttl="5m"` or `"1h"` (1h is recommended for
        skills-heavy agents — see `src/llm/prompt_cache.py`).
        """
        if cache_system_prompt:
            messages = apply_prompt_cache(messages, self.model, ttl=cache_ttl)

        max_retries = 3
        last_error: APIStatusError | None = None

        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature if temperature is not None else self.temperature,
                    max_tokens=max_tokens if max_tokens is not None else self.max_tokens,
                )
                return response.choices[0].message.content or ""
            except APIStatusError as e:
                last_error = e
                if e.status_code == 429 and attempt < max_retries - 1:
                    wait = 30 * (attempt + 1)
                    print(f"  Rate limited, retrying in {wait}s...")
                    time.sleep(wait)
                    continue
                raise

        if last_error is not None:
            raise last_error
        raise RuntimeError("chat() failed without error")

    def reset(self) -> None:
        """Clear conversation history."""
        self.conversation_history.clear()
