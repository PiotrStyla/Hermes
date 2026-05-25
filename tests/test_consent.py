"""Tests for ConsentRecord and ConsentStore (RODO consent gate)."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.compliance.consent import (
    ALL_SCOPES,
    DEFAULT_SCOPES,
    SCOPE_PROCESS_HEALTH_DATA,
    SCOPE_RECORD_AUDIO,
    SCOPE_SHARE_WITH_FAMILY,
    SCOPE_STORE_TRANSCRIPT,
    SCOPE_TRAIN_ON_TRANSCRIPTS,
    SCOPE_TRANSCRIBE,
    ConsentRecord,
    ConsentStatus,
    ConsentStore,
)


# ---- ConsentRecord unit tests ----

def test_covers_granted_scope() -> None:
    rec = ConsentRecord(
        senior_id="test-001",
        status=ConsentStatus.GRANTED,
        scopes=[SCOPE_TRANSCRIBE, SCOPE_STORE_TRANSCRIPT],
    )
    assert rec.covers(SCOPE_TRANSCRIBE)
    assert rec.covers(SCOPE_STORE_TRANSCRIPT)
    assert not rec.covers(SCOPE_RECORD_AUDIO)


def test_covers_revoked_returns_false() -> None:
    rec = ConsentRecord(
        senior_id="test-001",
        status=ConsentStatus.REVOKED,
        scopes=list(ALL_SCOPES),  # all scopes present but status is REVOKED
    )
    assert not rec.covers(SCOPE_TRANSCRIBE)
    assert not rec.covers(SCOPE_RECORD_AUDIO)


def test_covers_none_status() -> None:
    rec = ConsentRecord(senior_id="x", status=ConsentStatus.NONE)
    assert not rec.covers(SCOPE_TRANSCRIBE)


def test_default_scopes_constant() -> None:
    assert SCOPE_TRANSCRIBE in DEFAULT_SCOPES
    assert SCOPE_STORE_TRANSCRIPT in DEFAULT_SCOPES
    assert SCOPE_SHARE_WITH_FAMILY in DEFAULT_SCOPES
    assert SCOPE_RECORD_AUDIO not in DEFAULT_SCOPES
    assert SCOPE_PROCESS_HEALTH_DATA not in DEFAULT_SCOPES
    assert SCOPE_TRAIN_ON_TRANSCRIPTS not in DEFAULT_SCOPES


# ---- ConsentStore filesystem tests ----

def test_load_missing_returns_none_status(seniors_dir: Path) -> None:
    store = ConsentStore(base_dir=seniors_dir)
    rec = store.load("new-senior")
    assert rec.status == ConsentStatus.NONE
    assert rec.scopes == []


def test_grant_saves_and_loads(seniors_dir: Path) -> None:
    store = ConsentStore(base_dir=seniors_dir)
    rec = store.grant("s-001", scopes=DEFAULT_SCOPES)
    assert rec.status == ConsentStatus.GRANTED
    loaded = store.load("s-001")
    assert loaded.status == ConsentStatus.GRANTED
    assert set(loaded.scopes) == set(DEFAULT_SCOPES)
    assert loaded.granted_at is not None


def test_revoke_clears_scopes(seniors_dir: Path) -> None:
    store = ConsentStore(base_dir=seniors_dir)
    store.grant("s-002", scopes=DEFAULT_SCOPES)
    store.revoke("s-002", notes="Mid-call withdrawal.")
    loaded = store.load("s-002")
    assert loaded.status == ConsentStatus.REVOKED
    assert loaded.scopes == []
    assert loaded.revoked_at is not None
    assert "Mid-call withdrawal." in loaded.notes


def test_revoke_without_prior_grant(seniors_dir: Path) -> None:
    store = ConsentStore(base_dir=seniors_dir)
    rec = store.revoke("s-003")
    assert rec.status == ConsentStatus.REVOKED


def test_decline(seniors_dir: Path) -> None:
    store = ConsentStore(base_dir=seniors_dir)
    rec = store.decline("s-004", notes="Did not want to participate.")
    assert rec.status == ConsentStatus.DECLINED
    loaded = store.load("s-004")
    assert loaded.status == ConsentStatus.DECLINED


def test_grant_with_full_scopes(seniors_dir: Path) -> None:
    store = ConsentStore(base_dir=seniors_dir)
    store.grant("s-005", scopes=ALL_SCOPES)
    loaded = store.load("s-005")
    for scope in ALL_SCOPES:
        assert loaded.covers(scope)


def test_json_round_trip(seniors_dir: Path) -> None:
    store = ConsentStore(base_dir=seniors_dir)
    original = store.grant("s-006", method="written", language="pl")
    path = store.path_for("s-006")
    assert path.exists()
    reloaded = ConsentRecord.from_json(__import__("json").loads(path.read_text()))
    assert reloaded.senior_id == original.senior_id
    assert reloaded.status == original.status
    assert reloaded.method == "written"
    assert reloaded.language == "pl"
