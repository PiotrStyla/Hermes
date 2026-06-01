"""Training module — self-play loop for improving Operator skills."""
from .loop import TrainingLoop
from .scenario_generator import ScenarioGenerator

__all__ = ["TrainingLoop", "ScenarioGenerator"]
