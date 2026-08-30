from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

import numpy as np

from backend.app.core.config import ArgusConfig
from backend.app.inference.joint_state import JointInferenceState
from backend.app.models.domain import Experiment


ActionType = Literal["diagnostic", "calibration", "verification", "exploration"]


@dataclass(frozen=True)
class DualControlDecision:
    action_type: ActionType
    primary_reason: str
    structural_uncertainty: float
    metrology_uncertainty: float
    calibration_value: float
    diagnostic_value: float
    switching_margin: float
    dominant_metrology_component: str
    dominant_metrology_share: float
    policy: str
    calibration_type: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


class AdaptiveDualControlManager:
    """Choose whether the next action diagnoses the object or the instrument."""

    def __init__(self, config: ArgusConfig) -> None:
        self.config = config

    def choose(
        self,
        state: JointInferenceState,
        *,
        diagnostic_value: float,
        experiment_count: int,
        policy: str = "decision_theoretic",
    ) -> DualControlDecision:
        summary = state.uncertainty_summary()
        structural = float(summary["structural"]["combined"])
        metrology = float(summary["metrology"]["combined"])
        dominant = str(summary["metrology"]["dominant_component"])
        share = float(summary["metrology"]["dominant_share"])
        ood_score = float(state.ood_state.get("score", 0.0))
        model_trust = float(state.discrepancy_state.get("model_trust", 1.0))
        calibration_count = int(summary["metrology"].get("calibration_count", 0))
        diminishing_return = 1.0 / (1.0 + 0.65 * calibration_count)
        calibration_value = float(np.clip((metrology * (0.70 + 0.30 * (1 - model_trust)) + 0.35 * ood_score) * diminishing_return, 0, 1.5))
        diagnostic_value = float(np.clip(diagnostic_value * structural * model_trust, 0, 1.5))
        margin = calibration_value - diagnostic_value

        if state.ood_state.get("status") == "ABSTAIN":
            action_type: ActionType = "calibration"
            reason = "Calibration selected because the current response is out of distribution and a structural conclusion is blocked."
        elif policy == "threshold" and metrology >= self.config.metrology_calibration_threshold:
            action_type = "calibration"
            reason = f"Calibration selected because metrology uncertainty {metrology:.0%} exceeds the configured threshold."
        elif policy == "decision_theoretic" and margin > self.config.dual_control_value_margin:
            action_type = "calibration"
            reason = (
                f"Calibration selected because {dominant.replace('_', ' ')} contributes {share:.0%} of metrology uncertainty "
                f"and its expected value exceeds diagnostic value by {margin:.3f}."
            )
        elif experiment_count > 0 and structural < 0.42 and state.structural.ambiguity() < 0.50:
            action_type = "verification"
            reason = "Verification selected to challenge the leading structural hypothesis before stopping."
        elif structural > 0.82 and state.structural.ambiguity() < 0.55:
            action_type = "exploration"
            reason = "Exploration selected because the structural posterior is broad and lacks stable rival modes."
        else:
            action_type = "diagnostic"
            reason = "Diagnostic action selected because separating the leading structural hypotheses has the highest current value."

        calibration_type = self._calibration_type(dominant) if action_type == "calibration" else None
        return DualControlDecision(
            action_type, reason, structural, metrology, calibration_value, diagnostic_value,
            margin, dominant, share, policy, calibration_type,
        )

    @staticmethod
    def _calibration_type(dominant: str) -> str:
        if dominant in {"wave_velocity", "timing_offset"}:
            return "direct_path"
        if dominant in {"source_coupling", "receiver_coupling", "gain"}:
            return "coupling_repeat"
        if dominant in {"source_pose_error", "receiver_pose_error"}:
            return "phone_pose_recalibration"
        if dominant == "noise_scale":
            return "microphone_level_check"
        return "frequency_sweep"

    @staticmethod
    def calibration_experiment(calibration_type: str | None, index: int = 0) -> Experiment:
        if calibration_type == "coupling_repeat":
            return Experiment(0.05, 0.08, 0.95, 0.08, 2_200, 4_400, 0.30, 0.12, "chirp")
        if calibration_type == "phone_pose_recalibration":
            return Experiment(0.08, 0.05, 0.08, 0.95, 1_200, 3_000, 0.26, 0.12, "tone_burst")
        if calibration_type == "microphone_level_check":
            return Experiment(0.05, 0.92, 0.95, 0.92, 1_000, 2_200, 0.24, 0.10, "multisine")
        if calibration_type == "frequency_sweep":
            return Experiment(0.05, 0.50, 0.95, 0.50, 900, 6_500, 0.28, 0.16, "chirp")
        y = (0.08, 0.50, 0.92)[index % 3]
        return Experiment(0.05, y, 0.95, y, 1_200, 3_000, 0.28, 0.12, "chirp")
