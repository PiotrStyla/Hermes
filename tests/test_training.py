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
