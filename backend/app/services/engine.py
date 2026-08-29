from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from backend.app.active_learning.planner import ExperimentPlanner, PlannedExperiment
from backend.app.core.config import ArgusConfig
from backend.app.hardware.devices import SimulationDevice
from backend.app.inference.belief import BeliefState
from backend.app.models.domain import Defect, Experiment, Material, Panel, physical_distance
from backend.app.signal.processing import analyze_signal
from backend.app.simulation.physics import AcousticSimulator


@dataclass
class ExperimentResult:
    index: int
    parameters: Experiment
    signal: np.ndarray
    analysis: dict
    posterior_before: np.ndarray
    posterior_after: np.ndarray
    likelihood: np.ndarray
    diagnostics: dict[str, float]
    recommendation: PlannedExperiment


@dataclass
class ArgusEngine:
    config: ArgusConfig = field(default_factory=ArgusConfig)
    panel: Panel = field(default_factory=Panel)
    material: Material = field(default_factory=Material)
    seed: int = 7
    preset: str = "medium"
    truth: Defect | None = None

    def __post_init__(self) -> None:
        self.simulator = AcousticSimulator(self.panel, self.material, self.config.sample_rate, self.seed)
        if self.truth is None:
            self.truth = self.simulator.random_defect(self.preset)
        self.material = self.simulator.material
        self.belief = BeliefState(self.config.grid_size)
        self.planner = ExperimentPlanner(self.simulator, self.config, self.seed + 10_000)
        self.simulation_device = SimulationDevice(self.simulator, self.truth)
        self.simulation_device.connect()
        self.experiments: list[Experiment] = []
        self.results: list[ExperimentResult] = []
        self.current_recommendation = self.planner.recommend(self.belief.posterior, self.experiments)

    def run_recommended(self) -> ExperimentResult:
        return self.run_experiment(self.current_recommendation.selected.experiment, self.current_recommendation)

    def run_experiment(self, experiment: Experiment, recommendation: PlannedExperiment | None = None) -> ExperimentResult:
        recommendation = recommendation or self.planner.recommend(self.belief.posterior, self.experiments)
        signal = self.simulation_device.acquire(experiment, self.config.sample_rate)
        return self.process_signal(signal, experiment, recommendation)

    def process_signal(
        self,
        signal: np.ndarray,
        experiment: Experiment,
        recommendation: PlannedExperiment | None = None,
    ) -> ExperimentResult:
        recommendation = recommendation or self.planner.recommend(self.belief.posterior, self.experiments)
        before = self.belief.posterior.copy()
        likelihood, diagnostics = self.belief.update(
            signal, experiment, self.simulator, temperature=self.config.likelihood_temperature
        )
        self.experiments.append(experiment)
        result = ExperimentResult(
            index=len(self.experiments),
            parameters=experiment,
            signal=signal,
            analysis=analyze_signal(signal, self.config.sample_rate),
            posterior_before=before,
            posterior_after=self.belief.posterior.copy(),
            likelihood=likelihood,
            diagnostics=diagnostics,
            recommendation=recommendation,
        )
        self.results.append(result)
        self.current_recommendation = self.planner.recommend(self.belief.posterior, self.experiments)
        return result

    def status(self) -> dict:
        estimate = self.belief.estimate()
        stop_reason = None
        if estimate["confidence"] >= self.config.confidence_threshold:
            stop_reason = "confidence_threshold"
        elif estimate["normalized_entropy"] <= self.config.entropy_threshold:
            stop_reason = "entropy_threshold"
        elif len(self.experiments) >= self.config.max_experiments:
            stop_reason = "max_experiments"
        return {**estimate, "experiment_count": len(self.experiments), "should_stop": stop_reason is not None, "stop_reason": stop_reason}

    def localization_error(self) -> float:
        estimate = self.belief.estimate()
        return float(physical_distance(estimate["map_x"], estimate["map_y"], self.truth.center_x, self.truth.center_y, self.panel))
