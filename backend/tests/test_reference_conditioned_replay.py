"""Integration boundaries for the frozen exploratory replay, not field efficacy."""
from dataclasses import FrozenInstanceError
from hashlib import sha256
import itertools
import json

import numpy as np
import pytest
from threadpoolctl import threadpool_limits

import scripts.validate_reference_conditioned_replay as experiment
from backend.app.evaluation.trajectory_reference_gate import GateBinding


def digest(value):
    return sha256(value.encode()).hexdigest()


def test_unqueried_future_receivers_and_pitches_cannot_change_acquired_prefix():
    pairs = np.asarray(list(itertools.combinations(range(12), 2)))
    K = experiment.kernel(experiment.grid_points(), pairs)
    t = np.arange(128)
    wave = np.sin(2 * np.pi * t / 17.) + .2 * np.sin(2 * np.pi * t / 31.)
    reference = {"catch": np.broadcast_to(wave, (66, len(wave))).copy()}
    bank = {"catch": reference["catch"].copy(),
            "pitch": np.broadcast_to(wave, (66, len(wave))).copy(),
            "metadata": {"surface_temperature_c": [30., 30.1]},
            "provenance": {"timestamp": "unseen-fixture", "sha256": digest("fixture-bank")}}
    bank["catch"][3] = np.roll(wave, 4)
    eligible = np.arange(66) < 20
    sigma = np.full(66, .1)
    binding = GateBinding(*(digest(x) for x in ("model", "adaptive-controller", "protocol", "references")),
                          budgets=experiment.CHECKPOINTS)
    with threadpool_limits(limits=1):
        first = experiment.replay(experiment.ConditionedOracle("raw_global", None, reference, bank),
                                  .4, sigma, K, eligible, "adaptive", None, binding)
    prefix_queries = first["queries"][:4]
    changed = {**bank, "catch": bank["catch"].copy(), "pitch": bank["pitch"].copy()}
    unqueried = np.setdiff1d(np.arange(66), prefix_queries)
    rng = np.random.default_rng(4108)
    changed["catch"][unqueried] = rng.normal(size=(len(unqueried), len(wave)))
    changed["pitch"][unqueried] = rng.normal(size=(len(unqueried), len(wave)))
    with threadpool_limits(limits=1):
        second = experiment.replay(experiment.ConditionedOracle("raw_global", None, reference, changed),
                                   .4, sigma, K, eligible, "adaptive", None, binding)
    assert first["queries"][:4] == second["queries"][:4]
    assert first["trace"][:4] == second["trace"][:4]
    assert len(first["queries"]) == 16 and len(set(first["queries"])) == 16
    assert all(not row["control_disposition"]["next_physical_action_authorized"]
               for row in first["trace"] if "control_disposition" in row)


def test_cached_healthy_model_binds_current_sources_and_cannot_mutate_after_loading():
    report_path = experiment.ROOT / "research_results/healthy_reference_development_2026_10_08.json"
    if not report_path.is_file():
        pytest.skip("Measured healthy development cache is not distributed with this checkout")
    report = json.loads(report_path.read_text())
    if any(not (experiment.ROOT / row["local_path"]).is_file() for row in report["source_banks"]):
        pytest.skip("Original measured healthy anchors are not distributed with this checkout")
    model, source_rows = experiment.load_fitted_transport()
    assert model.model_sha256 == report["model"]["model_sha256"]
    assert model.training_sha256 == report["model"]["training_sha256"]
    assert len(source_rows) == 3
    assert all(experiment.stream_sha(experiment.ROOT / row["local_path"]) == row["sha256"]
               for row in source_rows)
    for name in ("temperatures_c", "receiver_reference", "pitch_reference", "parameter_anchors",
                 "supported_anchors", "healthy_sigma", "development_damage_index"):
        values = getattr(model, name)
        assert not values.flags.writeable
        with pytest.raises(ValueError):
            values.setflags(write=True)
    with pytest.raises(FrozenInstanceError):
        model.policy.stretch_bound = .5


def test_missing_confirmation_returns_unscored_before_any_model_or_waveform_access(tmp_path, monkeypatch):
    directory = tmp_path / "datasets/external/open_guided_waves_confirmation"
    directory.mkdir(parents=True)
    (directory / "argus_manifest.json").write_text(json.dumps({"completed": False, "files": []}))
    monkeypatch.setattr(experiment, "ROOT", tmp_path)
    accessed = []

    def forbidden(*args, **kwargs):
        accessed.append("model-or-native-data")
        raise AssertionError("An incomplete confirmation cannot open model or waveform data")

    for name in ("load_fitted_transport", "healthy_inputs", "load_rows", "read_native_bank", "stream_sha"):
        monkeypatch.setattr(experiment, name, forbidden)
    result = experiment.run_study("confirmation")
    assert result["status"] == "blocked_missing_confirmation_acquisitions"
    assert result["confirmation_scored"] is False and result["acquired_new_banks"] == 0
    assert result["required_new_banks"] == 29 and result["required_healthy_calibration_blocks"] == 19
    assert not result["synthetic_replacements_used"] and not result["gate_field_coverage_established"]
    assert accessed == []
