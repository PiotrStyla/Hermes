"""Tests for CallSchedule, ScheduleStore, and daemon helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.scheduling.schedule import DAYS_OF_WEEK, CallSchedule
from src.scheduling.store import ScheduleStore


# ---- CallSchedule validation ----

def test_valid_schedule() -> None:
    s = CallSchedule.new("s-001", "10:00", "Europe/Warsaw", ["mon", "wed", "fri"])
    assert s.hour == 10
    assert s.minute == 0
    assert s.timezone == "Europe/Warsaw"


def test_invalid_time_format() -> None:
    with pytest.raises(ValueError, match="HH:MM"):
        CallSchedule.new("s-001", "25:00")


def test_invalid_time_no_colon() -> None:
    with pytest.raises(ValueError, match="HH:MM"):
        CallSchedule.new("s-001", "1000")


def test_invalid_day() -> None:
    with pytest.raises(ValueError, match="Unknown day"):
        CallSchedule.new("s-001", "10:00", days_of_week=["monday"])  # must be "mon"


def test_empty_days_raises() -> None:
    """new() treats [] as 'use default', but the direct constructor must raise."""
    safe = CallSchedule.new("s-001", "09:00", days_of_week=[])
    assert safe.days_of_week == list(DAYS_OF_WEEK[:5])
    with pytest.raises(ValueError, match="must not be empty"):
        CallSchedule(
            senior_id="s-001", call_time="09:00",
            timezone="UTC", days_of_week=[],
        )


def test_apscheduler_day_of_week_string() -> None:
    s = CallSchedule.new("s-001", "08:00", days_of_week=["mon", "wed", "fri"])
    assert s.apscheduler_day_of_week == "mon,wed,fri"


def test_default_days_are_mon_to_fri() -> None:
    s = CallSchedule.new("s-001", "09:30")
    assert s.days_of_week == list(DAYS_OF_WEEK[:5])


def test_midnight_time_valid() -> None:
    s = CallSchedule.new("s-001", "00:00")
    assert s.hour == 0
    assert s.minute == 0


def test_end_of_day_time_valid() -> None:
    s = CallSchedule.new("s-001", "23:59")
    assert s.hour == 23
    assert s.minute == 59


def test_json_round_trip() -> None:
    original = CallSchedule.new("s-001", "14:30", "Europe/Warsaw", ["tue", "thu"])
    reloaded = CallSchedule.from_json(original.to_json())
    assert reloaded.call_time == "14:30"
    assert reloaded.timezone == "Europe/Warsaw"
    assert reloaded.days_of_week == ["tue", "thu"]
    assert reloaded.enabled is True


def test_summary_contains_key_info() -> None:
    s = CallSchedule.new("jadwiga-001", "10:00", "Europe/Warsaw", ["mon", "fri"])
    summary = s.summary()
    assert "jadwiga-001" in summary
    assert "10:00" in summary
    assert "Europe/Warsaw" in summary
    assert "enabled" in summary


# ---- ScheduleStore filesystem tests ----

def test_set_and_load(seniors_dir: Path) -> None:
    store = ScheduleStore(base_dir=seniors_dir)
    (seniors_dir / "s-001").mkdir()
    s = store.set("s-001", "09:00", "UTC", ["mon", "fri"])
    assert s.call_time == "09:00"
    loaded = store.load("s-001")
    assert loaded.call_time == "09:00"
    assert loaded.days_of_week == ["mon", "fri"]
    assert loaded.enabled is True


def test_load_missing_raises(seniors_dir: Path) -> None:
    store = ScheduleStore(base_dir=seniors_dir)
    with pytest.raises(FileNotFoundError, match="schedule set"):
        store.load("nobody")


def test_exists_false_then_true(seniors_dir: Path) -> None:
    store = ScheduleStore(base_dir=seniors_dir)
    assert not store.exists("s-002")
    (seniors_dir / "s-002").mkdir()
    store.set("s-002", "11:00")
    assert store.exists("s-002")


def test_set_updates_existing_preserves_enabled(seniors_dir: Path) -> None:
    store = ScheduleStore(base_dir=seniors_dir)
    (seniors_dir / "s-003").mkdir()
    store.set("s-003", "08:00", "UTC", ["mon"])
    store.set_enabled("s-003", False)
    updated = store.set("s-003", "09:00")
    assert updated.enabled is False
    assert updated.call_time == "09:00"


def test_set_updates_existing_preserves_created_at(seniors_dir: Path) -> None:
    store = ScheduleStore(base_dir=seniors_dir)
    (seniors_dir / "s-004").mkdir()
    first = store.set("s-004", "08:00")
    second = store.set("s-004", "10:00")
    assert second.created_at == first.created_at
    assert second.updated_at >= first.updated_at


def test_remove_existing(seniors_dir: Path) -> None:
    store = ScheduleStore(base_dir=seniors_dir)
    (seniors_dir / "s-005").mkdir()
    store.set("s-005", "08:00")
    assert store.remove("s-005") is True
    assert not store.exists("s-005")


def test_remove_nonexistent_returns_false(seniors_dir: Path) -> None:
    store = ScheduleStore(base_dir=seniors_dir)
    assert store.remove("nobody") is False


def test_set_enabled_and_disabled(seniors_dir: Path) -> None:
    store = ScheduleStore(base_dir=seniors_dir)
    (seniors_dir / "s-006").mkdir()
    store.set("s-006", "10:00")
    store.set_enabled("s-006", False)
    assert not store.load("s-006").enabled
    store.set_enabled("s-006", True)
    assert store.load("s-006").enabled


def test_set_enabled_missing_raises(seniors_dir: Path) -> None:
    store = ScheduleStore(base_dir=seniors_dir)
    with pytest.raises(FileNotFoundError):
        store.set_enabled("nobody", True)


def test_list_all_returns_all(seniors_dir: Path) -> None:
    store = ScheduleStore(base_dir=seniors_dir)
    for i in range(3):
        (seniors_dir / f"s-{i:03d}").mkdir()
        store.set(f"s-{i:03d}", "10:00")
    assert len(store.list_all()) == 3


def test_list_all_only_enabled(seniors_dir: Path) -> None:
    store = ScheduleStore(base_dir=seniors_dir)
    for i in range(4):
        (seniors_dir / f"s-{10 + i:03d}").mkdir()
        store.set(f"s-{10 + i:03d}", "10:00")
    store.set_enabled("s-010", False)
    store.set_enabled("s-011", False)
    enabled = store.list_all(only_enabled=True)
    assert len(enabled) == 2
    assert all(s.enabled for s in enabled)


def test_list_all_empty(seniors_dir: Path) -> None:
    store = ScheduleStore(base_dir=seniors_dir)
    assert store.list_all() == []
