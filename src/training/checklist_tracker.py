"""Deterministic wellness-checklist coverage tracker.

The training reports surfaced that the Operator's weakest, most recurring
failure is abandoning the mandatory wellness checklist — especially after an
interruption (emergency / sound / distraction). The Supervisor only judges
this qualitatively ("info_quality" + free-text issues), so there is no hard,
reproducible signal of *which* mandatory items were covered.

This module scans the operator's turns with Polish keyword matching and
reports exactly which mandatory items were covered and a completion percentage.
It is LLM-free, fast, and deterministic — ideal as a training metric.

Mandatory items (from data/skills/operator/{mood,safety,health}-checkin.md):
    mood, sleep, food, isolation, home_safety, fall_risk, health
"""

from __future__ import annotations

from dataclasses import dataclass


# Polish keyword fragments per mandatory checklist item. Matching is
# case-insensitive substring matching on operator turns only.
CHECKLIST_KEYWORDS: dict[str, list[str]] = {
    "mood": [
        "czuje", "czuj się", "czuj sie", "jak nastrój", "jak nastroj",
        "jak serce", "co słychać", "co slychac", "samopoczuci", "na duszy",
        "humor", "pogodn",
    ],
    "sleep": [
        "spał", "spal", "spała", "spala", "spało", "spalo",
        "w nocy", "wyspał", "wyspal", "sen ", "sen?", "snu", "noc była",
    ],
    "food": [
        "zjadł", "zjadl", "zjadła", "zjadla", "jadł", "jadl", "jadła", "jadla",
        "śniadan", "sniadan", "obiad", "kolacj", "jedzeni", "posiłek",
        "posilek", "coś konkretnego", "cos konkretnego",
    ],
    "isolation": [
        "sam w domu", "sama w domu", "ktoś wpada", "ktos wpada",
        "ktoś dziś", "ktos dzis", "ktoś do pan", "ktos do pan", "samotn",
        "ktoś był", "ktos byl", "ktoś odwiedz", "ktos odwiedz", "jest pan sam",
        "jest pani sama",
    ],
    "home_safety": [
        "ogrzewani", "ciepła woda", "ciepla woda", "nic się nie zepsuło",
        "nic sie nie zepsulo", "w domu wszystko", "zepsu", "prąd", "prad",
        "w porządku w domu", "w porzadku w domu",
    ],
    "fall_risk": [
        "upadk", "przewróc", "przewroc", "bezpiecznie porusz",
        "ryzyko upadku", "chodząc po domu", "chodzac po domu", "potknąć",
        "potknac", "bezpiecznie po domu",
    ],
    "health": [
        "leki", "lek ", "leków", "lekow", "tabletk", "chorob", "schorzeni",
        "ciśnieni", "cisnieni", "cukrzyc", "dawk", "lekarz", "przyjmuje pan",
        "przyjmuje pani",
    ],
}

MANDATORY_ITEMS: list[str] = list(CHECKLIST_KEYWORDS.keys())


@dataclass
class ChecklistResult:
    covered: dict[str, bool]
    completion_pct: float

    @property
    def covered_items(self) -> list[str]:
        return [k for k, v in self.covered.items() if v]

    @property
    def missed_items(self) -> list[str]:
        return [k for k, v in self.covered.items() if not v]


class ChecklistTracker:
    """Scans operator turns for coverage of mandatory wellness items."""

    def evaluate(self, history: list[dict[str, str]]) -> ChecklistResult:
        operator_text = " ".join(
            turn["content"].lower()
            for turn in history
            if turn.get("role") == "operator"
        )

        covered: dict[str, bool] = {}
        for item, keywords in CHECKLIST_KEYWORDS.items():
            covered[item] = any(kw in operator_text for kw in keywords)

        hits = sum(1 for v in covered.values() if v)
        completion = round(100.0 * hits / len(MANDATORY_ITEMS), 1)
        return ChecklistResult(covered=covered, completion_pct=completion)
