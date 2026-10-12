from dataclasses import replace

import numpy as np
import pytest
from fastapi.testclient import TestClient

from backend.app.active_learning.bayes_design import expected_position_risk
from backend.app.core.config import ArgusConfig, config_for_profile
from backend.app.evidence.ledger import EvidenceLedger, canonical_hash
from backend.app.inference.calibration import CalibrationEngine
from backend.app.inference.diagnostics import estimate_measurement_quality
from backend.app.inference.nuisance_posterior import NuisancePosterior
from backend.app.main import create_app
from backend.app.models.domain import Experiment, Material, Panel
from backend.app.services.engine import ArgusEngine


def test_single_delay_cannot_identify_velocity_and_timing_independently():
    posterior = NuisancePosterior.from_material(Material())
    before = posterior.propagation_covariance()
    posterior.update_direct_path(0.4, 0.0008 + 0.4 / 180, 0.00002, 1)
    after = posterior.propagation_covariance()
    # One scalar observation supplies a rank-one precision increment.
    scaling = np.diag(np.sqrt(np.diag(before)))
    precision_gain = scaling @ (np.linalg.inv(after)-np.linalg.inv(before)) @ scaling
    assert np.linalg.eigvalsh(precision_gain)[0] == pytest.approx(0, abs=1e-8)
    assert posterior.velocity_timing_correlation > 0.8
    assert np.linalg.det(after) > 0
    restored = NuisancePosterior.from_dict(posterior.to_dict())
    assert np.allclose(restored.propagation_covariance(), after)


def test_different_path_lengths_resolve_more_uncertainty_than_repeating_one():
    repeated = NuisancePosterior.from_material(Material())
    varied = NuisancePosterior.from_material(Material())
    for i in range(12):
        for posterior, distance in ((repeated, 0.3), (varied, (0.15, 0.55)[i % 2])):
            posterior.update_direct_path(distance, 0.0009 + distance / 195, 0.00002, 1)
    assert np.linalg.det(varied.propagation_covariance()) < np.linalg.det(repeated.propagation_covariance()) * 0.1
    assert varied.parameter("wave_velocity").mean == pytest.approx(195, abs=2)
    assert varied.parameter("timing_offset").mean == pytest.approx(0.0009, abs=0.00003)


def test_pose_calibration_requires_external_pose_measurement():
    posterior = NuisancePosterior.from_material(Material())
    before = posterior.to_dict()
    quality = estimate_measurement_quality(np.sin(np.linspace(0, 20, 1920)) * 0.1)
    result = CalibrationEngine().update(posterior, Experiment(0.1, 0.1, 0.9, 0.9), Panel(), {}, quality, "phone_pose_recalibration")
    assert not result.accepted
    assert posterior.to_dict() == before


def test_nonfinite_samples_and_placement_failure_are_rejected():
    values = np.sin(np.linspace(0, 20, 1920)) * 0.1
    values[1] = np.nan
    assert not estimate_measurement_quality(values).accepted
    assert not estimate_measurement_quality(np.nan_to_num(values), visual_position_error=1).accepted


def test_risk_integral_has_physical_units_and_correct_limits():
    p = np.array([0.5, 0.5])
    centers = np.array([[0., 0.], [0.2, 0.]])
    within = np.array([0.001, 0.001])
    uninformative = expected_position_risk(p, np.zeros(2), np.ones(2), centers, within)
    separated = expected_position_risk(p, np.array([-10., 10.]), np.ones(2), centers, within)
    assert uninformative == pytest.approx(0.011)
    assert separated == pytest.approx(0.001)
    scaled = expected_position_risk(p, np.zeros(2), np.ones(2), centers * 1000, within * 1e6)
    assert scaled == pytest.approx(uninformative * 1e6)
    translated = expected_position_risk(p, np.zeros(2), np.ones(2), centers+100, within)
    assert translated == pytest.approx(uninformative)


def test_correlated_two_step_design_respects_budget_and_reports_loss():
    engine = ArgusEngine(ArgusConfig(seed=763, candidate_count=8, top_hypotheses=3,
                                   planner_beam_width=2, max_experiments=2, enable_risk_calibration_design=True), seed=763)
    recommendation = engine.current_recommendation
    assert recommendation.strategy == "finite_horizon_bayes_risk"
    assert recommendation.planning_horizon == 2
    report = recommendation.structured_explanation
    assert report["loss_units"] == "m^2"
    assert report["posterior_mass"] == pytest.approx(1)
    assert report["field_calibrated"] is False
    assert report["expected_terminal_risk_m2"] <= report["prior_risk_m2"] + 1e-5
    engine.run_recommended()
    assert engine.current_recommendation.planning_horizon == 1
    engine.run_recommended()
    assert engine.status()["stop_reason"] == "STOP_BUDGET"


