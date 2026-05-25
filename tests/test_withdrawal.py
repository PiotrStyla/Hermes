"""Tests for the mid-call withdrawal phrase detector (RODO Art. 7(3)).

These are purely deterministic — no LLM, no network.
"""

import pytest

from src.compliance.withdrawal import is_withdrawal


# ---- True positives (must detect) ----

EN_WITHDRAWALS = [
    "I withdraw my consent",
    "I withdraw consent",
    "Please don't call me again",
    "stop calling",
    "Please stop calling",
    "Remove me",
    "I want to end this call",
    "I want to end the call",
    # case insensitivity
    "STOP CALLING!",
    "I WITHDRAW MY CONSENT.",
]

PL_WITHDRAWALS = [
    "Wycofuję moją zgodę",
    "Wycofuje zgodę",
    "Nie zgadzam się",
    "Proszę nie dzwonić do mnie więcej",
    "Nie dzwonić więcej",
    "Koniec rozmowy",
    "Rozłączam się",
    "Nie chcę tej rozmowy",
    "Proszę nie nagrywać",
    # mixed case
    "KONIEC ROZMOWY",
    "wYcOfUjĘ ZgOdĘ",
]

@pytest.mark.parametrize("text", EN_WITHDRAWALS + PL_WITHDRAWALS)
def test_true_positives(text: str) -> None:
    assert is_withdrawal(text), f"Expected withdrawal detection for: {text!r}"


# ---- True negatives (must NOT detect) ----

NOT_WITHDRAWALS = [
    "",
    "How are you today?",
    "I feel a little tired but okay.",
    "My foot is sore",                  # Polish "stopa" false-positive guard
    "Yes, I'm fine thank you.",
    "Can you repeat that?",
    "That sounds good.",
    "Dobry dzień pani!",
    "Dziękuję bardzo.",
    "Boli mnie noga.",
    "Zgadzam się z tobą.",             # "Nie zgadzam się" variant guard
    "I want to talk more",
    "I want to end this sandwich",     # partial match guard
]

@pytest.mark.parametrize("text", NOT_WITHDRAWALS)
def test_true_negatives(text: str) -> None:
    assert not is_withdrawal(text), f"False positive for: {text!r}"


# ---- Edge cases ----

def test_none_empty_string() -> None:
    assert not is_withdrawal("")


def test_withdrawal_embedded_in_sentence() -> None:
    assert is_withdrawal("Actually, I withdraw my consent right now.")


def test_polish_embedded() -> None:
    assert is_withdrawal("Przepraszam ale wycofuję zgodę na te rozmowy.")
