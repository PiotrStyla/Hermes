"""Sound event generator for audio scenario training.

Injects unexpected sounds during conversation to train Operator to handle
alarming audio situations: break-ins, accidents, alarms, emergencies.
"""

from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass
class SoundEvent:
    name: str
    description: str
    severity: str  # low, medium, high, critical
    expected_response: str
    category: str


SOUND_EVENTS: list[SoundEvent] = [
    SoundEvent(
        name="Łomot do drzwi",
        description="Ktoś mocno puka lub wybija drzwi",
        severity="high",
        expected_response="Zachowaj spokój, zapytaj seniora czy wie kto to, czy otworzyć, nie panikuj.",
        category="intrusion",
    ),
    SoundEvent(
        name="Wybuch",
        description="Głośny huk, jak wybuch lub strzał",
        severity="critical",
        expected_response="Natychmiast zapytaj co się stało, czy senior jest bezpieczny, czy potrzebuje pomocy.",
        category="explosion",
    ),
    SoundEvent(
        name="Tłuczone szkło",
        description="Dźwięk rozbijającego się szkła",
        severity="high",
        expected_response="Zapytaj co się rozbiło, czy senior się nie skaleczył, czy jest bezpieczny.",
        category="accident",
    ),
    SoundEvent(
        name="Rozbita szyba",
        description="Szyba w oknie zostaje rozbita",
        severity="critical",
        expected_response="Zapytaj czy ktoś wszedł przez okno, czy senior jest bezpieczny, czy wezwać policję.",
        category="intrusion",
    ),
    SoundEvent(
        name="Syrena alarmowa",
        description="Alarm w mieszkaniu lub budynku",
        severity="medium",
        expected_response="Zapytaj skąd alarm, czy senior wie jak go wyłączyć, czy wszystko w porządku.",
        category="alarm",
    ),
    SoundEvent(
        name="Krzyki",
        description="Ktoś krzyczy w tle",
        severity="high",
        expected_response="Zapytaj co się dzieje, kto krzyczy, czy senior jest bezpieczny.",
        category="distress",
    ),
    SoundEvent(
        name="Sygnał pogotowia",
        description="Ambulans lub karetka w tle",
        severity="medium",
        expected_response="Zapytaj czy ktoś jest chory, czy potrzebuje pomocy, czy wezwać kogoś.",
        category="emergency",
    ),
    SoundEvent(
        name="Syrena policji",
        description="Policja w tle",
        severity="medium",
        expected_response="Zapytaj co się stało, czy senior jest bezpieczny, czy potrzebuje pomocy.",
        category="emergency",
    ),
    SoundEvent(
        name="Straż pożarna",
        description="Syrena straży pożarnej w tle",
        severity="high",
        expected_response="Zapytaj czy widzi ogień, czy jest bezpieczny, czy budynek ewakuują.",
        category="emergency",
    ),
    SoundEvent(
        name="Upadek przedmiotów",
        description="Głośny trzask przewróconych rzeczy",
        severity="medium",
        expected_response="Zapytaj co się przewróciło, czy senior nie jest uwięziony pod ciężkimi rzeczami.",
        category="accident",
    ),
]


class SoundEventGenerator:
    """Generates sound events for audio scenario training."""

    def __init__(self, seed: int | None = None, sound_probability: float = 0.5):
        self.rng = random.Random(seed)
        self.sound_probability = sound_probability

    def should_inject_sound(self) -> bool:
        return self.rng.random() < self.sound_probability

    def generate(self) -> tuple[SoundEvent, int]:
        """Return (sound_event, turn_number) when to inject."""
        sound = self.rng.choice(SOUND_EVENTS)
        turn = self.rng.randint(2, 10)  # Inject between turns 2-10
        return sound, turn

    def format_sound_announcement(self, sound: SoundEvent) -> str:
        """Format the sound event as the operator would perceive it."""
        return f"[DŹWIĘK: {sound.name.upper()}] {sound.description}"
