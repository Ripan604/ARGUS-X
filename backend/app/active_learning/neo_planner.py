from __future__ import annotations

import json
from time import perf_counter

import numpy as np

from backend.app.active_learning.counterfactual import CounterfactualAnalysis, CounterfactualExperimentEngine
from backend.app.active_learning.horizon import RecedingHorizonPlanner
from backend.app.active_learning.planner import CandidateScore, ExperimentPlanner, PlannedExperiment
from backend.app.active_learning.waveform_optimizer import WaveformGeometryOptimizer
from backend.app.core.config import ArgusConfig
from backend.app.decision.loss import DecisionLossModel
from backend.app.digital_twin.discrepancy import OnlineDiscrepancyModel
from backend.app.digital_twin.forward_models import AnalyticalForwardModel, PhysicsSignatureModel
from backend.app.digital_twin.multifidelity import MultiFidelityController
from backend.app.inference.belief import entropy
from backend.app.inference.joint_state import JointInferenceState
from backend.app.models.domain import Experiment
from backend.app.safety.constraints import ExperimentConstraintEngine, NoGoRegion
from backend.app.simulation.physics import AcousticSimulator


class NeoExperimentPlanner:
    """Counterfactual, risk-aware, constrained and short-horizon planner."""

    def __init__(
        self,
        simulator: AcousticSimulator,
        config: ArgusConfig,
        discrepancy: OnlineDiscrepancyModel,
        seed: int = 71,
    ) -> None:
        self.simulator = simulator
        self.config = config
        self.baseline = ExperimentPlanner(simulator, config, seed)
        self.counterfactual = CounterfactualExperimentEngine()
        self.waveforms = WaveformGeometryOptimizer(seed + 1)
        self.constraints = ExperimentConstraintEngine(config)
        self.loss = DecisionLossModel()
        self.fidelity = MultiFidelityController()
        self.horizon = RecedingHorizonPlanner()
        self.discrepancy = discrepancy
        self.models = {
            0: AnalyticalForwardModel(simulator, config.forward_cache_size),
            1: PhysicsSignatureModel(simulator, config.forward_cache_size),
        }
        self.last_diagnostics: dict = {}

    @staticmethod
    def _key(experiment: Experiment) -> str:
        return json.dumps(experiment.to_dict(), sort_keys=True, separators=(",", ":"))

    def generate_candidates(
        self,
        state: JointInferenceState,
        history: list[Experiment],
        *,
        mode: str = "fast",
    ) -> list[Experiment]:
        baseline = self.baseline.generate_candidates(state.structural.posterior, history, self.config.candidate_count)
        if not self.config.enable_waveform_optimization:
            return baseline
        return self.waveforms.expand(baseline, "research" if mode == "research" else "fast", maximum=max(self.config.candidate_count, 24))

    def recommend(
        self,
        state: JointInferenceState,
        history: list[Experiment],
        *,
        action_type: str = "diagnostic",
        objective: str | None = None,
        no_go_regions: list[NoGoRegion] | None = None,
        unavailable_actions: set[str] | None = None,
        mode: str = "fast",
        candidate_override: list[Experiment] | None = None,
    ) -> PlannedExperiment:
        started = perf_counter()
        objective = objective or self.config.planner_objective
        candidates = candidate_override if candidate_override is not None else self.generate_candidates(state, history, mode=mode)
        hypotheses = state.structural.top_hypotheses(min(5, self.config.top_hypotheses))
        represented = sum(item["probability"] for item in hypotheses) + 1e-12
        hypotheses = [{**item, "probability": item["probability"] / represented} for item in hypotheses]
        structural_summary = state.structural.uncertainty_summary()
        estimate = state.structural.estimate()
        model_trust = float(state.discrepancy_state.get("model_trust", 1.0))
        current_risk = self.loss.current_risk(
            float(estimate["confidence"]), float(state.ood_state.get("score", 0.0)),
            float(state.structural.credible_region(0.90)["area_fraction"]),
        )
        scored: list[CandidateScore] = []
        analyses: dict[str, CounterfactualAnalysis] = {}
        rejected: list[dict] = []
        previous = history[-1] if history else None
        for candidate in candidates:
            constraint = self.constraints.evaluate(
                candidate, no_go_regions=no_go_regions,
                unavailable_actions=unavailable_actions,
            )
            if not constraint.feasible:
                rejected.append({"experiment": candidate.to_dict(), "reasons": list(constraint.reasons)})
                continue
            fidelity = self.fidelity.choose(
                structural_uncertainty=float(structural_summary["combined"]),
                hypothesis_ambiguity=float(structural_summary["competing_hypothesis_ambiguity"]),
                model_trust=model_trust,
                frequency_hz=candidate.center_frequency_hz,
            ) if self.config.enable_multifidelity_controller else self.fidelity.choose(
                structural_uncertainty=0.5, hypothesis_ambiguity=0.5, model_trust=max(model_trust, 0.5),
                frequency_hz=candidate.center_frequency_hz,
            )
            if fidelity.abstain:
                rejected.append({"experiment": candidate.to_dict(), "reasons": [fidelity.reason]})
                continue
            model = self.models.get(fidelity.level, self.models[1])
            analysis = self.counterfactual.analyze(candidate, hypotheses, state.nuisance, model)
            analyses[self._key(candidate)] = analysis
            separation = analysis.combined_separation
            information = float(entropy(state.structural.posterior, normalized=True) * separation * model_trust)
            risk_reduction = float(self.loss.expected_reduction(current_risk, information, separation, model_trust))
            source_distance = np.asarray([np.hypot(item["x"] - candidate.source_x, item["y"] - candidate.source_y) for item in hypotheses])
            receiver_distance = np.asarray([np.hypot(item["x"] - candidate.receiver_x, item["y"] - candidate.receiver_y) for item in hypotheses])
            weights = np.asarray([item["probability"] for item in hypotheses])
            coverage = float(np.sum(weights * np.exp(-2.0 * np.minimum(source_distance, receiver_distance))))
            source_motion = 0.0 if previous is None else float(np.hypot(candidate.source_x - previous.source_x, candidate.source_y - previous.source_y))
            receiver_motion = 0.0 if previous is None else float(np.hypot(candidate.receiver_x - previous.receiver_x, candidate.receiver_y - previous.receiver_y))
            movement = source_motion + receiver_motion
            remount = 0.0 if previous is None else float(source_motion > 0.05) + float(receiver_motion > 0.05)
            energy = candidate.amplitude**2 * candidate.duration_s
            experiment_cost = self.loss.experiment_cost(movement + 0.15 * remount, candidate.amplitude, candidate.duration_s)
            repetition = self.baseline._repetition_penalty(candidate, history)
            calibration_value = float(state.nuisance.predictive_variance(candidate)["magnitude"] * 0.20)
            time_cost = candidate.duration_s + 0.6 * movement + 0.12 * remount
            final = self._objective_score(
                objective, information, risk_reduction, separation, analysis.worst_case_separation,
                coverage, calibration_value, experiment_cost, repetition, energy, time_cost, model_trust,
                action_type,
            )
            scored.append(
                CandidateScore(
                    candidate, information, separation, coverage, experiment_cost, repetition, final,
                    expected_risk_reduction=risk_reduction,
                    calibration_value=calibration_value,
                    model_trust=model_trust,
                    time_cost=time_cost,
                    energy_cost=energy,
                    chosen_model_fidelity=fidelity.level,
                    reason_for_fidelity=fidelity.reason,
                    predicted_uncertainty_after=max(0.0, structural_summary["combined"] - 0.38 * information),
                )
            )
        if not scored:
            raise RuntimeError("No feasible experiment remains; revise no-go regions, device limits, or model support")
        scored.sort(key=lambda item: item.final_score, reverse=True)
        reranked, horizon_scores = self.horizon.rerank(scored, self.config.planner_horizon, self.config.planner_beam_width)
        selected = reranked[0]
        analysis = analyses[self._key(selected.experiment)]
        pair = analysis.most_separated_pair
        selected_hypotheses = [hypotheses[index] for index in pair] if len(hypotheses) > max(pair) else hypotheses[:2]
        reason = self._explain(action_type, selected, selected_hypotheses)
        structured = {
            "action_type": action_type,
            "primary_reason": reason,
            "objective": objective,
            "top_competing_hypotheses": hypotheses,
            "most_separated_hypotheses": selected_hypotheses,
            "counterfactual": analysis.to_dict(),
            "expected_information_gain": selected.expected_information_gain,
            "expected_risk_reduction": selected.expected_risk_reduction,
            "hypothesis_separation": selected.hypothesis_disagreement,
            "expected_physical_cost": selected.experiment_cost,
            "movement_cost": selected.experiment_cost,
            "energy_cost": selected.energy_cost,
            "time_cost": selected.time_cost,
            "calibration_value": selected.calibration_value,
            "model_trust": selected.model_trust,
            "uncertainty_before": structural_summary["combined"],
            "predicted_uncertainty_after": selected.predicted_uncertainty_after,
            "chosen_model_fidelity": selected.chosen_model_fidelity,
            "reason_for_fidelity": selected.reason_for_fidelity,
            "planning_horizon": self.config.planner_horizon,
            "horizon_score": horizon_scores[id(selected)].total,
            "rejected_candidate_count": len(rejected),
            "rejected_candidates": rejected[:12],
            "alternative_actions": [item.to_dict() for item in reranked[1:5]],
            "research_decision_action": self.loss.recommended_research_action(current_risk, str(state.ood_state.get("status", "NOMINAL")), False),
        }
        self.last_diagnostics = {
            "candidate_count": len(candidates),
            "feasible_count": len(scored),
            "rejected_count": len(rejected),
            "planning_seconds": perf_counter() - started,
            "objective": objective,
            "horizon": self.config.planner_horizon,
            "cache": {name: model.cache.stats() for name, model in self.models.items()},
        }
        return PlannedExperiment(
            selected,
            tuple(reranked[:5]),
            reason,
            strategy="argus_neo_counterfactual",
            action_type=action_type,
            objective=objective,
            structured_explanation=structured,
            chosen_model_fidelity=selected.chosen_model_fidelity,
            reason_for_fidelity=selected.reason_for_fidelity,
            planning_horizon=self.config.planner_horizon,
        )

    def _objective_score(
        self,
        objective: str,
        information: float,
        risk_reduction: float,
        separation: float,
        worst_case: float,
        coverage: float,
        calibration_value: float,
        experiment_cost: float,
        repetition: float,
        energy: float,
        time_cost: float,
        model_trust: float,
        action_type: str,
    ) -> float:
        penalty = self.config.planner_cost_weight * experiment_cost + self.config.planner_repetition_weight * repetition + self.config.planner_time_weight * time_cost
        if objective == "INFORMATION_GAIN":
            return information - penalty
        if objective == "BAYES_RISK":
            return self.config.planner_risk_weight * risk_reduction - penalty
        if objective == "WORST_CASE_AMBIGUITY":
            return worst_case + 0.25 * separation - penalty
        if objective == "MEASUREMENT_COMPRESSION":
            return (information + 0.25 * separation) / (1 + experiment_cost + time_cost) - 0.10 * repetition
        action_bonus = 0.18 * coverage if action_type == "exploration" else 0.08 * coverage
        return (
            self.config.planner_information_weight * information
            + self.config.planner_disagreement_weight * separation
            + self.config.planner_risk_weight * min(risk_reduction, 1.5)
            + self.config.planner_calibration_weight * calibration_value
            + self.config.planner_model_trust_weight * model_trust
            + action_bonus
            - penalty
            - 0.08 * energy
        )

    @staticmethod
    def _explain(action_type: str, selected: CandidateScore, hypotheses: list[dict]) -> str:
        if len(hypotheses) >= 2:
            rivalry = (
                f"hypotheses near ({hypotheses[0]['x']:.2f}, {hypotheses[0]['y']:.2f}) and "
                f"({hypotheses[1]['x']:.2f}, {hypotheses[1]['y']:.2f})"
            )
        else:
            rivalry = "the remaining structural hypotheses"
        return (
            f"{action_type.title()} action selected because {rivalry} predict distinguishable responses around "
            f"{selected.experiment.center_frequency_hz / 1_000:.2f} kHz (separation {selected.hypothesis_disagreement:.3f}) "
            f"after physical cost, repetition and model trust are accounted for."
        )
