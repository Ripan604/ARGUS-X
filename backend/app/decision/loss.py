from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class DecisionLossConfig:
    false_negative: float = 12.0
    false_positive: float = 3.0
    additional_experiment: float = 0.20
    movement_per_normalized_unit: float = 0.35
    excitation_energy: float = 0.12
    time_per_second: float = 0.08
    escalation: float = 1.4
    abstention: float = 0.8

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_json(cls, path: str | Path) -> "DecisionLossConfig":
        return cls(**json.loads(Path(path).read_text(encoding="utf-8")))


class DecisionLossModel:
    """Research-only decision loss; never a maintenance certification rule."""

    ACTIONS = (
        "CONTINUE_INSPECTION", "LOCALIZE_MORE", "ESCALATE_TO_REFERENCE_METHOD",
        "MARK_REGION_FOR_REVIEW", "ABSTAIN", "END_RESEARCH_SESSION",
    )

    def __init__(self, config: DecisionLossConfig | None = None) -> None:
        self.config = config or DecisionLossConfig()

    def current_risk(self, confidence: float, ood_score: float, credible_area: float) -> float:
        miss_probability = float(np.clip(1 - confidence + 0.45 * ood_score, 0, 1))
        false_alarm_probability = float(np.clip(credible_area * (1 - confidence), 0, 1))
        return self.config.false_negative * miss_probability + self.config.false_positive * false_alarm_probability

    def expected_reduction(self, current_risk: float, information_gain: float, separation: float, model_trust: float) -> float:
        fraction = float(np.clip((0.08 * information_gain + 0.40 * separation) * model_trust, 0, 0.75))
        return current_risk * fraction

    def experiment_cost(self, movement: float, amplitude: float, duration_s: float) -> float:
        energy = amplitude**2 * duration_s
        return (
            self.config.additional_experiment
            + self.config.movement_per_normalized_unit * movement
            + self.config.excitation_energy * energy
            + self.config.time_per_second * duration_s
        )

    def recommended_research_action(self, risk: float, ood_status: str, should_stop: bool) -> str:
        if ood_status == "ABSTAIN":
            return "ABSTAIN"
        if ood_status == "OUT_OF_DISTRIBUTION":
            return "ESCALATE_TO_REFERENCE_METHOD"
        if should_stop and risk < 0.5:
            return "END_RESEARCH_SESSION"
        if risk > 3.0:
            return "LOCALIZE_MORE"
        return "MARK_REGION_FOR_REVIEW"

