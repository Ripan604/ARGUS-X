from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np

from backend.app.core.config import ArgusConfig
from backend.app.inference.belief import entropy, spatial_mode_cells
from backend.app.models.domain import Experiment
from backend.app.simulation.physics import AcousticSimulator


@dataclass(frozen=True)
class CandidateScore:
    experiment: Experiment
    expected_information_gain: float
    hypothesis_disagreement: float
    uncertainty_coverage: float
    experiment_cost: float
    repetition_penalty: float
    final_score: float
    expected_risk_reduction: float = 0.0
    calibration_value: float = 0.0
    model_trust: float = 1.0
    time_cost: float = 0.0
    energy_cost: float = 0.0
    feasibility: bool = True
    rejection_reasons: tuple[str, ...] = ()
    chosen_model_fidelity: int = 1
    reason_for_fidelity: str = "Existing physics-inspired signature model"
    predicted_uncertainty_after: float | None = None
    waveform_utility: float = 0.0
    baseline_guard_utility: float = 0.0

    def to_dict(self) -> dict:
        return {"experiment": self.experiment.to_dict(), **{k: v for k, v in asdict(self).items() if k != "experiment"}}


@dataclass(frozen=True)
class PlannedExperiment:
    selected: CandidateScore
    top_candidates: tuple[CandidateScore, ...]
    explanation: str
    strategy: str = "counterfactual_disagreement"
    action_type: str = "diagnostic"
    objective: str = "INFORMATION_GAIN"
    structured_explanation: dict | None = None
    chosen_model_fidelity: int = 1
    reason_for_fidelity: str = "Existing physics-inspired signature model"
    planning_horizon: int = 1

    def to_dict(self) -> dict:
        return {
            "experiment": self.selected.experiment.to_dict(),
            "expected_information_gain": self.selected.expected_information_gain,
            "hypothesis_disagreement": self.selected.hypothesis_disagreement,
            "uncertainty_coverage": self.selected.uncertainty_coverage,
            "experiment_cost": self.selected.experiment_cost,
            "repetition_penalty": self.selected.repetition_penalty,
            "planner_score": self.selected.final_score,
            "explanation": self.explanation,
            "strategy": self.strategy,
            "action_type": self.action_type,
            "objective": self.objective,
            "chosen_model_fidelity": self.chosen_model_fidelity,
            "reason_for_fidelity": self.reason_for_fidelity,
            "planning_horizon": self.planning_horizon,
            "structured_explanation": self.structured_explanation or {
                "action_type": self.action_type,
                "primary_reason": self.explanation,
                "expected_information_gain": self.selected.expected_information_gain,
                "expected_risk_reduction": self.selected.expected_risk_reduction,
                "hypothesis_separation": self.selected.hypothesis_disagreement,
                "movement_cost": self.selected.experiment_cost,
                "energy_cost": self.selected.energy_cost,
                "model_trust": self.selected.model_trust,
                "calibration_value": self.selected.calibration_value,
                "predicted_uncertainty_after": self.selected.predicted_uncertainty_after,
            },
            "top_candidates": [candidate.to_dict() for candidate in self.top_candidates],
        }


def hypothesis_disagreement(signatures: np.ndarray, weights: np.ndarray) -> float:
    if len(signatures) < 2:
        return 0.0
    scaled = signatures.copy()
    scaled[:, 0] /= 0.00018
    scaled[:, 1] /= 0.55
    delta = scaled[:, None, :] - scaled[None, :, :]
    squared_distance = np.sum(delta**2, axis=-1)
    distinguishability = 1.0 - np.exp(-0.5 * squared_distance)
    pair_weight = weights[:, None] * weights[None, :]
    return float(np.sum(pair_weight * distinguishability))


def expected_information_gain(current_entropy_bits: float, disagreement: float, represented_mass: float) -> float:
    # Bounded mutual-information proxy derived from the overlap of predicted
    # Gaussian responses under the leading discrete hypotheses.
    return float(max(0.0, current_entropy_bits * represented_mass * disagreement))


