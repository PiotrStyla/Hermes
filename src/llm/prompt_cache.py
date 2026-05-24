"""Anthropic-style prompt-cache helper.

Anthropic supports caching the prefix of a request via `cache_control` markers
on content blocks. Cache writes cost 1.25× (5min TTL) or 2.0× (1h TTL); cache
reads cost 0.10×, so heavy reuse pays off quickly.

In March 2026 Anthropic silently changed the default ephemeral TTL from 1h to
5min — to keep the longer window we set `ttl` explicitly. The public docs
accept both `"5m"` / `"1h"` strings and we use the string form here.

This helper is **provider-aware**:
- For `anthropic/...` models (whether through OpenRouter or the native SDK),
  it converts a system message's plain-string content into a list of typed
  blocks and tags the LAST stable block with `cache_control`.
- For any other provider (DeepSeek, OpenAI, Google, ...) it is a no-op so
  callers can flip the flag without conditional code.

OpenRouter passes the `cache_control` field straight through to Anthropic.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Iterable

CACHE_DELIMITER = "\n\n<!-- HERMES_CACHE_BREAKPOINT -->\n\n"
"""Marker callers can embed in a system prompt string to indicate where the
stable / dynamic split happens. Everything BEFORE the marker is cached;
everything after is treated as per-call dynamic data.
"""


def is_anthropic_model(model: str | None) -> bool:
    """Return True for any model id that should receive Anthropic cache markers.

    Covers OpenRouter (`anthropic/claude-...`), Vertex (`claude-...@...`),
    AWS Bedrock (`...anthropic.claude-...`), and the native Anthropic SDK
    (`claude-...`).
    """
    if not model:
        return False
    m = model.lower()
    return (
        m.startswith("anthropic/")
        or m.startswith("claude-")
        or "anthropic.claude" in m
    )


def split_system_message(content: str, delimiter: str = CACHE_DELIMITER) -> tuple[str, str]:
    """Split a system prompt into (stable, dynamic) on the delimiter.

    If the delimiter isn't present, the whole string is treated as STABLE
    (and dynamic is empty). This keeps the helper safe for prompts that
    haven't been migrated yet.
    """
    if delimiter in content:
        stable, dynamic = content.split(delimiter, 1)
        return stable.strip(), dynamic.strip()
    return content, ""


def apply_prompt_cache(
    messages: Iterable[dict[str, Any]],
    model: str,
    ttl: str = "1h",
) -> list[dict[str, Any]]:
    """Return a copy of `messages` with cache markers added when applicable.

    For Anthropic models with a string-typed system message, the system
    content is split on `CACHE_DELIMITER` and rewritten as two text blocks:

        [
          {"type": "text", "text": <stable>,
           "cache_control": {"type": "ephemeral", "ttl": ttl}},
          {"type": "text", "text": <dynamic>},
        ]

    The dynamic block is omitted when empty. If the system content is already
    a list of blocks, only the last block gets a cache_control tag (caller is
    assumed to know what they're doing).

    For all other providers, returns `messages` unchanged.
    """
    msgs = [deepcopy(m) for m in messages]
    if not is_anthropic_model(model):
        return msgs

    for msg in msgs:
        if msg.get("role") != "system":
            continue
        content = msg.get("content", "")

        if isinstance(content, str):
            stable, dynamic = split_system_message(content)
            if not stable:
                continue
            blocks: list[dict[str, Any]] = [{
                "type": "text",
                "text": stable,
                "cache_control": {"type": "ephemeral", "ttl": ttl},
            }]
            if dynamic:
                blocks.append({"type": "text", "text": dynamic})
            msg["content"] = blocks
        elif isinstance(content, list) and content:
            # Already structured — tag the last block as the cache breakpoint.
            last = content[-1]
            if isinstance(last, dict) and last.get("type") == "text":
                last.setdefault("cache_control", {"type": "ephemeral", "ttl": ttl})
        # else: unsupported content shape, leave alone.
        # Only the FIRST system message gets the marker; we don't expect more.
        break

    return msgs
