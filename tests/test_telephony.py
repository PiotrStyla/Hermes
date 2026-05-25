"""Tests for telephony: TelephonyConfig, CallStateStore, TwilioCallClient dry-run."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.telephony.config import TelephonyConfig
from src.telephony.session import CallState, CallStateStore
from src.telephony.twilio_client import TwilioCallClient


# ---- TelephonyConfig ----

def test_config_from_env_missing_all(monkeypatch: pytest.MonkeyPatch) -> None:
    for k in ("TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_FROM_NUMBER", "TELEPHONY_PUBLIC_URL"):
        monkeypatch.delenv(k, raising=False)
    cfg = TelephonyConfig.from_env()
    assert not cfg.is_configured()
    missing = cfg.missing_keys()
    assert "TWILIO_ACCOUNT_SID" in missing
    assert "TWILIO_AUTH_TOKEN" in missing
    assert "TWILIO_FROM_NUMBER" in missing
    assert "TELEPHONY_PUBLIC_URL" in missing


def test_config_from_env_fully_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TWILIO_ACCOUNT_SID", "ACtest123")
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "token123")
    monkeypatch.setenv("TWILIO_FROM_NUMBER", "+15005550006")
    monkeypatch.setenv("TELEPHONY_PUBLIC_URL", "https://example.ngrok.app")
    cfg = TelephonyConfig.from_env()
    assert cfg.is_configured()
    assert cfg.missing_keys() == []
    assert cfg.public_base_url == "https://example.ngrok.app"


def test_config_strips_trailing_slash(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TELEPHONY_PUBLIC_URL", "https://example.ngrok.app/")
    cfg = TelephonyConfig.from_env()
    assert not cfg.public_base_url.endswith("/")


def test_config_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    for k in ("TWILIO_MACHINE_DETECTION", "TWILIO_RECORD_MAX_SECONDS", "TWILIO_RECORD_SILENCE_SECONDS"):
        monkeypatch.delenv(k, raising=False)
    cfg = TelephonyConfig.from_env()
    assert cfg.machine_detection == "DetectMessageEnd"
    assert cfg.record_max_seconds == 20
    assert cfg.record_silence_timeout == 3


# ---- CallStateStore ----

def test_create_and_load(calls_dir: Path) -> None:
    store = CallStateStore(base_dir=calls_dir)
    state = store.create(
        call_sid="CA123",
        senior_id="test-001",
        operator_system_prompt="You are...",
        record_audio_consent=False,
        health_consent=True,
        training_consent=False,
    )
    assert state.call_sid == "CA123"
    assert state.senior_id == "test-001"
    assert state.status == "initiated"

    loaded = store.load("CA123")
    assert loaded.call_sid == "CA123"
    assert loaded.senior_id == "test-001"
    assert loaded.health_consent is True
    assert loaded.record_audio_consent is False


def test_load_missing_raises(calls_dir: Path) -> None:
    store = CallStateStore(base_dir=calls_dir)
    with pytest.raises(FileNotFoundError):
        store.load("nonexistent-sid")


def test_exists(calls_dir: Path) -> None:
    store = CallStateStore(base_dir=calls_dir)
    assert not store.exists("nope")
    store.create("CA456", "s-001", "", False, True, False)
    assert store.exists("CA456")


def test_save_and_reload(calls_dir: Path) -> None:
    store = CallStateStore(base_dir=calls_dir)
    state = store.create("CA789", "s-001", "prompt", False, True, False)
    state.history.append({"role": "operator", "content": "Hello!"})
    state.turn_count = 1
    store.save(state)
    loaded = store.load("CA789")
    assert loaded.turn_count == 1
    assert loaded.history[0]["content"] == "Hello!"


def test_mark_ended(calls_dir: Path) -> None:
    store = CallStateStore(base_dir=calls_dir)
    state = store.create("CAabc", "s-002", "", False, False, False)
    store.mark_ended(state, reason="natural_end", status="completed")
    loaded = store.load("CAabc")
    assert loaded.status == "completed"
    assert loaded.end_reason == "natural_end"
    assert loaded.ended_at is not None


def test_list_all(calls_dir: Path) -> None:
    store = CallStateStore(base_dir=calls_dir)
    store.create("CA001", "s-001", "", False, True, False)
    store.create("CA002", "s-002", "", False, True, False)
    states = store.list()
    assert len(states) == 2


def test_list_filter_by_status(calls_dir: Path) -> None:
    store = CallStateStore(base_dir=calls_dir)
    s1 = store.create("CAx01", "s-001", "", False, True, False)
    s2 = store.create("CAx02", "s-002", "", False, True, False)
    store.mark_ended(s1, reason="natural_end", status="completed")
    completed = store.list(status="completed")
    initiated = store.list(status="initiated")
    assert len(completed) == 1
    assert len(initiated) == 1
    assert completed[0].call_sid == "CAx01"


def test_call_dir_creates_subdirs(calls_dir: Path) -> None:
    store = CallStateStore(base_dir=calls_dir)
    call_dir = store.call_dir("CA_subdirtest")
    assert (call_dir / "tts").exists()
    assert (call_dir / "rec").exists()


# ---- TwilioCallClient dry_run ----

def test_dry_run_auto_enabled_when_unconfigured(monkeypatch: pytest.MonkeyPatch) -> None:
    for k in ("TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_FROM_NUMBER", "TELEPHONY_PUBLIC_URL"):
        monkeypatch.delenv(k, raising=False)
    client = TwilioCallClient()
    assert client.dry_run is True


def test_dry_run_forced_explicit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TWILIO_ACCOUNT_SID", "ACtest")
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "token")
    monkeypatch.setenv("TWILIO_FROM_NUMBER", "+15005550006")
    monkeypatch.setenv("TELEPHONY_PUBLIC_URL", "https://x.ngrok.app")
    client = TwilioCallClient(dry_run=True)
    assert client.dry_run is True


def test_dry_run_initiate_call_returns_fake_sid(monkeypatch: pytest.MonkeyPatch) -> None:
    for k in ("TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_FROM_NUMBER", "TELEPHONY_PUBLIC_URL"):
        monkeypatch.delenv(k, raising=False)
    client = TwilioCallClient()
    result = client.initiate_call("+15005550006", call_id_param="abc123")
    assert result.dry_run is True
    assert "abc123" in result.call_sid


def test_dry_run_delete_recording_returns_true(monkeypatch: pytest.MonkeyPatch) -> None:
    for k in ("TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_FROM_NUMBER", "TELEPHONY_PUBLIC_URL"):
        monkeypatch.delenv(k, raising=False)
    client = TwilioCallClient()
    assert client.delete_recording("RE_fake_sid") is True