class ExperimentPlanner:
    def __init__(self, simulator: AcousticSimulator, config: ArgusConfig, seed: int | None = None) -> None:
        self.simulator = simulator
        self.config = config
        self.rng = np.random.default_rng(config.seed if seed is None else seed)

    def generate_candidates(
        self,
        posterior: np.ndarray,
        history: list[Experiment],
        count: int | None = None,
    ) -> list[Experiment]:
        target_count = count or self.config.candidate_count
        grid_size = posterior.shape[0]
        hypothesis_points = [
            ((column + 0.5) / grid_size, (row + 0.5) / grid_size)
            for row, column in spatial_mode_cells(posterior, min(8, posterior.size), max(2, grid_size // 8))
        ]
        perimeter = [
            (0.06, 0.06), (0.50, 0.04), (0.94, 0.06), (0.96, 0.50),
            (0.94, 0.94), (0.50, 0.96), (0.06, 0.94), (0.04, 0.50),
        ]
        sources = perimeter + hypothesis_points
        receivers = perimeter[::2] + [(0.5, 0.5)]
        bands = [(1_200.0, 3_000.0), (2_200.0, 4_400.0), (3_400.0, 6_200.0)]
        waveforms = ["chirp", "impulse", "chirp"]
        candidates: list[Experiment] = []
        offset = len(history)
        for index in range(target_count * 2):
            source = sources[(index * 5 + offset * 3) % len(sources)]
            receiver = receivers[(index * 3 + 1 + offset) % len(receivers)]
            if np.hypot(source[0] - receiver[0], source[1] - receiver[1]) < 0.16:
                receiver = receivers[(index * 3 + 2 + offset) % len(receivers)]
            band_index = (index + offset) % len(bands)
            band = bands[band_index]
            candidate = Experiment(
                source_x=source[0], source_y=source[1],
                receiver_x=receiver[0], receiver_y=receiver[1],
                frequency_start_hz=band[0], frequency_end_hz=band[1],
                amplitude=0.42 + 0.06 * ((index + 1) % 3),
                duration_s=0.12,
                waveform=waveforms[band_index],
            )
            key = tuple(round(v, 4) if isinstance(v, float) else v for v in candidate.to_dict().values())
            if all(tuple(round(v, 4) if isinstance(v, float) else v for v in c.to_dict().values()) != key for c in candidates):
                candidates.append(candidate)
            if len(candidates) >= target_count:
                break
        return candidates

    def score_candidates(self, posterior: np.ndarray, candidates: list[Experiment], history: list[Experiment]) -> list[CandidateScore]:
        grid_size = posterior.shape[0]
        cells = spatial_mode_cells(posterior, min(self.config.top_hypotheses, posterior.size), 1)
        indices = np.asarray([row * grid_size + column for row, column in cells], dtype=int)
        flat = posterior.ravel()
        xs = (indices % grid_size + 0.5) / grid_size
        ys = (indices // grid_size + 0.5) / grid_size
        raw_weights = flat[indices]
        represented_mass = float(np.sum(raw_weights))
        weights = raw_weights / (represented_mass + 1e-12)
        current_entropy = entropy(posterior)
        scores: list[CandidateScore] = []
        for candidate in candidates:
            signatures = self.simulator.predicted_signature(xs, ys, candidate)
            disagreement = hypothesis_disagreement(signatures, weights)
            eig = expected_information_gain(current_entropy, disagreement, represented_mass)
            source_distance = np.hypot(xs - candidate.source_x, ys - candidate.source_y)
            receiver_distance = np.hypot(xs - candidate.receiver_x, ys - candidate.receiver_y)
            coverage = float(np.sum(weights * np.exp(-2.2 * np.minimum(source_distance, receiver_distance))))
            cost = self._experiment_cost(candidate, history)
            repetition = self._repetition_penalty(candidate, history)
            final = (
                self.config.planner_information_weight * eig
                + self.config.planner_disagreement_weight * disagreement
                + 0.22 * coverage
                - self.config.planner_cost_weight * cost
                - self.config.planner_repetition_weight * repetition
            )
            scores.append(CandidateScore(candidate, eig, disagreement, coverage, cost, repetition, float(final)))
        return sorted(scores, key=lambda item: item.final_score, reverse=True)

    def recommend(self, posterior: np.ndarray, history: list[Experiment]) -> PlannedExperiment:
        candidates = self.generate_candidates(posterior, history)
        scored = self.score_candidates(posterior, candidates, history)
        selected = scored[0]
        explanation = self._explain(selected, posterior, history)
        return PlannedExperiment(selected, tuple(scored[:5]), explanation)

    def random_experiment(self) -> Experiment:
        source = self.rng.uniform(0.04, 0.96, 2)
        receiver = self.rng.uniform(0.04, 0.96, 2)
        start = float(self.rng.choice([1_200, 2_200, 3_400]))
        return Experiment(
            float(source[0]), float(source[1]), float(receiver[0]), float(receiver[1]),
            start, min(6_500.0, start + 2_000), 0.48, 0.12, "chirp",
        )

    @staticmethod
    def _experiment_cost(candidate: Experiment, history: list[Experiment]) -> float:
        energy = candidate.amplitude**2 * candidate.duration_s / 0.12
        if not history:
            motion = 0.0
        else:
            previous = history[-1]
            source_motion = np.hypot(candidate.source_x - previous.source_x, candidate.source_y - previous.source_y)
            receiver_motion = np.hypot(candidate.receiver_x - previous.receiver_x, candidate.receiver_y - previous.receiver_y)
            motion = source_motion + receiver_motion
        return float(0.52 * energy + 0.48 * motion / (2 * np.sqrt(2)))

    @staticmethod
    def _repetition_penalty(candidate: Experiment, history: list[Experiment]) -> float:
        if not history:
            return 0.0
        penalties = []
        for previous in history:
            source_delta = np.hypot(candidate.source_x - previous.source_x, candidate.source_y - previous.source_y)
            receiver_delta = np.hypot(candidate.receiver_x - previous.receiver_x, candidate.receiver_y - previous.receiver_y)
            frequency_delta = abs(candidate.center_frequency_hz - previous.center_frequency_hz) / 3_000
            # Reusing either endpoint preserves substantial geometric
            # ambiguity, so repetition must include both source and receiver.
            endpoint_overlap = np.sqrt(np.exp(-6 * source_delta) * np.exp(-6 * receiver_delta))
            penalties.append(endpoint_overlap * np.exp(-2 * frequency_delta))
        return float(max(penalties))

    @staticmethod
    def _explain(candidate: CandidateScore, posterior: np.ndarray, history: list[Experiment]) -> str:
        normalized_entropy = entropy(posterior, normalized=True)
        if candidate.hypothesis_disagreement > 0.62:
            reason = "The current belief contains competing regions; their predicted echo delays separate strongly under this geometry."
        elif normalized_entropy > 0.72:
            reason = "Uncertainty is still broad, and this source-receiver path covers high-probability territory while producing distinct responses."
        else:
            reason = "This measurement resolves the remaining local ambiguity around the leading defect hypothesis."
        if history and candidate.repetition_penalty < 0.25:
            reason += " It also avoids repeating the recent probe geometry and frequency band."
        return reason
