"""Tests for ScenarioGenerator and TrainingLoop."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.training.scenario_generator import ARCHETYPES, ScenarioGenerator


class TestScenarioGenerator:
    def test_generates_persona_and_profile(self) -> None:
        gen = ScenarioGenerator(seed=42)
        persona_md, profile = gen.generate()
        assert persona_md.startswith("# ")
        assert "## Cechy charakteru" in persona_md
        assert "## Dzisiejszy nastrój" in persona_md
        assert profile.name
        assert profile.age > 0
        assert profile.language == "pl"

    def test_seed_reproducibility(self) -> None:
        gen1 = ScenarioGenerator(seed=123)
        gen2 = ScenarioGenerator(seed=123)
        p1, _ = gen1.generate()
        p2, _ = gen2.generate()
        assert p1 == p2

    def test_different_seeds_differ(self) -> None:
        gen1 = ScenarioGenerator(seed=1)
        gen2 = ScenarioGenerator(seed=999)
        p1, _ = gen1.generate()
        p2, _ = gen2.generate()
        # Very unlikely to match across 10 archetypes
        assert p1 != p2 or len(ARCHETYPES) == 1

    def test_all_archetypes_have_required_fields(self) -> None:
        for arch in ARCHETYPES:
            assert arch.name
            assert arch.age_range[0] < arch.age_range[1]
            assert arch.traits
            assert arch.speaking_style
            assert arch.common_concerns
            assert arch.mood_variants


class TestTrainingLoop:
    def test_instantiation(self) -> None:
        from src.training.loop import TrainingLoop
        loop = TrainingLoop(rounds=1, seed=42)
        assert loop.rounds == 1
        assert len(loop.metrics) == 0

    def test_avg_scores_empty(self) -> None:
        from src.training.loop import TrainingLoop
        loop = TrainingLoop(rounds=0)
        assert loop._avg_scores() == {}

    def test_metrics_dataclass(self) -> None:
        from src.training.loop import TrainingMetrics
        m = TrainingMetrics(
            round=1,
            archetype="Test",
            scores={"warmth": 8, "listening": 7},
            skill_updates=["greeting"],
            duration_s=1.5,
        )
        assert m.round == 1
        assert m.scores["warmth"] == 8


class TestEmergencyScenarioGenerator:
    def test_generates_emergency(self) -> None:
        from src.training.emergency_generator import EmergencyScenarioGenerator
        gen = EmergencyScenarioGenerator(seed=42, emergency_probability=1.0)
        emerg, turn = gen.generate()
        assert emerg.name
        assert emerg.trigger_phrase
        assert emerg.severity in ("low", "medium", "high", "critical")
        assert 3 <= turn <= 8

    def test_inject_into_history(self) -> None:
        from src.training.emergency_generator import EmergencyScenarioGenerator, EmergencyType
        gen = EmergencyScenarioGenerator(seed=42)
        history = [
            {"role": "operator", "content": "Hello"},
            {"role": "senior", "content": "Hi"},
            {"role": "operator", "content": "How are you?"},
            {"role": "senior", "content": "Fine"},
        ]
        emerg = EmergencyType("Test", "Emergency!", "high", "Response", "test")
        new_history = gen.inject_into_history(history, 2, emerg)
        assert len(new_history) == 5
        assert new_history[3]["content"] == "Emergency!"

    def test_emergency_probability(self) -> None:
        from src.training.emergency_generator import EmergencyScenarioGenerator
        gen_never = EmergencyScenarioGenerator(seed=42, emergency_probability=0.0)
        gen_always = EmergencyScenarioGenerator(seed=42, emergency_probability=1.0)
        assert not gen_never.should_inject_emergency()
        assert gen_always.should_inject_emergency()

    def test_all_emergency_types_have_required_fields(self) -> None:
        from src.training.emergency_generator import EMERGENCY_TYPES
        for emerg in EMERGENCY_TYPES:
            assert emerg.name
            assert emerg.trigger_phrase
            assert emerg.severity
            assert emerg.expected_response
            assert emerg.category


class TestSoundEventGenerator:
    def test_generates_sound(self) -> None:
        from src.training.sound_generator import SoundEventGenerator
        gen = SoundEventGenerator(seed=42, sound_probability=1.0)
        sound, turn = gen.generate()
        assert sound.name
        assert sound.description
        assert sound.severity in ("low", "medium", "high", "critical")
        assert 2 <= turn <= 10

    def test_sound_probability(self) -> None:
        from src.training.sound_generator import SoundEventGenerator
        gen_never = SoundEventGenerator(seed=42, sound_probability=0.0)
        gen_always = SoundEventGenerator(seed=42, sound_probability=1.0)
        assert not gen_never.should_inject_sound()
        assert gen_always.should_inject_sound()

    def test_format_sound_announcement(self) -> None:
        from src.training.sound_generator import SoundEventGenerator, SoundEvent
        gen = SoundEventGenerator(seed=42)
        sound = SoundEvent("Test", "Test desc", "high", "Response", "test")
        announcement = gen.format_sound_announcement(sound)
        assert "DŹWIĘK" in announcement
        assert "TEST" in announcement

    def test_all_sound_events_have_required_fields(self) -> None:
        from src.training.sound_generator import SOUND_EVENTS
        for sound in SOUND_EVENTS:
            assert sound.name
            assert sound.description
            assert sound.severity
            assert sound.expected_response
            assert sound.category
