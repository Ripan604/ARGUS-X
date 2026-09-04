from __future__ import annotations

from dataclasses import dataclass, field, replace
import json
from pathlib import Path

import numpy as np
from scipy.signal import correlate, correlation_lags

from backend.app.active_learning.planner import CandidateScore, ExperimentPlanner, PlannedExperiment
from backend.app.active_learning.neo_planner import NeoExperimentPlanner
from backend.app.assurance.monitor import RuntimeAssuranceMonitor
from backend.app.control.dual_control import AdaptiveDualControlManager
from backend.app.core.config import ArgusConfig
from backend.app.decision.loss import DecisionLossModel
from backend.app.decision.stopping import StoppingEngine
from backend.app.digital_twin.discrepancy import OnlineDiscrepancyModel
from backend.app.hardware.devices import SimulationDevice
from backend.app.inference.calibration import CalibrationEngine
from backend.app.inference.diagnostics import estimate_measurement_quality
from backend.app.inference.joint_state import JointInferenceState
from backend.app.inference.structural_posterior import StructuralPosterior
from backend.app.models.domain import Defect, Experiment, Material, Panel, physical_distance
from backend.app.ood.detection import OODDetector
from backend.app.ood.acoustic_reference import AcousticReferenceMonitor
from backend.app.safety.constraints import NoGoRegion
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
    quality: dict = field(default_factory=dict)
    calibration_result: dict | None = None
    action_type: str = "diagnostic"


