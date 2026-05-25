"""Tests for OperatorAgent.build_system_prompt structure.

We don't make LLM calls here — we only verify that the prompt string has the
right shape: stable part first, delimiter, dynamic part second.
"""

from __future__ import annotations

import pytest

from src.agents.operator import OperatorAgent
from src.llm.prompt_cache import CACHE_DELIMITER
from src.seniors.store import SeniorProfile


@pytest.fixture()
def operator() -> OperatorAgent:
    return OperatorAgent()


@pytest.fixture()
def english_profile() -> SeniorProfile:
    return SeniorProfile(
        id="test-en",
        name="Alice",
        age=78,
        language="en",
        conditions=["arthritis"],
        medications=["ibuprofen"],
        preferences={"tone": "friendly"},
        family_contact={"name": "Bob", "email": "bob@example.com"},
        notes="Likes cats.",
        phone_number="+15005550001",
    )


@pytest.fixture()
def polish_profile() -> SeniorProfile:
    return SeniorProfile(
        id="test-pl",
        name="Jadwiga",
        age=81,
        language="pl",
        conditions=["nadciśnienie"],
        medications=["amlodypina"],
        preferences={"tone": "ciepły"},
        family_contact={"name": "Marek", "email": "marek@example.com"},
        notes="Lubi wnuki.",
        phone_number="+48123456789",
    )


# ---- Delimiter and split ----

def test_prompt_contains_delimiter(operator, english_profile) -> None:
    prompt = operator.build_system_prompt(english_profile, "")
    assert CACHE_DELIMITER in prompt


def test_prompt_splits_into_two_parts(operator, english_profile) -> None:
    prompt = operator.build_system_prompt(english_profile, "")
    parts = prompt.split(CACHE_DELIMITER, 1)
    assert len(parts) == 2
    stable, dynamic = parts
    assert len(stable) > 0
    assert len(dynamic) > 0


# ---- Stable block: must be identical across different seniors ----

def test_stable_block_identical_for_different_seniors(operator, english_profile, polish_profile) -> None:
    """The stable part (skills + output rules) must be bit-for-bit equal.
    This is the whole point — one Anthropic cache write serves all seniors."""
    stable_en = operator.build_system_prompt(english_profile, "").split(CACHE_DELIMITER, 1)[0]
    stable_pl = operator.build_system_prompt(polish_profile, "").split(CACHE_DELIMITER, 1)[0]
    assert stable_en == stable_pl


def test_stable_block_contains_skills(operator, english_profile) -> None:
    stable = operator.build_system_prompt(english_profile, "").split(CACHE_DELIMITER, 1)[0]
    assert "wellness-check operator" in stable


def test_stable_block_contains_output_rules(operator, english_profile) -> None:
    stable = operator.build_system_prompt(english_profile, "").split(CACHE_DELIMITER, 1)[0]
    assert "Output rules" in stable
    assert "<<END_CALL>>" in stable
    assert "disclosure" in stable


def test_stable_block_does_not_contain_senior_name(operator, english_profile) -> None:
    stable = operator.build_system_prompt(english_profile, "").split(CACHE_DELIMITER, 1)[0]
    assert english_profile.name not in stable


# ---- Dynamic block: per-senior data ----

def test_dynamic_block_contains_senior_name(operator, english_profile) -> None:
    dynamic = operator.build_system_prompt(english_profile, "").split(CACHE_DELIMITER, 1)[1]
    assert english_profile.name in dynamic


def test_dynamic_block_contains_language(operator, polish_profile) -> None:
    dynamic = operator.build_system_prompt(polish_profile, "").split(CACHE_DELIMITER, 1)[1]
    assert "Polish" in dynamic


def test_dynamic_block_contains_learnings(operator, english_profile) -> None:
    learnings = "Prefers morning calls."
    dynamic = operator.build_system_prompt(english_profile, learnings).split(CACHE_DELIMITER, 1)[1]
    assert "Prefers morning calls." in dynamic


def test_dynamic_block_no_learnings_shows_placeholder(operator, english_profile) -> None:
    dynamic = operator.build_system_prompt(english_profile, "").split(CACHE_DELIMITER, 1)[1]
    assert "no prior notes" in dynamic


# ---- Health consent flag ----

def test_health_consent_false_adds_restriction_to_dynamic(operator, english_profile) -> None:
    operator.health_consent = False
    dynamic = operator.build_system_prompt(english_profile, "").split(CACHE_DELIMITER, 1)[1]
    assert "RODO Art. 9" in dynamic
    assert "MUST NOT ask about" in dynamic


def test_health_consent_true_no_restriction(operator, english_profile) -> None:
    operator.health_consent = True
    prompt = operator.build_system_prompt(english_profile, "")
    assert "RODO Art. 9" not in prompt


def test_health_consent_restriction_not_in_stable_block(operator, english_profile) -> None:
    """Restriction is dynamic (per-senior) — must never pollute the stable cached block."""
    operator.health_consent = False
    stable = operator.build_system_prompt(english_profile, "").split(CACHE_DELIMITER, 1)[0]
    assert "RODO Art. 9" not in stable
