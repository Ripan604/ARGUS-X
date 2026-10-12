"""Physical time origin must gate inference and remain bound to saved evidence."""
from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import json

import numpy as np
import pytest

from backend.app.core.config import ArgusConfig
from backend.app.database.repository import SessionRepository
from backend.app.schemas.api import CreateSessionRequest
from backend.app.services.engine import ArgusEngine
from backend.app.services.session_manager import SessionManager


def declaration(experiment, rate=16000):
    digest = hashlib.sha256(json.dumps(experiment.to_dict(), sort_keys=True,
        separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    return {"kind": "trigger_aligned_recording", "sample_rate_hz": rate,
        "trigger_sample_index": 0, "max_trigger_alignment_error_us": 5.0,
        "max_clock_error_ppm": 100.0, "reference_sha256": "a" * 64,
        "operator": "Synthetic test operator", "arrival_adapter_validated": True,
        "calibrated_at_utc": datetime.now(timezone.utc).isoformat(),
        "experiment_sha256": digest, "drive_adapter": "validated_experiment_reference"}


@pytest.mark.parametrize("action", ["diagnostic", "calibration", "verification"])
def test_physical_engine_without_internal_timing_cannot_change_inference(action):
    engine = ArgusEngine(ArgusConfig(candidate_count=8, max_experiments=2,
        enable_ood_layer=False, enable_discrepancy_model=False), seed=877)
    plan = replace(engine.current_recommendation, action_type=action,
        structured_explanation={"calibration_type": "direct_path"})
    experiment = plan.selected.experiment
    signal = engine.acquisition_simulator.simulate_baseline(experiment)
    grid = engine.belief.posterior.copy()
    nuisance = engine.joint_state.nuisance.to_dict()
    screening = engine.assurance.damage_log_odds
    result = engine.process_signal(signal, experiment, plan,
        {"sensor_id": "simulation_fake", "hardware_frame_checked": True},
        physical_acquisition=True, plan_next=False)
    assert not result.quality["accepted"]
    assert result.diagnostics["update_blocked_physical_timing"]
    assert result.diagnostics["evidence_weight"] == 0
    if action == "calibration":
        assert not result.calibration_result["accepted"]
    np.testing.assert_array_equal(engine.belief.posterior, grid)
    assert engine.joint_state.nuisance.to_dict() == nuisance
    assert engine.assurance.damage_log_odds == screening
    assert engine.joint_state.ood_state["decision_confidence_cap"] == 0
    assert not engine.prior_signals


def test_external_timing_declaration_is_saved_but_not_host_certified(tmp_path):
    repository = SessionRepository(tmp_path / "timing.db")
    manager = SessionManager(repository)
    runtime = manager.create(CreateSessionRequest(mode="physical", seed=878, max_experiments=1))
    experiment = runtime.engine.current_recommendation.selected.experiment
    signal = runtime.engine.acquisition_simulator.simulate_baseline(experiment)
    evidence = declaration(experiment)
    result = manager.process_samples(runtime.id, signal, 16000, experiment,
        sensor_metadata={"acquisition_timing": evidence})
    assert not result.diagnostics["update_blocked_physical_timing"]
    assert result.diagnostics["hardware_acquisition"] == evidence
    assert result.diagnostics["physical_timing"]["supported"] is True
    restored_repository = SessionRepository(tmp_path / "timing.db")
    stored = restored_repository.list_experiments(runtime.id)[0]
    assert stored["diagnostics"]["hardware_acquisition"] == evidence
    # Mutating a declaration changes the bound evidence even when the samples
    # and posterior happen to remain identical.
    assert manager.ledger.verify(runtime.id)["valid"] is True
    stored["diagnostics"]["hardware_acquisition"]["reference_sha256"] = "b" * 64
    with restored_repository.connection() as connection:
        connection.execute("UPDATE experiments SET diagnostics_json=? WHERE session_id=?",
                           (json.dumps(stored["diagnostics"]), runtime.id))
    assert manager.ledger.verify(runtime.id)["valid"] is False


def test_public_metadata_cannot_claim_internal_frame_validation(tmp_path):
    manager = SessionManager(SessionRepository(tmp_path / "forged.db"))
    runtime = manager.create(CreateSessionRequest(mode="physical", seed=879, max_experiments=1))
    experiment = runtime.engine.current_recommendation.selected.experiment
    signal = runtime.engine.acquisition_simulator.simulate_baseline(experiment)
    result = manager.process_samples(runtime.id, signal, 16000, experiment,
        sensor_metadata={"hardware_frame_checked": True,
                         "acquisition_timing": {"protocol_version": 2}})
    assert result.diagnostics["update_blocked_physical_timing"]
    assert result.diagnostics["evidence_weight"] == 0
    assert not result.quality["accepted"]