def test_rejected_verification_cannot_count_as_support():
    engine = ArgusEngine(ArgusConfig(seed=764, candidate_count=8, max_experiments=1), seed=764)
    recommendation = replace(engine.current_recommendation, action_type="verification")
    engine.process_signal(np.zeros(1920), recommendation.selected.experiment, recommendation)
    assert engine.joint_state.verification_state["accepted"] is False
    assert engine.status()["stop_criteria"]["verification"] is False


def test_ood_gate_precedes_posterior_update():
    engine = ArgusEngine(ArgusConfig(seed=765, candidate_count=8, max_experiments=1), seed=765)
    before = engine.belief.posterior.copy()
    def force_ood(*args):
        engine.joint_state.ood_state = {"status": "ABSTAIN", "score": 0.99}
    engine._update_model_diagnostics = force_ood
    result = engine.run_recommended()
    assert result.diagnostics["evidence_weight"] == 0
    assert result.diagnostics["update_blocked_ood"] is True
    assert np.allclose(engine.belief.posterior, before)


def test_independently_retained_checkpoint_detects_rehashed_history(tmp_path):
    client = TestClient(create_app(tmp_path / "checkpoint.db"), base_url="http://localhost")
    state = client.post("/sessions", json={"seed": 766, "max_experiments": 1}).json()
    client.post(f"/sessions/{state['id']}/experiments/run", json={}).raise_for_status()
    repository = client.app.state.repository
    ledger = EvidenceLedger(repository)
    checkpoint = ledger.checkpoint(state["id"])
    assert ledger.verify(state["id"])["externally_anchored"] is False
    record = repository.list_ledger_entries(state["id"])[0]
    record["entry"]["timestamp"] = "rewritten"
    import json
    with repository.connection() as connection:
        connection.execute("UPDATE ledger_entries SET entry_json=?, entry_hash=? WHERE session_id=?",
                           (json.dumps(record["entry"]), canonical_hash(record["entry"]), state["id"]))
    assert ledger.verify(state["id"])["valid"] is True
    report = ledger.verify(state["id"], trusted_head_hash=checkpoint["head_hash"], trusted_record_count=checkpoint["record_count"])
    assert report["reason"] == "trusted_checkpoint_mismatch"


def test_profiles_allow_explicit_overrides():
    assert config_for_profile("demo", candidate_count=10).candidate_count == 10


def test_waveform_quality_does_not_collapse_independent_coupling_uncertainty():
    posterior = NuisancePosterior.from_material(Material())
    before = [posterior.parameter(name).std for name in ("source_coupling", "receiver_coupling")]
    for _ in range(20):
        posterior.passive_quality_update(0.007, 1.0, 1.0)
    assert [posterior.parameter(name).std for name in ("source_coupling", "receiver_coupling")] == before


def test_stereo_integer_and_unsigned_wav_normalization(tmp_path):
    import json
    from scipy.io import wavfile
    from backend.app.replay.datasets import WAVCollectionCounterfactualDataset
    e = Experiment(0.1, 0.1, 0.9, 0.9).to_dict()
    stereo = np.tile(np.array([[-16384, -16384], [16384, 16384]], dtype=np.int16), (160, 1))
    wavfile.write(tmp_path / "stereo.wav", 16000, stereo)
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"actions": [{"experiment": e, "wav": "stereo.wav"}]}))
    values = WAVCollectionCounterfactualDataset(manifest).get_observation(e)
    assert np.max(np.abs(values)) == pytest.approx(0.5)
    unsigned = np.full(320, 128, dtype=np.uint8)
    wavfile.write(tmp_path / "stereo.wav", 16000, unsigned)
    assert np.all(WAVCollectionCounterfactualDataset(manifest).get_observation(e) == 0)


def test_physical_plan_cannot_be_mistaken_for_acquired_evidence(tmp_path):
    import json
    from scripts.physical_campaign import make_plan, audit_manifests
    manifest = tmp_path / "planned.json"
    manifest.write_text(json.dumps(make_plan()))
    report = audit_manifests([manifest])
    assert not report["valid"]
    assert not report["accuracy_established"]
    assert "not declared acquired" in report["errors"][0]["error"]


def test_unexecuted_verification_label_cannot_survive_as_valid_evidence():
    engine = ArgusEngine(ArgusConfig(seed=769, candidate_count=8, max_experiments=1), seed=769)
    engine.action_history = ["verification"]
    assert engine.status()["stop_criteria"]["verification"] is False
