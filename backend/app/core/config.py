from __future__ import annotations

from dataclasses import asdict, dataclass
import math
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

    def __post_init__(self) -> None:
        integer_fields = (
            self.grid_size, self.sample_rate, self.max_experiments, self.candidate_count,
            self.top_hypotheses, self.seed, self.planner_horizon, self.planner_beam_width,
            self.planner_rollout_samples, self.forward_cache_size, self.research_seed,
        )
        if any(isinstance(value, bool) or not isinstance(value, int) for value in integer_fields):
            raise ValueError("ARGUS count, seed, and sample-rate values must be integers")
        boolean_fields = (
            self.enable_nuisance_inference, self.enable_discrepancy_model,
            self.enable_calibration_actions, self.enable_ood_layer,
            self.enable_waveform_optimization, self.enable_multifidelity_controller,
        )
        if any(not isinstance(value, bool) for value in boolean_fields):
            raise ValueError("ARGUS feature flags must be booleans")
        numeric_values = [
            value for value in asdict(self).values()
            if isinstance(value, (int, float)) and not isinstance(value, bool)
        ]
        if any(not math.isfinite(float(value)) for value in numeric_values):
            raise ValueError("ARGUS configuration values must be finite")
        if not isinstance(self.profile, str) or self.profile not in {"demo", "research", "phone", "distributed", "benchmark"}:
            raise ValueError("Unknown ARGUS configuration profile")
        if not isinstance(self.planner_objective, str) or self.planner_objective not in {
            "INFORMATION_GAIN", "BAYES_RISK", "WORST_CASE_AMBIGUITY",
            "MEASUREMENT_COMPRESSION", "MULTIOBJECTIVE",
        }:
            raise ValueError("Unknown planner objective")
        if not 4 <= self.grid_size <= 100:
            raise ValueError("grid_size must be between 4 and 100")
        if not 1_000 <= self.sample_rate <= 384_000:
            raise ValueError("sample_rate must be between 1 kHz and 384 kHz")
        if not 0.005 <= self.signal_duration <= 10:
            raise ValueError("signal_duration must be between 5 ms and 10 s")
        if not 1 <= self.max_experiments <= 1_000:
            raise ValueError("max_experiments must be between 1 and 1000")
        if not 1 <= self.candidate_count <= 2_000 or not 1 <= self.top_hypotheses <= 2_000:
            raise ValueError("planner candidate and hypothesis counts are outside supported bounds")
        if self.likelihood_temperature <= 0:
            raise ValueError("likelihood_temperature must be positive")
        if not 0 <= self.seed <= 2_147_483_647 or not 0 <= self.research_seed <= 2_147_483_647:
            raise ValueError("random seeds must be between 0 and 2^31-1")
        probability_fields = (
            self.confidence_threshold, self.entropy_threshold,
            self.metrology_calibration_threshold, self.ood_caution_threshold,
            self.ood_abstain_threshold, self.minimum_evidence_weight,
            self.credible_region_stop_fraction,
        )
        if any(value < 0 or value > 1 for value in probability_fields):
            raise ValueError("probability and uncertainty thresholds must be in [0, 1]")
        if self.ood_abstain_threshold < self.ood_caution_threshold:
            raise ValueError("OOD abstain threshold cannot be below the caution threshold")
        if self.maximum_frequency_hz <= 0 or self.maximum_frequency_hz >= self.sample_rate / 2:
            raise ValueError("maximum_frequency_hz must be positive and below Nyquist")
        if not 0 < self.maximum_amplitude <= 1 or self.maximum_duration_s <= 0:
            raise ValueError("actuator amplitude and duration limits must be positive")
        if not 0 <= self.minimum_probe_spacing <= 2**0.5:
            raise ValueError("minimum_probe_spacing is outside the normalized panel")
        if not 1 <= self.planner_horizon <= 3 or self.planner_beam_width < 1 or self.planner_rollout_samples < 1:
            raise ValueError("planner horizon, beam width, and rollout count are invalid")
        if self.forward_cache_size < 1:
            raise ValueError("forward_cache_size must be positive")
        planner_weights = (
            self.planner_information_weight, self.planner_disagreement_weight,
            self.planner_cost_weight, self.planner_repetition_weight,
            self.planner_risk_weight, self.planner_calibration_weight,
            self.planner_model_trust_weight, self.planner_time_weight,
        )
        if any(value < 0 for value in planner_weights):
            raise ValueError("planner weights must be non-negative")
        if self.dual_control_value_margin < 0 or self.bayes_risk_stop_threshold < 0:
            raise ValueError("control and Bayes-risk thresholds must be non-negative")
        if self.expected_value_stop_threshold < -1:
            raise ValueError("expected-value stop threshold must be at least -1")

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
