from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

from backend.app.control.dual_control import AdaptiveDualControlManager
from backend.app.active_learning.horizon import RecedingHorizonPlanner
from backend.app.active_learning.planner import CandidateScore
from backend.app.core.config import ArgusConfig
from backend.app.digital_twin.discrepancy import OnlineDiscrepancyModel
from backend.app.inference.calibration import CalibrationEngine
from backend.app.inference.diagnostics import estimate_measurement_quality
from backend.app.inference.joint_state import JointInferenceState
from backend.app.inference.structural_posterior import StructuralPosterior
from backend.app.models.domain import Experiment, Material, Panel
from backend.app.ood.detection import OODDetector
from backend.app.safety.constraints import ExperimentConstraintEngine, NoGoRegion
from backend.app.services.engine import ArgusEngine


@pytest.mark.parametrize("overrides", [
    {"profile": ["demo"]},
    {"planner_objective": ["MULTIOBJECTIVE"]},
    {"enable_ood_layer": 1},
    {"grid_size": True},
    {"planner_information_weight": -0.1},
])
def test_configuration_rejects_malformed_or_unsafe_values(overrides):
    with pytest.raises(ValueError):
        ArgusConfig(**overrides)


def test_calibration_reduces_nuisance_uncertainty_and_updates_forward_model():
    engine = ArgusEngine(ArgusConfig(seed=4, candidate_count=12), seed=4)
    posterior = engine.joint_state.nuisance
    experiment = Experiment(0.05, 0.5, 0.95, 0.5)
    before = posterior.uncertainty_summary()["combined"]
    quality = estimate_measurement_quality(np.sin(np.linspace(0, 40, 1_920)) * 0.08)
    result = CalibrationEngine().update(
        posterior, experiment, Panel(), {"peak_delay_s": 0.0034, "noise_floor": 0.006}, quality, "direct_path"
    )
    engine.synchronize_inference_material()
    assert result.uncertainty_after < before
    assert posterior.calibration_count == 1
    assert engine.simulator.material.wave_velocity == posterior.parameter("wave_velocity").mean


def test_dual_control_switches_to_calibration_when_metrology_is_inflated():
    state = JointInferenceState.nominal(StructuralPosterior(12), Material())
    for parameter in state.nuisance.parameters.values():
        parameter.inflate(8)
    decision = AdaptiveDualControlManager(ArgusConfig()).choose(state, diagnostic_value=0.02, experiment_count=1)
    assert decision.action_type == "calibration"
    assert decision.calibration_value > decision.diagnostic_value
    assert decision.calibration_type is not None


def test_rejected_silence_cannot_collapse_posterior():
    engine = ArgusEngine(ArgusConfig(seed=8, candidate_count=12), seed=8)
    initial = engine.belief.posterior.copy()
    experiment = engine.current_recommendation.selected.experiment
    for _ in range(3):
        result = engine.process_signal(np.zeros(1_920, dtype=np.float32), experiment)
        assert not result.quality["accepted"]
    assert np.allclose(engine.belief.posterior, initial)
    assert engine.belief.estimate()["confidence"] < 0.1


def test_tempered_low_quality_evidence_reduces_overconfidence():
    source = ArgusEngine(ArgusConfig(seed=12, candidate_count=12), seed=12)
    experiment = source.current_recommendation.selected.experiment
    signal = source.simulator.simulate(source.truth, experiment)
    high = StructuralPosterior(20); low = StructuralPosterior(20)
    high.update(signal, experiment, source.simulator, evidence_weight=1.0)
    low.update(signal, experiment, source.simulator, evidence_weight=0.1)
    assert low.estimate()["normalized_entropy"] > high.estimate()["normalized_entropy"]


def test_uniform_prior_hypotheses_are_spatially_distributed():
    modes = StructuralPosterior(20).top_hypotheses(5, minimum_separation_cells=2)
    coordinates = np.asarray([(item["x"], item["y"]) for item in modes])

    assert np.ptp(coordinates[:, 0]) > 0.5
    assert np.ptp(coordinates[:, 1]) > 0.5


def test_constraints_and_waveform_bounds_are_enforced():
    config = ArgusConfig(maximum_amplitude=0.6, maximum_frequency_hz=6_000)
    constraints = ExperimentConstraintEngine(config)
    experiment = Experiment(0.2, 0.2, 0.8, 0.8, 1_000, 6_500, 0.7, 0.12, "spectrally_notched")
    result = constraints.evaluate(experiment, no_go_regions=[NoGoRegion(0.1, 0.1, 0.3, 0.3, "fixture")])
    assert not result.feasible
    assert "amplitude_limit" in result.reasons
    assert "frequency_outside_model_or_sensor_support" in result.reasons
    assert "source_in_no_go:fixture" in result.reasons


def test_discrepancy_and_ood_are_conservative():
    model = OnlineDiscrepancyModel()
    features = model.features(3_000, 0.4, (0.1, 0.2, 0.8, 0.7))
    first = model.update(features, np.asarray([0.0001, 0.1, 0.05, -0.04]))
    large = model.update(features, np.asarray([0.003, 4.0, 3.0, -3.0]))
    assert large["model_trust"] < first["model_trust"]
    assessment = OODDetector().assess(np.asarray([0.01, 8.0, 6.0, -6.0]), ensemble_disagreement=1.0, measurement_quality=0.1)
    assert assessment.status == "ABSTAIN"
    assert assessment.decision_confidence_cap <= 0.2


def test_ood_cap_is_applied_to_decision_confidence():
    engine = ArgusEngine(ArgusConfig(seed=33, candidate_count=12), seed=33)
    engine.joint_state.ood_state = {"score": 0.9, "status": "ABSTAIN", "decision_confidence_cap": 0.2}
    engine.joint_state.discrepancy_state["model_trust"] = 1.0
    assert engine.status()["decision_confidence"] <= 0.2
    assert engine.status()["stop_reason"] == "STOP_OOD"