@dataclass
class ArgusEngine:
    config: ArgusConfig = field(default_factory=ArgusConfig)
    panel: Panel = field(default_factory=Panel)
    material: Material = field(default_factory=Material)
    seed: int = 7
    preset: str = "medium"
    truth: Defect | None = None
    acquisition_material: Material | None = None

    def __post_init__(self) -> None:
        self.simulator = AcousticSimulator(self.panel, self.material, self.config.sample_rate, self.seed)
        if self.truth is None:
            self.truth = self.simulator.random_defect(self.preset)
        self.material = self.simulator.material
        self.belief = StructuralPosterior(self.config.grid_size)
        self.joint_state = JointInferenceState.nominal(self.belief, self.material)
        self.planner = ExperimentPlanner(self.simulator, self.config, self.seed + 10_000)
        self.discrepancy_model = OnlineDiscrepancyModel()
        self.ood_detector = OODDetector(self.config.ood_caution_threshold, self.config.ood_abstain_threshold)
        reference_path = Path(__file__).resolve().parents[3] / "models" / "sim2real_acoustic_reference.json"
        self.acoustic_reference = AcousticReferenceMonitor.from_file(reference_path) if reference_path.exists() else None
        self.neo_planner = NeoExperimentPlanner(self.simulator, self.config, self.discrepancy_model, self.seed + 20_000)
        self.loss_model = DecisionLossModel()
        self.stopping_engine = StoppingEngine()
        self.assurance = RuntimeAssuranceMonitor()
        self.dual_control = AdaptiveDualControlManager(self.config)
        self.calibration_engine = CalibrationEngine()
        # Acquisition physics and inference physics must remain independent.
        # Calibration updates the inference twin; it must never rewrite the
        # hidden simulator that generates subsequent observations.
        acquisition_material = self.acquisition_material or self.material
        self.acquisition_simulator = AcousticSimulator(
            self.panel, acquisition_material, self.config.sample_rate, self.seed
        )
        if self.acquisition_material is None:
            self.acquisition_simulator.rng.bit_generator.state = self.simulator.rng.bit_generator.state
        self.simulation_device = SimulationDevice(self.acquisition_simulator, self.truth)
        self.simulation_device.connect()
        self.experiments: list[Experiment] = []
        self.results: list[ExperimentResult] = []
        self.action_history: list[str] = []
        self.prior_signals: dict[str, np.ndarray] = {}
        self.current_recommendation = self._recommend()

    def run_recommended(self) -> ExperimentResult:
        return self.run_experiment(self.current_recommendation.selected.experiment, self.current_recommendation)

    def run_experiment(self, experiment: Experiment, recommendation: PlannedExperiment | None = None) -> ExperimentResult:
        recommendation = self._resolve_recommendation(experiment, recommendation)
        if recommendation.action_type == "calibration":
            baseline = self.acquisition_simulator.simulate_baseline(experiment)
            signal = (
                baseline + self.acquisition_simulator.rng.normal(
                    0.0, self.acquisition_simulator.material.noise_std, len(baseline)
                )
            ).astype(np.float32)
        else:
            signal = self.simulation_device.acquire(experiment, self.config.sample_rate)
        return self.process_signal(signal, experiment, recommendation)

    def process_signal(
        self,
        signal: np.ndarray,
        experiment: Experiment,
        recommendation: PlannedExperiment | None = None,
        quality_context: dict | None = None,
    ) -> ExperimentResult:
        recommendation = self._resolve_recommendation(experiment, recommendation)
        before = self.belief.posterior.copy()
        analysis = analyze_signal(signal, self.config.sample_rate)
        experiment_key = json.dumps(experiment.to_dict(), sort_keys=True, separators=(",", ":"))
        prior_signal = self.prior_signals.get(experiment_key)
        quality_context = quality_context or {}
        reference_assessment = None
        sensor_id = str(quality_context.get("sensor_id", "")).lower()
        if self.acoustic_reference is not None and sensor_id and "simulation" not in sensor_id:
            reference_assessment = self.acoustic_reference.assess(analysis["features"])
        quality = estimate_measurement_quality(
            signal, prior_signal,
            acceleration_rms=quality_context.get("acceleration_deviation_g"),
            visual_position_error=quality_context.get("visual_position_error"),
        )
        evidence_weight = max(self.config.minimum_evidence_weight, quality.evidence_weight) if quality.accepted else 0.0
        calibration_result = None
        if recommendation.action_type == "calibration":
            likelihood = np.ones_like(self.belief.posterior)
            diagnostics = self._direct_path_diagnostics(signal, experiment)
            calibration_result = self.calibration_engine.update(
                self.joint_state.nuisance,
                experiment,
                self.panel,
                diagnostics,
                quality,
                str((recommendation.structured_explanation or {}).get("calibration_type", "direct_path")),
            ).to_dict()
            self.joint_state.last_calibration = calibration_result
            if calibration_result["accepted"]:
                self.synchronize_inference_material()
                calibration_residual = np.asarray([
                    diagnostics.get("peak_delay_s", 0.0)
                    - (self.material.system_delay_s + float(physical_distance(experiment.source_x, experiment.source_y, experiment.receiver_x, experiment.receiver_y, self.panel)) / self.material.wave_velocity),
                    0.0, 0.0, 0.0,
                ])
                self.ood_detector.register_calibration(calibration_residual)
                prior_trust = float(self.joint_state.discrepancy_state.get("model_trust", 0.5))
                self.joint_state.discrepancy_state = {
                    **self.joint_state.discrepancy_state,
                    "model_trust": min(0.96, prior_trust + 0.20),
                    "uncertainty": float(self.joint_state.discrepancy_state.get("uncertainty", 0.5)) * 0.68,
                    "calibration_supported": True,
                }
                prior_ood = float(self.joint_state.ood_state.get("score", 0.0))
                self.joint_state.ood_state = {
                    **self.joint_state.ood_state,
                    "score": prior_ood * 0.55,
                    "status": "NOMINAL" if prior_ood * 0.55 < self.config.ood_caution_threshold else "CAUTION",
                    "recommendation": "Calibration evidence incorporated; resume diagnostic interrogation while monitoring residuals.",
                }
            else:
                self.joint_state.ood_state = {
                    **self.joint_state.ood_state,
                    "status": "CAUTION",
                    "decision_confidence_cap": min(
                        0.35, float(self.joint_state.ood_state.get("decision_confidence_cap", 1.0))
                    ),
                    "recommendation": "Calibration acquisition failed quality checks; reacquire the reference signal.",
                }
        elif not quality.accepted:
            likelihood = np.ones_like(self.belief.posterior)
            diagnostics = {"rejected": 1.0, "evidence_weight": 0.0}
        else:
            likelihood, diagnostics = self.belief.update(
                signal,
                experiment,
                self.simulator,
                temperature=self.config.likelihood_temperature,
                evidence_weight=evidence_weight,
            )
            if self.config.enable_nuisance_inference:
                self.joint_state.nuisance.passive_quality_update(
                    analysis["features"]["noise_estimate"], quality.coupling_quality, quality.signal_quality
                )
            if self.config.enable_discrepancy_model or self.config.enable_ood_layer:
                self._update_model_diagnostics(
                    experiment,
                    diagnostics,
                    quality.evidence_weight,
                    reference_assessment.score if reference_assessment is not None else 0.0,
                )
        diagnostics.update({
            "coupling_quality": quality.coupling_quality,
            "placement_quality": quality.placement_quality,
            "signal_quality": quality.signal_quality,
            "evidence_weight": evidence_weight if recommendation.action_type != "calibration" else 0.0,
            "motion_proxy": quality_context.get("acceleration_deviation_g"),
            "visual_position_error_proxy": quality_context.get("visual_position_error"),
            "real_reference_distance": reference_assessment.distance if reference_assessment is not None else None,
            "real_reference_quantile": reference_assessment.empirical_quantile if reference_assessment is not None else None,
            "real_reference_score": reference_assessment.score if reference_assessment is not None else 0.0,
        })
        assurance_state = self.assurance.update(
            quality,
            diagnostics,
            quality_context,
            action_type=recommendation.action_type,
        )
        current_sensor = assurance_state.get("sensors", {}).get(assurance_state.get("last_update", {}).get("sensor_id", ""), {})
        sensor_status = current_sensor.get("status", "NOMINAL")
        if sensor_status == "UNRELIABLE":
            self.joint_state.ood_state = {
                **self.joint_state.ood_state,
                "score": max(self.config.ood_abstain_threshold, float(self.joint_state.ood_state.get("score", 0.0))),
                "status": "ABSTAIN",
                "decision_confidence_cap": 0.10,
                "recommendation": "The active sensing channel is unreliable; reacquire or repair it before structural interpretation.",
                "sensor_fault": current_sensor,
            }
        elif sensor_status == "DEGRADED" and self.joint_state.ood_state.get("status") == "NOMINAL":
            self.joint_state.ood_state = {
                **self.joint_state.ood_state,
                "score": max(self.config.ood_caution_threshold, float(self.joint_state.ood_state.get("score", 0.0))),
                "status": "CAUTION",
                "decision_confidence_cap": min(0.55, float(self.joint_state.ood_state.get("decision_confidence_cap", 1.0))),
                "recommendation": "Channel reliability is degraded; verify coupling or use a redundant sensor.",
                "sensor_fault": current_sensor,
            }
        self.joint_state.last_quality = quality
        self.joint_state.revision += 1
        self.experiments.append(experiment)
        result = ExperimentResult(
            index=len(self.experiments),
            parameters=experiment,
            signal=signal,
            analysis=analysis,
            posterior_before=before,
            posterior_after=self.belief.posterior.copy(),
            likelihood=likelihood,
            diagnostics=diagnostics,
            recommendation=recommendation,
            quality=quality.to_dict(),
            calibration_result=calibration_result,
            action_type=recommendation.action_type,
        )
        self.results.append(result)
        self.action_history.append(result.action_type)
        self.prior_signals[experiment_key] = np.asarray(signal, dtype=np.float32).copy()
        # There is no executable "next" action once the inspection budget is
        # exhausted.  Keeping the last recommendation makes status/evidence
        # rendering deterministic and avoids an unnecessary planner call that
        # can legitimately find no supported action at very low model trust.
        if len(self.experiments) < self.config.max_experiments:
            self.current_recommendation = self._recommend()
        return result

    def _resolve_recommendation(
        self,
        experiment: Experiment,
        recommendation: PlannedExperiment | None,
    ) -> PlannedExperiment:
        """Attach truthful planner metadata to a measured experiment.

        A caller may execute the current recommendation or explicitly override
        its geometry. An override must not inherit a pending calibration action:
        doing so would classify a diagnostic signal as a baseline and suppress
        the structural posterior update.
        """

        if recommendation is not None:
            return recommendation
        current = self.current_recommendation
        if experiment == current.selected.experiment:
            return current
        selected = self.planner.score_candidates(
            self.belief.posterior,
            [experiment],
            self.experiments,
        )[0]
        explanation = "Operator-specified diagnostic experiment; ARGUS recorded the override and updated the posterior."
        return PlannedExperiment(
            selected=selected,
            top_candidates=(selected,),
            explanation=explanation,
            strategy="human_specified",
            action_type="diagnostic",
            objective=self.config.planner_objective,
            structured_explanation={
                "action_type": "diagnostic",
                "primary_reason": explanation,
                "operator_override": True,
                "superseded_action_type": current.action_type,
                "superseded_experiment": current.selected.experiment.to_dict(),
            },
            chosen_model_fidelity=selected.chosen_model_fidelity,
            reason_for_fidelity=selected.reason_for_fidelity,
            planning_horizon=1,
        )

    def _update_model_diagnostics(
        self,
        experiment: Experiment,
        diagnostics: dict[str, float],
        quality_weight: float,
        acoustic_reference_score: float = 0.0,
    ) -> None:
        hypotheses = self.belief.top_hypotheses(5)
        observed_delay = float(diagnostics.get("peak_delay_s", 0.0))
        observed_gain = float(np.log(max(diagnostics.get("residual_rms", 1e-8), 1e-8)))
        observed_phase = 2 * np.pi * experiment.center_frequency_hz * observed_delay
        observed = np.asarray([observed_delay, observed_gain, np.sin(observed_phase), np.cos(observed_phase)])
        residual_options: list[tuple[float, np.ndarray, dict]] = []
        scale = np.asarray([0.0008, 1.2, 1.0, 1.0])
        for hypothesis in hypotheses:
            predicted = self.simulator.predicted_signature(
                np.asarray([hypothesis["x"]]), np.asarray([hypothesis["y"]]), experiment
            )[0]
            residual = observed - predicted
            residual_options.append((float(np.linalg.norm(residual / scale)), residual, hypothesis))
        _, residual, hypothesis = min(residual_options, key=lambda item: item[0])
        path = float(
            physical_distance(experiment.source_x, experiment.source_y, hypothesis["x"], hypothesis["y"], self.panel)
            + physical_distance(hypothesis["x"], hypothesis["y"], experiment.receiver_x, experiment.receiver_y, self.panel)
        )
        features = self.discrepancy_model.features(
            experiment.center_frequency_hz,
            path,
            (experiment.source_x, experiment.source_y, experiment.receiver_x, experiment.receiver_y),
        )
        correction, correction_uncertainty = self.discrepancy_model.predict(features, len(residual))
        corrected_residual = residual - correction
        confidence = float(self.belief.estimate()["confidence"])
        # Before the structure is localized, residuals are a mixture of model
        # error and hypothesis error.  Do not let an arbitrary early MAP cell
        # create a false OOD alarm; the residual becomes fully attributable to
        # the forward model as structural confidence grows.
        ood_residual = corrected_residual * confidence
        assessment = None
        if self.config.enable_ood_layer:
            assessment = self.ood_detector.assess(
                ood_residual,
                ensemble_disagreement=float(np.clip(correction_uncertainty / 0.8, 0, 1)),
                measurement_quality=quality_weight,
                acoustic_reference_score=acoustic_reference_score,
            )
            self.joint_state.ood_state = assessment.to_dict()
        may_learn = (
            not self.config.enable_ood_layer
            or (assessment is not None and assessment.status in {"NOMINAL", "CAUTION"} and quality_weight >= 0.25)
        )
        if self.config.enable_discrepancy_model and may_learn:
            # A residual is only identifiable as model discrepancy to the
            # extent that the structural hypothesis producing it is known.
            # Learning the full residual under a diffuse early posterior made
            # ordinary localization error look like sensor/model drift and
            # could trigger needless calibration after one measurement.
            discrepancy_learning_weight = float(np.clip(confidence, 0.0, 1.0))
            discrepancy_state = self.discrepancy_model.update(
                features, corrected_residual * discrepancy_learning_weight
            )
        elif self.config.enable_discrepancy_model:
            prior_state = self.joint_state.discrepancy_state
            trust_cap = 0.18 if assessment is not None and assessment.status == "ABSTAIN" else 0.35
            discrepancy_state = {
                **prior_state,
                "model_trust": min(float(prior_state.get("model_trust", 1.0)), trust_cap),
                "uncertainty": max(float(prior_state.get("uncertainty", 0.0)), 1.0 - trust_cap),
                "update_blocked_ood": True,
            }
        else:
            discrepancy_state = {
                "sample_count": 0, "recent_residual_rms": 0.0, "uncertainty": 0.0,
                "model_trust": 1.0,
            }
        discrepancy_state.update({
            "prediction_correction": correction.tolist(),
            "correction_uncertainty": correction_uncertainty,
            "last_raw_residual": residual.tolist(),
            "last_corrected_residual": corrected_residual.tolist(),
            "structural_identifiability_weight": confidence,
        })
        self.joint_state.discrepancy_state = discrepancy_state

    def _direct_path_diagnostics(self, signal: np.ndarray, experiment: Experiment) -> dict[str, float]:
        excitation = self.simulator.excitation(experiment)
        correlation = np.abs(correlate(np.asarray(signal), excitation, mode="full", method="fft"))
        lags = correlation_lags(len(signal), len(excitation), mode="full")
        positive = lags >= 0
        selected_lags, selected_corr = lags[positive], correlation[positive]
        peak_index = int(np.argmax(selected_corr))
        noise_floor = float(np.median(np.abs(signal - np.median(signal))) * 1.4826 + 1e-12)
        baseline = self.simulator.simulate_baseline(experiment)
        return {
            "peak_delay_s": float(selected_lags[peak_index] / self.config.sample_rate),
            "noise_floor": noise_floor,
            "direct_correlation_peak": float(selected_corr[peak_index]),
            "signal_rms": float(np.sqrt(np.mean(np.square(signal)))),
            "baseline_rms": float(np.sqrt(np.mean(np.square(baseline)))),
        }

    def synchronize_inference_material(self) -> None:
        """Feed calibrated nuisance means back into every inference forward model."""

        self.material = replace(
            self.material,
            wave_velocity=self.joint_state.nuisance.parameter("wave_velocity").mean,
            system_delay_s=self.joint_state.nuisance.parameter("timing_offset").mean,
            noise_std=self.joint_state.nuisance.parameter("noise_scale").mean,
        )
        self.simulator.material = self.material

    def _recommend(
        self,
        no_go_regions: list[NoGoRegion] | None = None,
        unavailable_actions: set[str] | None = None,
    ) -> PlannedExperiment:
        baseline = self.planner.recommend(self.belief.posterior, self.experiments)
        diagnostic_value = float(np.clip(baseline.selected.hypothesis_disagreement + baseline.selected.expected_information_gain / 4.0, 0, 1))
        decision = self.dual_control.choose(
            self.joint_state,
            diagnostic_value=diagnostic_value,
            experiment_count=len(self.experiments),
        )
        if not self.config.enable_calibration_actions and decision.action_type == "calibration":
            decision = replace(
                decision,
                action_type="diagnostic",
                primary_reason="Diagnostic action forced by the no-calibration ablation configuration.",
                calibration_type=None,
            )
            if float(self.joint_state.discrepancy_state.get("model_trust", 1.0)) < 0.18:
                self.joint_state.ood_state = {
                    **self.joint_state.ood_state,
                    "score": max(self.config.ood_abstain_threshold, float(self.joint_state.ood_state.get("score", 0.0))),
                    "status": "ABSTAIN",
                    "decision_confidence_cap": 0.20,
                    "recommendation": "Calibration is disabled and model trust is insufficient; abstain instead of forcing a structural conclusion.",
                }
                return replace(
                    baseline,
                    explanation="Model trust fell below the supported planning domain while calibration was disabled; ARGUS abstained.",
                    strategy="model_trust_abstention",
                    action_type="verification",
                    objective=self.config.planner_objective,
                    structured_explanation={
                        "action_type": "verification", "primary_reason": "Model-trust abstention",
                        "model_trust": self.joint_state.discrepancy_state.get("model_trust"),
                        "ood": self.joint_state.ood_state,
                    },
                )
        if decision.action_type == "calibration":
            start_index = len(self.experiments)
            calibration_options = [
                self.dual_control.calibration_experiment(decision.calibration_type, start_index + offset)
                for offset in range(3)
            ]
            experiment = next(
                (
                    candidate
                    for candidate in calibration_options
                    if self.neo_planner.constraints.evaluate(
                        candidate,
                        no_go_regions=no_go_regions,
                        unavailable_actions=unavailable_actions,
                    ).feasible
                ),
                None,
            )
            if experiment is None:
                decision = replace(
                    decision,
                    action_type="verification",
                    primary_reason=(
                        "Calibration is required but every supported calibration geometry is restricted; "
                        "ARGUS will seek a constrained verification action without lifting the confidence cap."
                    ),
                    calibration_type=None,
                )
        if decision.action_type == "calibration":
            assert experiment is not None
            cost = self.planner._experiment_cost(experiment, self.experiments)
            candidate = CandidateScore(
                experiment=experiment,
                expected_information_gain=0.0,
                hypothesis_disagreement=0.0,
                uncertainty_coverage=0.0,
                experiment_cost=cost,
                repetition_penalty=self.planner._repetition_penalty(experiment, self.experiments),
                final_score=decision.calibration_value - self.config.planner_cost_weight * cost,
                calibration_value=decision.calibration_value,
                model_trust=float(self.joint_state.discrepancy_state.get("model_trust", 1.0)),
                energy_cost=experiment.amplitude**2 * experiment.duration_s,
                predicted_uncertainty_after=max(0.0, decision.metrology_uncertainty * 0.72),
            )
            explanation = {
                **decision.to_dict(),
                "expected_information_gain": 0.0,
                "expected_risk_reduction": 0.0,
                "hypothesis_separation": 0.0,
                "movement_cost": cost,
                "energy_cost": candidate.energy_cost,
                "model_trust": candidate.model_trust,
                "uncertainty_before": decision.metrology_uncertainty,
                "predicted_uncertainty_after": candidate.predicted_uncertainty_after,
            }
            return PlannedExperiment(
                candidate,
                (candidate, *baseline.top_candidates[:4]),
                decision.primary_reason,
                strategy="adaptive_dual_control",
                action_type="calibration",
                objective=self.config.planner_objective,
                structured_explanation=explanation,
            )
        neo = self.neo_planner.recommend(
            self.joint_state,
            self.experiments,
            action_type=decision.action_type,
            objective=self.config.planner_objective,
            mode="research" if self.config.profile == "research" else "fast",
            no_go_regions=no_go_regions,
            unavailable_actions=unavailable_actions,
        )
        structured = {**(neo.structured_explanation or {}), "dual_control": decision.to_dict()}
        return replace(
            neo,
            explanation=decision.primary_reason + " " + neo.explanation,
            structured_explanation=structured,
        )

    def status(self) -> dict:
        estimate = self.belief.estimate()
        uncertainty = self.joint_state.uncertainty_summary()
        posterior_containment = self.belief.radial_containment(self.panel)
        expected_value = float(self.current_recommendation.selected.expected_information_gain) if hasattr(self, "current_recommendation") else 1.0
        credible_area = float(self.belief.credible_region(0.90)["area_fraction"])
        decision_confidence = float(min(
            estimate["confidence"] * self.joint_state.discrepancy_state.get("model_trust", 1.0),
            self.joint_state.ood_state.get("decision_confidence_cap", 1.0),
        ))
        bayes_risk = self.loss_model.current_risk(decision_confidence, float(self.joint_state.ood_state.get("score", 0.0)), credible_area)
        verification_count = sum(action_type == "verification" for action_type in self.action_history)
        stop = self.stopping_engine.evaluate(
            confidence=decision_confidence,
            confidence_threshold=self.config.confidence_threshold,
            entropy=estimate["normalized_entropy"],
            entropy_threshold=self.config.entropy_threshold,
            credible_area=credible_area,
            credible_area_threshold=self.config.credible_region_stop_fraction,
            expected_value=expected_value,
            expected_value_threshold=self.config.expected_value_stop_threshold,
            bayes_risk=bayes_risk,
            bayes_risk_threshold=self.config.bayes_risk_stop_threshold,
            experiment_count=len(self.experiments),
            maximum_experiments=self.config.max_experiments,
            ood_status=str(self.joint_state.ood_state.get("status", "NOMINAL")),
            verification_count=verification_count,
        )
        integrity = self.assurance.structural_assessment(
            self.belief,
            ood_state=self.joint_state.ood_state,
            model_trust=float(self.joint_state.discrepancy_state.get("model_trust", 1.0)),
            should_stop=stop.should_stop,
        )
        return {
            **estimate,
            "experiment_count": len(self.experiments),
            "should_stop": stop.should_stop,
            "stop_reason": stop.reason,
            "stop_explanation": stop.explanation,
            "stop_criteria": stop.triggered,
            "bayes_risk": bayes_risk,
            "expected_value_of_information": expected_value,
            "structural_uncertainty": uncertainty["structural"]["combined"],
            "metrology_uncertainty": uncertainty["metrology"]["combined"],
            "model_trust": self.joint_state.discrepancy_state.get("model_trust", 1.0),
            "ood_score": self.joint_state.ood_state.get("score", 0.0),
            "ood_status": self.joint_state.ood_state.get("status", "NOMINAL"),
            "decision_confidence": decision_confidence,
            "posterior_containment": posterior_containment,
            "credible_region_90": self.belief.credible_region(0.90),
            "top_hypotheses": self.belief.top_hypotheses(5),
            "integrity_assessment": integrity,
            "sensor_health": self.assurance.to_dict(),
            "recommended_engineering_action": integrity["engineering_action"],
        }

    def automatic_recovery_available(self) -> bool:
        """Whether a stop state has one bounded, model-selected recovery action."""

        return (
            len(self.experiments) < self.config.max_experiments
            and self.current_recommendation.action_type == "calibration"
        )

    def localization_error(self) -> float:
        estimate = self.belief.estimate()
        return float(physical_distance(estimate["map_x"], estimate["map_y"], self.truth.center_x, self.truth.center_y, self.panel))
