"""Tests for ReviewQueue (human-in-the-loop, EU AI Act high-risk)."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.compliance.review_queue import (
    ONBOARDING_REVIEW_CALLS,
    ReviewEntry,
    ReviewQueue,
)


GOOD_SCORES = {"warmth": 9, "listening": 8, "info_quality": 8, "brevity": 9}
BAD_SCORES  = {"warmth": 4, "listening": 3, "info_quality": 6, "brevity": 8}
THRESHOLD   = 7


# ---- needs_review (pure logic, no filesystem) ----

class TestNeedsReview:
    def test_onboarding_first_call(self) -> None:
        reasons = ReviewQueue.needs_review(0, GOOD_SCORES, withdrew_consent=False)
        assert any("onboarding" in r for r in reasons)

    def test_onboarding_still_active_before_threshold(self) -> None:
        for n in range(ONBOARDING_REVIEW_CALLS):
            reasons = ReviewQueue.needs_review(n, GOOD_SCORES, withdrew_consent=False)
            assert any("onboarding" in r for r in reasons)

    def test_no_review_after_onboarding_with_good_scores(self) -> None:
        reasons = ReviewQueue.needs_review(ONBOARDING_REVIEW_CALLS, GOOD_SCORES, withdrew_consent=False)
        assert reasons == []

    def test_low_score_triggers_review(self) -> None:
        reasons = ReviewQueue.needs_review(99, BAD_SCORES, withdrew_consent=False)
        assert any("low_score" in r for r in reasons)
        assert any("warmth" in r for r in reasons)

    def test_only_axes_below_threshold_flagged(self) -> None:
        scores = {"warmth": 9, "listening": 4}
        reasons = ReviewQueue.needs_review(99, scores, withdrew_consent=False)
        flagged_axes = [r for r in reasons if "low_score" in r]
        assert all("listening" in r for r in flagged_axes)
        assert all("warmth" not in r for r in flagged_axes)

    def test_consent_withdrawal_always_triggers(self) -> None:
        reasons = ReviewQueue.needs_review(99, GOOD_SCORES, withdrew_consent=True)
        assert any("consent_withdrawal" in r for r in reasons)

    def test_multiple_reasons_combined(self) -> None:
        reasons = ReviewQueue.needs_review(0, BAD_SCORES, withdrew_consent=True)
        reason_str = " ".join(reasons)
        assert "onboarding" in reason_str
        assert "low_score" in reason_str
        assert "consent_withdrawal" in reason_str

    def test_custom_quality_threshold(self) -> None:
        scores = {"warmth": 8}
        assert ReviewQueue.needs_review(99, scores, withdrew_consent=False, quality_threshold=9)
        assert not ReviewQueue.needs_review(99, scores, withdrew_consent=False, quality_threshold=7)

    def test_non_numeric_score_ignored(self) -> None:
        scores = {"warmth": "N/A", "listening": 8}
        reasons = ReviewQueue.needs_review(99, scores, withdrew_consent=False)
        assert reasons == []


# ---- ReviewQueue filesystem CRUD ----

def test_enqueue_creates_entry(review_dir: Path) -> None:
    q = ReviewQueue(base_dir=review_dir)
    entry = q.enqueue(
        senior_id="s-001",
        transcript_path=Path("/fake/transcript.md"),
        report_path=Path("/fake/report.md"),
        scores=GOOD_SCORES,
        reasons=["onboarding_period (call #1)"],
    )
    assert entry.id
    assert entry.status == "pending"
    assert entry.senior_id == "s-001"


def test_enqueue_persists_to_disk(review_dir: Path) -> None:
    q = ReviewQueue(base_dir=review_dir)
    entry = q.enqueue("s-002", Path("/t.md"), Path("/r.md"), GOOD_SCORES, ["onboarding"])
    assert (review_dir / f"{entry.id}.json").exists()


def test_list_pending(review_dir: Path) -> None:
    q = ReviewQueue(base_dir=review_dir)
    q.enqueue("s-001", Path("/t.md"), Path("/r.md"), GOOD_SCORES, ["onboarding"])
    q.enqueue("s-002", Path("/t.md"), Path("/r.md"), GOOD_SCORES, ["low_score"])
    entries = q.list(status="pending")
    assert len(entries) == 2


def test_get_by_id(review_dir: Path) -> None:
    q = ReviewQueue(base_dir=review_dir)
    created = q.enqueue("s-001", Path("/t.md"), Path("/r.md"), GOOD_SCORES, ["onboarding"])
    loaded = q.get(created.id)
    assert loaded is not None
    assert loaded.id == created.id


def test_get_nonexistent_returns_none(review_dir: Path) -> None:
    q = ReviewQueue(base_dir=review_dir)
    assert q.get("nope") is None


def test_decide_approve(review_dir: Path) -> None:
    q = ReviewQueue(base_dir=review_dir)
    entry = q.enqueue("s-001", Path("/t.md"), Path("/r.md"), GOOD_SCORES, ["onboarding"])
    decided = q.decide(entry.id, "approved", decided_by="dr_kowalski", comment="Looks good.")
    assert decided.status == "approved"
    assert decided.decided_by == "dr_kowalski"
    assert decided.comment == "Looks good."
    assert decided.decided_at is not None

    reloaded = q.get(entry.id)
    assert reloaded.status == "approved"


def test_decide_flag(review_dir: Path) -> None:
    q = ReviewQueue(base_dir=review_dir)
    entry = q.enqueue("s-001", Path("/t.md"), Path("/r.md"), BAD_SCORES, ["low_score:warmth=4"])
    decided = q.decide(entry.id, "flagged", decided_by="supervisor")
    assert decided.status == "flagged"


def test_decide_invalid_status_raises(review_dir: Path) -> None:
    q = ReviewQueue(base_dir=review_dir)
    entry = q.enqueue("s-001", Path("/t.md"), Path("/r.md"), GOOD_SCORES, [])
    with pytest.raises(ValueError):
        q.decide(entry.id, "deleted")


def test_decide_missing_entry_raises(review_dir: Path) -> None:
    q = ReviewQueue(base_dir=review_dir)
    with pytest.raises(FileNotFoundError):
        q.decide("nonexistent", "approved")


def test_list_filter_by_status(review_dir: Path) -> None:
    q = ReviewQueue(base_dir=review_dir)
    e1 = q.enqueue("s-001", Path("/t.md"), Path("/r.md"), GOOD_SCORES, ["onboarding"])
    e2 = q.enqueue("s-002", Path("/t.md"), Path("/r.md"), GOOD_SCORES, ["onboarding"])
    q.decide(e1.id, "approved")
    pending = q.list(status="pending")
    approved = q.list(status="approved")
    assert len(pending) == 1
    assert len(approved) == 1
    assert pending[0].id == e2.id


def test_json_round_trip(review_dir: Path) -> None:
    q = ReviewQueue(base_dir=review_dir)
    entry = q.enqueue("s-999", Path("/t.md"), Path("/r.md"), BAD_SCORES, ["low_score:warmth=4"])
    raw = (review_dir / f"{entry.id}.json").read_text()
    reconstructed = ReviewEntry.from_json(__import__("json").loads(raw))
    assert reconstructed.senior_id == "s-999"
    assert reconstructed.scores == BAD_SCORES
