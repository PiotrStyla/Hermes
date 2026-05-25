"""Shared pytest fixtures.

Rules:
- All filesystem operations go under `tmp_path` — never touch `data/`.
- Fake API keys are set as env vars so agent constructors don't fail at import/init time.
  Tests that exercise LLM calls should mock the client (not done here —
  those paths require real network and are left for integration tests).
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def fake_api_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    """Inject placeholder credentials so BaseAgent._create_client does not raise."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-openrouter-key")
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    monkeypatch.setenv("ELEVENLABS_API_KEY", "test-elevenlabs-key")


@pytest.fixture()
def seniors_dir(tmp_path: Path) -> Path:
    """An empty tmp directory shaped like `data/seniors/`."""
    d = tmp_path / "seniors"
    d.mkdir()
    return d


@pytest.fixture()
def calls_dir(tmp_path: Path) -> Path:
    """An empty tmp directory shaped like `data/calls/`."""
    d = tmp_path / "calls"
    d.mkdir()
    return d


@pytest.fixture()
def review_dir(tmp_path: Path) -> Path:
    """An empty tmp directory shaped like `data/review_queue/`."""
    d = tmp_path / "review_queue"
    d.mkdir()
    return d


@pytest.fixture()
def sample_senior_profile():
    """A minimal in-memory SeniorProfile for use in tests that need one."""
    from src.seniors.store import SeniorProfile

    return SeniorProfile(
        id="test-001",
        name="Test Senior",
        age=75,
        language="en",
        conditions=["hypertension"],
        medications=["lisinopril"],
        preferences={"tone": "friendly", "topics_loved": ["grandchildren"]},
        family_contact={"name": "Son", "email": "son@example.com"},
        notes="Test notes.",
        phone_number="+15005550006",
    )
