from __future__ import annotations

from dataclasses import dataclass, field, replace
import json
from pathlib import Path

import numpy as np
from scipy.signal import correlate, correlation_lags

from backend.app.active_learning.planner import CandidateScore, ExperimentPlanner, PlannedExperiment
from backend.app.active_learning.neo_planner import NeoExperimentPlanner
from backend.app.active_learning.bayes_design import FiniteHorizonRiskPlanner
from backend.app.active_learning.reference_design import select_task_reference
from backend.app.assurance.monitor import RuntimeAssuranceMonitor
from backend.app.control.dual_control import AdaptiveDualControlManager
from backend.app.core.config import ArgusConfig
from backend.app.decision.loss import DecisionLossModel
from backend.app.decision.stopping import StoppingEngine
from backend.app.digital_twin.discrepancy import OnlineDiscrepancyModel
from backend.app.hardware.devices import SimulationDevice
from backend.app.hardware.timing_contract import AcquisitionTimingAssessment
from backend.app.inference.calibration import CalibrationEngine
from backend.app.inference.belief import measurement_likelihood, posterior_update
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
        self.risk_planner = FiniteHorizonRiskPlanner(self.neo_planner)
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

    def run_recommended(self, *, plan_next: bool = True) -> ExperimentResult:
        return self.run_experiment(self.current_recommendation.selected.experiment, self.current_recommendation, plan_next=plan_next)

    def run_experiment(self, experiment: Experiment, recommendation: PlannedExperiment | None = None, *, plan_next: bool = True) -> ExperimentResult:
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
        return self.process_signal(signal, experiment, recommendation, plan_next=plan_next)

    def process_signal(
        self,
        signal: np.ndarray,
        experiment: Experiment,
        recommendation: PlannedExperiment | None = None,
        quality_context: dict | None = None,
        *, plan_next: bool = True, physical_acquisition: bool = False,
        physical_timing: AcquisitionTimingAssessment | None = None,
    ) -> ExperimentResult:
        recommendation = self._resolve_recommendation(experiment, recommendation)
        before = self.belief.posterior.copy()
        containment_before = self.belief.radial_containment(self.panel)
        # Validate the entire declared observation before changing any state.
        # Flattening channels or truncating an incomplete recording changes the
        # physical observation while retaining its original action metadata.
        signal = np.asarray(signal, dtype=np.float64)
        expected_samples = max(32, int(round(experiment.duration_s * self.config.sample_rate)))
        if signal.ndim != 1 or signal.size != expected_samples:
            raise ValueError("Signal must be mono and match the declared experiment window")
        analysis = analyze_signal(signal, self.config.sample_rate)
        self.joint_state.verification_state = {"accepted": False, "reason": "latest_action_not_verified"}
        experiment_key = json.dumps(experiment.to_dict(), sort_keys=True, separators=(",", ":"))
        prior_signal = self.prior_signals.get(experiment_key)
        quality_context = quality_context or {}
        reference_assessment = None
        # Provenance comes from the acquisition adapter, not a client-supplied
        # sensor name which could suppress the measured-data reference gate.
        if self.acoustic_reference is not None and physical_acquisition:
            reference_assessment = self.acoustic_reference.assess(analysis["features"])
        quality = estimate_measurement_quality(
            signal, prior_signal,
            acceleration_rms=quality_context.get("acceleration_deviation_g"),
            visual_position_error=quality_context.get("visual_position_error"),
        )
        # Travel-time likelihoods require a known excitation time origin and
        # a validated arrival adapter. Only the ingestion service can supply
        # this assessment; an arbitrary sensor name/metadata flag cannot
        # turn an unaligned physical recording into structural evidence.
        timing_supported = not physical_acquisition or bool(
            physical_timing is not None and physical_timing.supported
        )
        if not timing_supported:
            timing_reason = physical_timing.reason if physical_timing is not None else "unknown_excitation_time_origin"
            quality = replace(quality, accepted=False, reasons=(*quality.reasons, timing_reason))
        evidence_weight = max(self.config.minimum_evidence_weight, quality.evidence_weight) if quality.accepted else 0.0
        # Channel reliability is part of the evidence gate. A merely adequate
        # reading must not update structure/calibration while its sensor still
        # has an accumulated unreliable-channel state.
        assurance_state = self.assurance.update(quality, {}, quality_context, action_type=recommendation.action_type)
        current_sensor = assurance_state.get("sensors", {}).get(assurance_state.get("last_update", {}).get("sensor_id", ""), {})
        sensor_status = current_sensor.get("status", "NOMINAL")
        if sensor_status == "UNRELIABLE":
            evidence_weight = 0.0
        elif sensor_status == "DEGRADED":
            evidence_weight *= 0.35
        calibration_result = None
        if recommendation.action_type == "calibration":
            likelihood = np.ones_like(self.belief.posterior)
            diagnostics = self._direct_path_diagnostics(signal, experiment)
            diagnostics.update({key: quality_context[key] for key in (
                "source_pose_error_observed", "receiver_pose_error_observed", "pose_observation_std"
            ) if key in quality_context})
            calibration_quality = quality
            if sensor_status == "UNRELIABLE":
                calibration_quality = replace(quality, accepted=False, reasons=(*quality.reasons, "unreliable_channel"))
            elif sensor_status == "DEGRADED":
                calibration_quality = replace(quality, signal_quality=quality.signal_quality * 0.35)
            calibration_result = self.calibration_engine.update(
                self.joint_state.nuisance,
                experiment,
                self.panel,
                diagnostics,
                calibration_quality,
                str((recommendation.structured_explanation or {}).get("calibration_type", "direct_path")),
            ).to_dict()
            self.joint_state.last_calibration = calibration_result
            if calibration_result["accepted"]:
                self.synchronize_inference_material()
                # Direct-path residuals are not exchangeable with defect-scatter
                # residuals and must not populate the latter's conformal set.
                prior_trust = float(self.joint_state.discrepancy_state.get("model_trust", 0.5))
                self.joint_state.discrepancy_state = {
                    **self.joint_state.discrepancy_state,
                    # A valid reference permits a cautious diagnostic probe;
                    # it does not validate the entire scattered-wave model.
                    "model_trust": max(prior_trust, 0.20),
                    "calibration_supported": True,
                    "calibration_support_scope": "propagation_reference_only",
                    "trust_is_heuristic": True,
                }
                prior_ood = float(self.joint_state.ood_state.get("score", 0.0))
                self.joint_state.ood_state = {
                    **self.joint_state.ood_state,
                    "score": min(prior_ood, self.config.ood_caution_threshold),
                    "status": "NOMINAL" if prior_ood < self.config.ood_caution_threshold else "CAUTION",
                    "recommendation": "Reference evidence incorporated; a fresh diagnostic measurement must reassess structural model support.",
                }
            else:
                self.joint_state.ood_state = {
                    **self.joint_state.ood_state,
                    "status": self.joint_state.ood_state.get("status") if self.joint_state.ood_state.get("status") in {"ABSTAIN", "OUT_OF_DISTRIBUTION"} else "CAUTION",
                    "decision_confidence_cap": min(
                        0.35, float(self.joint_state.ood_state.get("decision_confidence_cap", 1.0))
                    ),
                    "recommendation": "Calibration acquisition failed quality checks; reacquire the reference signal.",
                }
        elif not quality.accepted or sensor_status == "UNRELIABLE":
            likelihood = np.ones_like(self.belief.posterior)
            diagnostics = {"rejected": 1.0, "evidence_weight": 0.0}
            if sensor_status == "UNRELIABLE":
                diagnostics["update_blocked_sensor"] = True
        else:
            likelihood, diagnostics = measurement_likelihood(
                signal,
                experiment,
                self.simulator,
                self.belief.grid_size,
                temperature=self.config.likelihood_temperature,
            )
            # Assess against the pre-observation belief. An outlier must not
            # first move the posterior toward itself and then pass its own test.
            if self.config.enable_discrepancy_model or self.config.enable_ood_layer:
                self._update_model_diagnostics(
                    experiment,
                    diagnostics,
                    quality.evidence_weight,
                    reference_assessment.score if reference_assessment is not None else 0.0,
                )
            ood_status = str(self.joint_state.ood_state.get("status", "NOMINAL"))
            if self.config.enable_ood_layer and ood_status in {"ABSTAIN", "OUT_OF_DISTRIBUTION"}:
                evidence_weight = 0.0
                diagnostics["update_blocked_ood"] = True
            elif self.config.enable_ood_layer and ood_status == "CAUTION":
                evidence_weight *= 0.35
            self.belief.posterior = posterior_update(before, np.maximum(likelihood, 1e-12) ** evidence_weight)
            self.belief.history.append(self.belief.posterior.copy())
            if self.config.enable_nuisance_inference and evidence_weight > 0:
                self.joint_state.nuisance.passive_quality_update(
                    analysis["features"]["noise_estimate"], quality.coupling_quality, quality.signal_quality
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
            "sensor_status_before_fusion": sensor_status,
            "update_blocked_sensor": sensor_status == "UNRELIABLE",
            "update_blocked_physical_timing": not timing_supported,
            "physical_timing": physical_timing.to_dict() if physical_timing is not None else {
                "supported": not physical_acquisition,
                "reason": "simulation_time_origin" if not physical_acquisition else "unknown_excitation_time_origin",
            },
        })
        self.assurance.incorporate_structural_evidence(quality, diagnostics, action_type=recommendation.action_type)
        if not timing_supported:
            self.joint_state.ood_state = {
                **self.joint_state.ood_state,
                "status": "ABSTAIN", "decision_confidence_cap": 0.0,
                "recommendation": "Record a trigger-aligned signal with an externally validated arrival/drive adapter before structural interpretation.",
                "physical_time_origin_supported": False,
            }
        elif sensor_status == "UNRELIABLE":
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
        if recommendation.action_type == "verification":
            estimate_after = self.belief.estimate()
            displacement_mm = 1000 * float(np.hypot(
                (estimate_after["map_x"] - containment_before["reference_x"]) * self.panel.width_m,
                (estimate_after["map_y"] - containment_before["reference_y"]) * self.panel.height_m,
            ))
            diverse = bool(self.experiments and self._verification_is_diverse(experiment, self.experiments[-1]))
            verified = bool(quality.accepted and evidence_weight > 0 and diverse
                            and self.joint_state.ood_state.get("status") == "NOMINAL"
                            and displacement_mm <= containment_before["radius90_mm"] + 1e-9)
            self.joint_state.verification_state = {
                "accepted": verified, "experiment_index": len(self.experiments) + 1,
                "diverse_from_previous": diverse, "map_displacement_mm": displacement_mm,
                "prior_radius90_mm": containment_before["radius90_mm"],
                "reason": "accepted_diverse_consistent_measurement" if verified else "quality_ood_diversity_or_consistency_failed",
                "field_calibrated": False,
            }
        diagnostics["verification"] = self.joint_state.verification_state.copy()
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
        # A rejected reading must not become the consistency reference for a
        # future measurement and poison its coupling-quality assessment.
        accepted_reference = bool(evidence_weight > 0 if recommendation.action_type != "calibration"
                                  else calibration_result and calibration_result.get("accepted"))
        if quality.accepted and sensor_status != "UNRELIABLE" and accepted_reference:
            self.prior_signals[experiment_key] = np.asarray(signal, dtype=np.float32).copy()
        # There is no executable "next" action once the inspection budget is
        # exhausted.  Keeping the last recommendation makes status/evidence
        # rendering deterministic and avoids an unnecessary planner call that
        # can legitimately find no supported action at very low model trust.
        if plan_next and len(self.experiments) < self.config.max_experiments:
            self.current_recommendation = self._recommend()
        return result

    @staticmethod
    def _verification_is_diverse(experiment: Experiment, previous: Experiment) -> bool:
        """Require changed path geometry or excitation content.

        Amplitude/duration metadata and reciprocal TX/RX order alone do not
        provide a new structural path constraint in this reciprocal model.
        This is a diversity check, not a guarantee of conditional independence.
        """
        geometry = np.asarray([experiment.source_x, experiment.source_y, experiment.receiver_x, experiment.receiver_y])
        old_geometry = np.asarray([previous.source_x, previous.source_y, previous.receiver_x, previous.receiver_y])
        same_path = np.allclose(geometry, old_geometry, rtol=0, atol=1e-8) or np.allclose(
            geometry, old_geometry[[2, 3, 0, 1]], rtol=0, atol=1e-8
        )
        same_excitation = (
            np.isclose(experiment.frequency_start_hz, previous.frequency_start_hz, rtol=1e-8, atol=1e-8)
            and np.isclose(experiment.frequency_end_hz, previous.frequency_end_hz, rtol=1e-8, atol=1e-8)
            and experiment.waveform == previous.waveform
            and experiment.phase_code == previous.phase_code
            and experiment.spectral_notches_hz == previous.spectral_notches_hz
        )
        return not (same_path and same_excitation)

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
        quiet = signal[max(0, int(len(signal) * 0.8)):]
        noise_floor = float(np.median(np.abs(quiet - np.median(quiet))) * 1.4826 + 1e-12)
        baseline = self.simulator.simulate_baseline(experiment)
        return {
            "peak_delay_s": float(selected_lags[peak_index] / self.config.sample_rate),
            "noise_floor": noise_floor,
            "direct_correlation_peak": float(selected_corr[peak_index]),
            "signal_rms": float(np.sqrt(np.mean(np.square(signal)))),
            "baseline_rms": float(np.sqrt(np.mean(np.square(baseline)))),
            "delay_std_s": float(np.sqrt(max(1.0 / self.config.sample_rate, 0.00020)**2
                + (max(self.panel.width_m, self.panel.height_m) * np.hypot(
                    self.joint_state.nuisance.parameter("source_pose_error").std,
                    self.joint_state.nuisance.parameter("receiver_pose_error").std) / self.material.wave_velocity)**2)),
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
        if self.config.enable_risk_calibration_design:
            return self.risk_planner.recommend(self.joint_state, self.experiments,
                no_go_regions=no_go_regions, unavailable_actions=unavailable_actions)
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
            reference_design = None
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
            if (experiment is not None and self.config.enable_task_conditioned_calibration
                    and decision.calibration_type == "direct_path"):
                feasible = [e for e in calibration_options if self.neo_planner.constraints.evaluate(
                    e, no_go_regions=no_go_regions, unavailable_actions=unavailable_actions).feasible]
                target = next((item.experiment for item in baseline.top_candidates
                    if self.neo_planner.constraints.evaluate(item.experiment,
                        no_go_regions=no_go_regions, unavailable_actions=unavailable_actions).feasible), None)
                if target is not None:
                    selection = select_task_reference(self.belief.posterior, self.joint_state.nuisance,
                        self.panel, target, feasible, sample_rate=self.config.sample_rate,
                        cost_function=lambda e: self.planner._experiment_cost(e, self.experiments),
                        cost_m2_per_unit=self.config.decision_cost_m2_per_unit)
                    experiment, reference_design = selection.experiment, selection.diagnostics
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
            if reference_design is not None:
                explanation["reference_design"] = reference_design
                explanation["primary_reason"] = (
                    decision.primary_reason + " Reference geometry minimizes full-grid modeled propagation "
                    "variance for the next diagnostic geometry plus declared cost.")
            return PlannedExperiment(
                candidate,
                (candidate, *baseline.top_candidates[:4]),
                explanation.get("primary_reason", decision.primary_reason),
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
        if self.config.enable_risk_calibration_design:
            # Bits/proxies and m² have different units. The legacy VOI stopping
            # threshold is disabled for the physical-loss experimental policy.
            expected_value = 1.0
        credible_area = float(self.belief.credible_region(0.90)["area_fraction"])
        decision_confidence = float(min(
            estimate["confidence"] * self.joint_state.discrepancy_state.get("model_trust", 1.0),
            self.joint_state.ood_state.get("decision_confidence_cap", 1.0),
        ))
        bayes_risk = self.loss_model.current_risk(decision_confidence, float(self.joint_state.ood_state.get("score", 0.0)), credible_area)
        verification_count = int(self.joint_state.verification_state.get("accepted", False)
                                 and self.joint_state.verification_state.get("experiment_index") == len(self.experiments))
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
            "bayes_risk_method": "legacy_heuristic_risk_index_not_failure_probability",
            "decision_confidence_method": "posterior_concentration_times_heuristic_trust_not_calibrated_probability",
            "verification_state": self.joint_state.verification_state,
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
            and not self.joint_state.ood_state.get("planning_blocked", False)
        )

    def localization_error(self) -> float:
        estimate = self.belief.estimate()
        return float(physical_distance(estimate["map_x"], estimate["map_y"], self.truth.center_x, self.truth.center_y, self.panel))
