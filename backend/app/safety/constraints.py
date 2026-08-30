from __future__ import annotations

from dataclasses import asdict, dataclass
import json

import numpy as np

from backend.app.core.config import ArgusConfig
from backend.app.models.domain import Experiment


@dataclass(frozen=True)
class NoGoRegion:
    x_min: float
    y_min: float
    x_max: float
    y_max: float
    label: str = "inaccessible"

    def contains(self, x: float, y: float) -> bool:
        return self.x_min <= x <= self.x_max and self.y_min <= y <= self.y_max

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class ConstraintResult:
    feasible: bool
    reasons: tuple[str, ...]


class ExperimentConstraintEngine:
    def __init__(self, config: ArgusConfig) -> None:
        self.config = config

    def evaluate(
        self,
        experiment: Experiment,
        *,
        no_go_regions: list[NoGoRegion] | None = None,
        supported_frequency_hz: tuple[float, float] = (100.0, 7_000.0),
        unavailable_actions: set[str] | None = None,
    ) -> ConstraintResult:
        reasons: list[str] = []
        separation = float(np.hypot(experiment.source_x - experiment.receiver_x, experiment.source_y - experiment.receiver_y))
        if separation < self.config.minimum_probe_spacing:
            reasons.append("source_receiver_spacing")
        if experiment.amplitude > self.config.maximum_amplitude:
            reasons.append("amplitude_limit")
        if experiment.duration_s > self.config.maximum_duration_s:
            reasons.append("duration_limit")
        if experiment.frequency_start_hz < supported_frequency_hz[0] or experiment.frequency_end_hz > min(supported_frequency_hz[1], self.config.maximum_frequency_hz):
            reasons.append("frequency_outside_model_or_sensor_support")
        for region in no_go_regions or []:
            if region.contains(experiment.source_x, experiment.source_y):
                reasons.append(f"source_in_no_go:{region.label}")
            if region.contains(experiment.receiver_x, experiment.receiver_y):
                reasons.append(f"receiver_in_no_go:{region.label}")
        key = json.dumps(experiment.to_dict(), sort_keys=True, separators=(",", ":"))
        if unavailable_actions and key in unavailable_actions:
            reasons.append("human_rejected_or_unavailable")
        return ConstraintResult(not reasons, tuple(reasons))