def test_ood_reference_does_not_learn_from_rejected_outliers():
    detector = OODDetector()
    outlier = np.asarray([0.02, 10.0, 8.0, -8.0])

    assessments = [
        detector.assess(outlier, ensemble_disagreement=1.0, measurement_quality=0.1)
        for _ in range(12)
    ]

    assert all(item.status == "ABSTAIN" for item in assessments)
    assert detector.residual_vectors == []


def test_all_waveform_families_generate_finite_bounded_signals():
    engine = ArgusEngine(ArgusConfig(seed=51, candidate_count=12), seed=51)
    families = ("impulse", "sine", "chirp", "tone_burst", "ricker", "multisine", "phase_coded", "complementary_coded", "spectrally_notched")
    for family in families:
        experiment = Experiment(
            0.1, 0.2, 0.8, 0.7, 1_200, 5_400, 0.5, 0.12, family,
            phase_code="1101001" if family == "phase_coded" else None,
            code_length=7 if family == "phase_coded" else 0,
            spectral_notches_hz=((2_500, 3_000),) if family == "spectrally_notched" else (),
        )
        signal = engine.simulator.excitation(experiment)
        assert len(signal) == 1_920
        assert np.all(np.isfinite(signal))
        assert np.max(np.abs(signal)) <= experiment.amplitude + 1e-5


def test_custom_probe_does_not_inherit_pending_calibration_action():
    engine = ArgusEngine(config=ArgusConfig(seed=109), seed=109)
    engine.joint_state.ood_state.update({"status": "ABSTAIN", "score": 0.95})
    engine.current_recommendation = engine._recommend()
    assert engine.current_recommendation.action_type == "calibration"
    custom = Experiment(0.06, 0.06, 0.94, 0.94, 3_400, 6_200, 0.42, 0.12, "chirp")

    result = engine.run_experiment(custom)

    assert result.action_type == "diagnostic"
    assert result.recommendation.strategy == "human_specified"
    assert result.recommendation.structured_explanation["operator_override"] is True
    assert not np.array_equal(result.posterior_before, result.posterior_after)


def test_calibration_recommendation_avoids_restricted_geometry():
    engine = ArgusEngine(config=ArgusConfig(seed=113), seed=113)
    engine.joint_state.ood_state.update({"status": "ABSTAIN", "score": 0.95})
    first = engine.dual_control.calibration_experiment("direct_path", 0)
    restricted = NoGoRegion(0.0, first.source_y - 0.02, 1.0, first.source_y + 0.02, "fixture")

    recommendation = engine._recommend([restricted])

    assert recommendation.action_type == "calibration"
    assert recommendation.selected.experiment.source_y != first.source_y
    assert ExperimentConstraintEngine(engine.config).evaluate(
        recommendation.selected.experiment, no_go_regions=[restricted]
    ).feasible


def test_calibration_never_rewrites_hidden_acquisition_physics():
    engine = ArgusEngine(config=ArgusConfig(seed=127), seed=127)
    acquisition_before = engine.acquisition_simulator.material
    engine.joint_state.ood_state.update({"status": "ABSTAIN", "score": 0.95})
    engine.current_recommendation = engine._recommend()

    result = engine.run_recommended()

    assert result.action_type == "calibration"
    assert result.calibration_result["accepted"]
    assert engine.acquisition_simulator is not engine.simulator
    assert engine.acquisition_simulator.material == acquisition_before


def test_failed_calibration_cannot_increase_model_trust():
    engine = ArgusEngine(config=ArgusConfig(seed=131), seed=131)
    engine.joint_state.ood_state.update({"status": "ABSTAIN", "score": 0.95})
    engine.current_recommendation = engine._recommend()
    recommendation = engine.current_recommendation
    trust_before = engine.joint_state.discrepancy_state["model_trust"]

    result = engine.process_signal(
        np.zeros(int(engine.config.sample_rate * engine.config.signal_duration), dtype=np.float32),
        recommendation.selected.experiment,
        recommendation,
    )

    assert result.calibration_result["accepted"] is False
    assert engine.joint_state.discrepancy_state["model_trust"] == trust_before
    assert engine.joint_state.ood_state["status"] == "CAUTION"


def test_horizon_diagnostics_report_the_selected_future_route_cost():
    first = CandidateScore(Experiment(0.1, 0.1, 0.9, 0.9), 0, 0, 0, 0, 0, 1.0)
    second = CandidateScore(Experiment(0.8, 0.8, 0.1, 0.1), 0, 0, 0, 0, 0, 0.9)

    _, scores = RecedingHorizonPlanner().rerank([first, second], horizon=2, beam_width=2)

    assert scores[id(first)].route_cost > 0


def test_early_structural_ambiguity_is_not_learned_as_model_discrepancy():
    engine = ArgusEngine(ArgusConfig(seed=910, max_experiments=8), seed=910)

    engine.run_recommended()

    assert engine.joint_state.discrepancy_state["structural_identifiability_weight"] < 0.20
    assert engine.joint_state.discrepancy_state["model_trust"] > 0.90
    assert engine.current_recommendation.action_type != "calibration"


def test_budget_exhaustion_does_not_attempt_to_plan_an_extra_action():
    engine = ArgusEngine(ArgusConfig(seed=137, max_experiments=1), seed=137)
    recommendation = engine.current_recommendation
    engine._recommend = lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("unexpected planning call"))  # type: ignore[method-assign]

    result = engine.run_experiment(recommendation.selected.experiment, recommendation)

    assert result.index == 1
    assert engine.status()["stop_reason"] == "STOP_BUDGET"
