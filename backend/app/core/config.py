from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class ArgusConfig:
    grid_size: int = 20
    sample_rate: int = 16_000
    signal_duration: float = 0.12
    max_experiments: int = 12
    confidence_threshold: float = 0.72
    entropy_threshold: float = 0.38
    candidate_count: int = 48
    top_hypotheses: int = 24
    likelihood_temperature: float = 4.8
    seed: int = 7
    planner_information_weight: float = 1.0
    planner_disagreement_weight: float = 0.35
    planner_cost_weight: float = 0.16
    planner_repetition_weight: float = 0.22

    def to_dict(self) -> dict:
        return asdict(self)


DEFAULT_CONFIG = ArgusConfig()
