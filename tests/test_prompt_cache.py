"""Tests for the Anthropic prompt-cache helper (src/llm/prompt_cache.py)."""

from __future__ import annotations

import pytest

from src.llm.prompt_cache import (
    CACHE_DELIMITER,
    apply_prompt_cache,
    is_anthropic_model,
    split_system_message,
)


# ---- is_anthropic_model ----

@pytest.mark.parametrize("model", [
    "anthropic/claude-sonnet-4",
    "anthropic/claude-3-5-sonnet-20241022",
    "anthropic/claude-opus-4",
    "claude-3-haiku-20240307",
    "claude-3-5-sonnet",
    "us.anthropic.claude-3-sonnet-20240229-v1:0",  # Bedrock
    "anthropic.claude-3-haiku-20240307-v1:0",      # Bedrock alternate
])
def test_is_anthropic_model_true(model: str) -> None:
    assert is_anthropic_model(model)


@pytest.mark.parametrize("model", [
    "deepseek/deepseek-v4-flash",
    "openai/gpt-4o",
    "google/gemini-2.5-pro",
    "meta-llama/llama-3.1-70b-instruct",
    "mistral/mistral-large",
    "",
    None,
])
def test_is_anthropic_model_false(model) -> None:
    assert not is_anthropic_model(model)


# ---- split_system_message ----

def test_split_on_delimiter() -> None:
    stable = "STABLE_INSTRUCTIONS"
    dynamic = "DYNAMIC_PER_CALL"
    combined = stable + CACHE_DELIMITER + dynamic
    s, d = split_system_message(combined)
    assert s == stable
    assert d == dynamic


def test_split_no_delimiter_returns_full_as_stable() -> None:
    content = "Just one big block of text"
    s, d = split_system_message(content)
    assert s == content
    assert d == ""


def test_split_strips_whitespace() -> None:
    content = "  stable  " + CACHE_DELIMITER + "  dynamic  "
    s, d = split_system_message(content)
    assert s == "stable"
    assert d == "dynamic"


def test_split_multiple_delimiters_uses_first() -> None:
    """Only the first occurrence splits; remaining text goes into dynamic."""
    content = "A" + CACHE_DELIMITER + "B" + CACHE_DELIMITER + "C"
    s, d = split_system_message(content)
    assert s == "A"
    assert "B" in d
    assert "C" in d


# ---- apply_prompt_cache ----

STABLE = "You are a wellness operator."
DYNAMIC = "The senior is named Test."
COMBINED = STABLE + CACHE_DELIMITER + DYNAMIC


def _make_messages(content: str = COMBINED) -> list[dict]:
    return [
        {"role": "system", "content": content},
        {"role": "user", "content": "Hello."},
    ]


def test_anthropic_model_converts_system_to_blocks() -> None:
    result = apply_prompt_cache(_make_messages(), "anthropic/claude-sonnet-4")
    system_msg = result[0]
    assert isinstance(system_msg["content"], list)
    assert len(system_msg["content"]) == 2

    stable_block = system_msg["content"][0]
    assert stable_block["type"] == "text"
    assert stable_block["text"] == STABLE
    assert stable_block["cache_control"] == {"type": "ephemeral", "ttl": "1h"}

    dynamic_block = system_msg["content"][1]
    assert dynamic_block["type"] == "text"
    assert dynamic_block["text"] == DYNAMIC
    assert "cache_control" not in dynamic_block


def test_anthropic_no_delimiter_single_cached_block() -> None:
    msgs = [{"role": "system", "content": "All stable, no delimiter"}, {"role": "user", "content": "Hi"}]
    result = apply_prompt_cache(msgs, "anthropic/claude-sonnet-4")
    blocks = result[0]["content"]
    assert len(blocks) == 1
    assert blocks[0]["cache_control"] == {"type": "ephemeral", "ttl": "1h"}


def test_deepseek_is_noop() -> None:
    msgs = _make_messages()
    result = apply_prompt_cache(msgs, "deepseek/deepseek-v4-flash")
    assert result == msgs


def test_openai_is_noop() -> None:
    msgs = _make_messages()
    result = apply_prompt_cache(msgs, "openai/gpt-4o")
    assert result == msgs


def test_user_message_unchanged() -> None:
    msgs = _make_messages()
    result = apply_prompt_cache(msgs, "anthropic/claude-sonnet-4")
    user_msg = result[1]
    assert user_msg["content"] == "Hello."
    assert user_msg["role"] == "user"


def test_custom_ttl_respected() -> None:
    msgs = _make_messages()
    result = apply_prompt_cache(msgs, "anthropic/claude-sonnet-4", ttl="5m")
    blocks = result[0]["content"]
    assert blocks[0]["cache_control"]["ttl"] == "5m"


def test_input_not_mutated() -> None:
    """apply_prompt_cache must not modify the input messages in-place."""
    msgs = _make_messages()
    original_content = msgs[0]["content"]
    apply_prompt_cache(msgs, "anthropic/claude-sonnet-4")
    assert msgs[0]["content"] == original_content


def test_already_structured_content_tagged_on_last_block() -> None:
    msgs = [{
        "role": "system",
        "content": [
            {"type": "text", "text": "First block"},
            {"type": "text", "text": "Last block"},
        ],
    }]
    result = apply_prompt_cache(msgs, "anthropic/claude-sonnet-4")
    blocks = result[0]["content"]
    assert "cache_control" not in blocks[0]
    assert blocks[1]["cache_control"] == {"type": "ephemeral", "ttl": "1h"}
