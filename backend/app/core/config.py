from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal


PlannerObjective = Literal[
    "INFORMATION_GAIN",
    "BAYES_RISK",
    "WORST_CASE_AMBIGUITY",
    "MEASUREMENT_COMPRESSION",
    "MULTIOBJECTIVE",
]


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
    profile: str = "demo"
    planner_objective: PlannerObjective = "MULTIOBJECTIVE"
    planner_risk_weight: float = 0.55
    planner_calibration_weight: float = 0.65
    planner_model_trust_weight: float = 0.30
    planner_time_weight: float = 0.08
    planner_horizon: int = 1
    planner_beam_width: int = 4
    planner_rollout_samples: int = 6
    metrology_calibration_threshold: float = 0.62
    dual_control_value_margin: float = 0.05
    ood_caution_threshold: float = 0.55
    ood_abstain_threshold: float = 0.82
    minimum_evidence_weight: float = 0.08
    maximum_frequency_hz: float = 7_000.0
    maximum_amplitude: float = 0.75
    maximum_duration_s: float = 0.35
    minimum_probe_spacing: float = 0.10
    expected_value_stop_threshold: float = 0.035
    credible_region_stop_fraction: float = 0.035
    bayes_risk_stop_threshold: float = 0.12
    forward_cache_size: int = 8_192
    research_seed: int = 71
    enable_nuisance_inference: bool = True
    enable_discrepancy_model: bool = True
    enable_calibration_actions: bool = True
    enable_ood_layer: bool = True
    enable_waveform_optimization: bool = True
    enable_multifidelity_controller: bool = True

    def to_dict(self) -> dict:
        return asdict(self)


DEFAULT_CONFIG = ArgusConfig()


CONFIG_PROFILES: dict[str, dict] = {
    "demo": {"candidate_count": 36, "planner_horizon": 1, "planner_beam_width": 3},
    "research": {"candidate_count": 72, "planner_horizon": 2, "planner_beam_width": 5},
    "phone": {"candidate_count": 30, "planner_horizon": 1, "maximum_frequency_hz": 7_000.0},
    "distributed": {"candidate_count": 48, "planner_horizon": 2},
    "benchmark": {"candidate_count": 36, "planner_horizon": 1},
}


def config_for_profile(profile: str, **overrides) -> ArgusConfig:
    """Return a centralized, reproducible configuration profile."""

    if profile not in CONFIG_PROFILES:
        raise ValueError(f"Unknown ARGUS profile: {profile}")
    return ArgusConfig(profile=profile, **CONFIG_PROFILES[profile], **overrides)
