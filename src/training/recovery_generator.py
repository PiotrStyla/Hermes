"""Distraction & resumption generator — Stage 3 training.

Conclusions from training reports (data/training/report_*.json):

1. The Operator handles the *moment* of an interruption reasonably well
   (warmth/listening stay high), but consistently FAILS TO RESUME and
   complete the mandatory wellness checklist afterwards. This is the single
   biggest, most recurring weakness — `info_quality` collapses (e.g. avg
   dropped 7.8 -> 4.9 between two runs) and free-text issues repeat:
   "Did not complete the mandatory safety block ... due to emergency",
   "after the glass-breaking sound, the call restarted and ... lacked it".

2. Stages 1 (emergencies) and 2 (sounds) test DETECTION/REACTION. They do
   NOT explicitly test RECOVERY. The skills files even mandate resumption
   ("after the senior stabilises you must resume with the safety block
   immediately"), yet it is rarely measured.

Therefore Stage 3 targets RECOVERY specifically: a benign distraction pulls
the senior away mid-call (doorbell, boiling pot, phone, etc.), then the
senior returns. The Operator must gracefully resume and COMPLETE the
checklist. Coverage is measured deterministically by ChecklistTracker.
"""

from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass
class DistractionEvent:
    name: str
    leave_phrase: str   # senior announces they must step away briefly
    return_phrase: str  # senior comes back to the call
    category: str


DISTRACTION_EVENTS: list[DistractionEvent] = [
    DistractionEvent(
        name="Dzwonek do drzwi",
        leave_phrase="Chwileczkę, ktoś dzwoni do drzwi, muszę zobaczyć kto to...",
        return_phrase="Już jestem, to był tylko listonosz. O czym to rozmawialiśmy?",
        category="visitor",
    ),
    DistractionEvent(
        name="Kipi mleko",
        leave_phrase="Ojej, mleko mi kipi na kuchni! Sekundkę...",
        return_phrase="Uff, już zdjęłam garnek. Przepraszam, słucham?",
        category="kitchen",
    ),
    DistractionEvent(
        name="Dzwoni telefon stacjonarny",
        leave_phrase="Moment, dzwoni mój drugi telefon, zaraz wracam...",
        return_phrase="Już, to pomyłka. Kontynuujmy.",
        category="phone",
    ),
    DistractionEvent(
        name="Czajnik gwiżdże",
        leave_phrase="Czajnik gwiżdże, muszę go wyłączyć, chwileczkę...",
        return_phrase="Dobrze, herbata się robi. Tak, słucham pana.",
        category="kitchen",
    ),
    DistractionEvent(
        name="Pies się dobija",
        leave_phrase="Piesek drapie w drzwi, muszę go wpuścić na moment...",
        return_phrase="Już go wpuściłam, leży grzecznie. Proszę mówić dalej.",
        category="pet",
    ),
    DistractionEvent(
        name="Wnuki przyszły",
        leave_phrase="Aaa, wnuki właśnie weszły! Daj mi chwilę, przywitam się...",
        return_phrase="Już się przywitałam, poszły do pokoju. To gdzie skończyliśmy?",
        category="family",
    ),
    DistractionEvent(
        name="Upuszczony telefon",
        leave_phrase="(trzask) Ojej, upuściłam telefon... halo? Słychać mnie?",
        return_phrase="Już go podniosłam, przepraszam za to. Słucham?",
        category="device",
    ),
    DistractionEvent(
        name="Za głośny telewizor",
        leave_phrase="Moment, ten telewizor za głośno gra, ścieszę go...",
        return_phrase="Już ciszej, teraz się dobrze rozumiemy. Proszę mówić.",
        category="noise",
    ),
    DistractionEvent(
        name="Sąsiad puka",
        leave_phrase="Sąsiadka puka, pewnie po cukier, dam jej sekundę...",
        return_phrase="Załatwione, to faktycznie po cukier. Wracajmy do rozmowy.",
        category="visitor",
    ),
    DistractionEvent(
        name="Coś się wylało",
        leave_phrase="Och, rozlałam herbatę na stół, muszę szybko wytrzeć...",
        return_phrase="Już wytarte. Przepraszam, na czym stanęliśmy?",
        category="accident",
    ),
]


class RecoveryScenarioGenerator:
    """Generates benign distractions that test conversation resumption."""

    def __init__(self, seed: int | None = None, distraction_probability: float = 0.6):
        self.rng = random.Random(seed)
        self.distraction_probability = distraction_probability

    def should_inject_distraction(self) -> bool:
        return self.rng.random() < self.distraction_probability

    def generate(self) -> tuple[DistractionEvent, int]:
        """Return (distraction, turn_number). Injected mid-call (turns 4-9)."""
        distraction = self.rng.choice(DISTRACTION_EVENTS)
        turn = self.rng.randint(4, 9)
        return distraction, turn
