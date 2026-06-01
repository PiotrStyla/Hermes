"""Generates diverse senior personas for training the Operator agent.

Template-based — no API calls needed. ~10 archetypes × randomized parameters
produce hundreds of distinct scenarios.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from ..seniors.store import SeniorProfile


@dataclass
class SeniorArchetype:
    name: str
    age_range: tuple[int, int]
    traits: list[str]
    speaking_style: str
    common_concerns: list[str]
    mood_variants: list[str]
    language: str = "pl"


ARCHETYPES: list[SeniorArchetype] = [
    SeniorArchetype(
        name="Samotna wdowa",
        age_range=(75, 85),
        traits=["łagodna", "tęskniąca za mężem", "wdzięczna za rozmowę", "czasem płaczliwa"],
        speaking_style="Cicha, mówi wolno, często wraca do wspomnień o zmarłym mężu. Używa zdrobnień.",
        common_concerns=["samotność wieczorami", "czy dzieci jeszcze pamiętają", "ból w kolanach"],
        mood_variants=["smutna i refleksyjna", "pogodna, bo dzwoniła córka", "niespokojna, bo dawno nikt nie dzwonił"],
    ),
    SeniorArchetype(
        name="Zmartwiony emeryt",
        age_range=(70, 80),
        traits=["praktyczny", "narzekający na system", "troskliwy wobec żony", "lubi politykę"],
        speaking_style="Głośny, energiczny, przerywa, lubi dygresje o polityce i emeryturach.",
        common_concerns=["ceny leków", "kolejki do lekarza", "czy ZUS wypłaci na czas"],
        mood_variants=["zdenerwowany po wiadomościach", "zadowolony, bo dostał podwyżkę emerytury", "zmartwiony stanem żony"],
    ),
    SeniorArchetype(
        name="Rozmowny dziadek",
        age_range=(72, 82),
        traits=["towarzyski", "dowcipny", "opowiada długie historie", "lubi młodzież"],
        speaking_style="Mówi dużo i szybko, łatwo odchodzi od tematu, opowiada anegdoty sprzed 40 lat.",
        common_concerns=["wnuki za mało dzwonią", "sąsiad znowu hałasuje", "co ugotować na niedzielę"],
        mood_variants=["wesoły i rozgadany", "nostalgiczny po obejrzeniu starych zdjęć", "podekscytowany wizytą wnuka"],
    ),
    SeniorArchetype(
        name="Małomówny introwertyk",
        age_range=(68, 80),
        traits=["cichy", "nieufny wobec obcych", "konkretny", "samodzielny"],
        speaking_style="Odpowiada jednym słowem, nie inicjuje tematów. Trzeba delikatnie wyciągać informacje.",
        common_concerns=["po co to komu", "czy to coś kosztuje", "wolę być sam"],
        mood_variants=["zamknięty w sobie", "lekko zirytowany pytaniami", "zaskakująco otwarty po przełamaniu lodów"],
    ),
    SeniorArchetype(
        name="Zdezorientowany",
        age_range=(78, 90),
        traits=["zapominalski", "powtarza pytania", "łagodny", "gubi wątek"],
        speaking_style="Mówi chaotycznie, pyta o to samo kilka razy, myli daty i imiona.",
        common_concerns=["jaki dziś dzień", "kto dzwoni", "czy brałem już tabletki"],
        mood_variants=["spokojnie zagubiony", "sfrustrowany własnym zapominaniem", "radosny mimo wszystko"],
    ),
    SeniorArchetype(
        name="Po kłótni z rodziną",
        age_range=(65, 78),
        traits=["zraniony", "dumny", "tęskniący za zgodą", "emocjonalny"],
        speaking_style="Początkowo oschły, potem się otwiera. Mówi z żalem, czasem podniesionym głosem.",
        common_concerns=["córka mnie nie rozumie", "chcą mnie oddać do domu starców", "nikt nie słucha"],
        mood_variants=["rozżalony i zamknięty", "gotów do płaczu", "szukający rady"],
    ),
    SeniorArchetype(
        name="Niedosłyszący",
        age_range=(75, 88),
        traits=["pogodny mimo wszystko", "prosi o powtórzenie", "mówi głośno", "docenia cierpliwość"],
        speaking_style="Mówi głośno, często prosi o powtórzenie: 'Słucham?', 'Głośniej, proszę'.",
        common_concerns=["aparat słuchowy się zepsuł", "nie słyszałem co pani mówiła", "proszę mówić wyraźniej"],
        mood_variants=["cierpliwy i wyrozumiały", "sfrustrowany niedosłuchem", "żartuje ze swojej głuchoty"],
    ),
    SeniorArchetype(
        name="Depresyjny nastrój",
        age_range=(68, 82),
        traits=["smutny", "bez energii", "pesymistyczny", "wdzięczny za zainteresowanie"],
        speaking_style="Mówi cicho, powoli, z długimi pauzami. Wszystko widzi w czarnych barwach.",
        common_concerns=["po co wstawać z łóżka", "nikt by nie zauważył gdybym umarł", "wszystko boli"],
        mood_variants=["głęboko przygnębiony", "lekko lepiej niż wczoraj", "płacze podczas rozmowy"],
    ),
    SeniorArchetype(
        name="Podejrzliwy",
        age_range=(70, 80),
        traits=["nieufny", "dociekliwy", "sprawdza intencje", "boi się oszustwa"],
        speaking_style="Zadaje dużo pytań kontrolnych. Sprawdza, czy to nie oszustwo 'na wnuczka'.",
        common_concerns=["skąd macie mój numer", "kto za to płaci", "czy to legalne"],
        mood_variants=["agresywnie podejrzliwy", "ostrożny ale ciekawy", "uspokojony po wyjaśnieniach"],
    ),
    SeniorArchetype(
        name="Wdzięczny i pogodny",
        age_range=(72, 85),
        traits=["optymistyczny", "wdzięczny", "modli się", "kocha przyrodę"],
        speaking_style="Ciepły, spokojny, często dziękuje. Mówi o wnukach, ogrodzie, pogodzie.",
        common_concerns=["czy jutro też pani zadzwoni", "mam tyle szczęścia", "zdrowie dopisuje"],
        mood_variants=["promienny i wdzięczny", "spokojny i refleksyjny", "dzieli się radosną nowiną"],
    ),
]


class ScenarioGenerator:
    """Produces (persona_md, profile) pairs for training."""

    def __init__(self, seed: int | None = None):
        self.rng = random.Random(seed)

    def generate(self) -> tuple[str, SeniorProfile]:
        arch = self.rng.choice(ARCHETYPES)
        age = self.rng.randint(*arch.age_range)
        mood = self.rng.choice(arch.mood_variants)
        concern = self.rng.choice(arch.common_concerns)
        traits_sample = self.rng.sample(arch.traits, min(3, len(arch.traits)))

        name = f"{arch.name} (wiek {age})"
        senior_id = f"train-{arch.name.lower().replace(' ', '-')[:20]}-{age}"

        persona_md = f"""# {name}

## Cechy charakteru
{chr(10).join(f'- {t}' for t in traits_sample)}

## Styl mówienia
{arch.speaking_style}

## Dzisiejszy nastrój
{mood}

## Główne zmartwienie dnia
{concern}

## Wiek
{age} lat

## Język
{arch.language}
"""

        profile = SeniorProfile(
            id=senior_id,
            name=name,
            age=age,
            language=arch.language,
            phone_number="",
            conditions=[],
            medications=[],
            preferences={},
            family_contact={},
            notes=f"Training scenario: {arch.name}. Mood: {mood}",
        )
        return persona_md, profile
