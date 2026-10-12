from dataclasses import replace

import numpy as np
import pytest
from scipy.integrate import quad
from scipy.special import logsumexp

from backend.app.active_learning.nuisance_design import (
    NuisanceArrivalTimeDesign, SpatialDesignRegions, gaussian_mixture_information,
)
from backend.app.core.config import ArgusConfig
from backend.app.inference.nuisance_posterior import NuisancePosterior
from backend.app.models.domain import Experiment, Material, Panel
from backend.app.schemas.api import CreateSessionRequest
from backend.app.services.engine import ArgusEngine


def test_information_limits_and_units():
    p = np.asarray([0.25, 0.75])
    zero, h = gaussian_mixture_information(p, np.zeros(2), np.ones(2))
    assert zero == pytest.approx(0, abs=1e-12)
    separate, _ = gaussian_mixture_information(p, np.asarray([-20.0, 20.0]), np.ones(2))
    assert separate == pytest.approx(h, abs=1e-12)
    base, _ = gaussian_mixture_information(p, np.asarray([-0.3, 1.2]), np.asarray([0.5, 0.8]))
    transformed, _ = gaussian_mixture_information(p, np.asarray([-0.3, 1.2]) * 1e-3 + 12, np.asarray([0.5, 0.8]) * 1e-6)
    assert base == pytest.approx(transformed, abs=1e-11)


def test_quadrature_matches_independent_adaptive_integration():
    p = np.asarray([0.2, 0.5, 0.3])
    mu, var = np.asarray([-1.0, 0.3, 1.4]), np.asarray([0.8, 1.2, 0.6])
    computed, entropy = gaussian_mixture_information(p, mu, var, order=96)

    def integrand(y):
        log_f = -0.5 * (np.log(2 * np.pi * var) + (y - mu) ** 2 / var)
        return float(np.sum(p * np.exp(log_f) * (log_f - logsumexp(np.log(p) + log_f))) / np.log(2))

    integrated, _ = quad(integrand, -15, 15, epsabs=1e-10)
    assert 0 < computed < entropy
    assert computed == pytest.approx(integrated, abs=1e-8)


def test_common_additive_nuisance_cannot_create_information():
    p, mu = np.asarray([0.3, 0.7]), np.asarray([-1.0, 1.0])
    values = [gaussian_mixture_information(p, mu, np.ones(2) * variance, order=96)[0] for variance in (0.1, 0.5, 2, 20)]
    assert all(a > b for a, b in zip(values, values[1:]))


def test_complete_posterior_partition_uses_physical_distance_and_preserves_mass():
    panel = Panel(2.0, 0.2)
    posterior = np.arange(1, 25).reshape(4, 6)
    hypotheses = [{"x": 0.25, "y": 0.1}, {"x": 0.75, "y": 0.9}]
    regions = SpatialDesignRegions.from_posterior(posterior, hypotheses, panel)
    assert regions.probabilities.sum() == pytest.approx(1)
    assert len(regions.cell_probabilities) == posterior.size
    centers = np.asarray([[0.5, 0.02], [1.5, 0.18]])
    expected = np.argmin(np.sum((regions.coordinates_m[:, None] - centers[None]) ** 2, axis=2), axis=1)
    np.testing.assert_array_equal(regions.membership, expected)
    np.testing.assert_allclose(regions.probabilities, np.bincount(expected, weights=posterior.ravel() / posterior.sum()))


def _bimodal_regions():
    posterior = np.zeros((20, 20))
    posterior[4, 3], posterior[15, 16] = 0.5, 0.5
    hypotheses = [{"x": 3.5 / 20, "y": 4.5 / 20}, {"x": 16.5 / 20, "y": 15.5 / 20}]
    panel = Panel()
    return panel, SpatialDesignRegions.from_posterior(posterior, hypotheses, panel)


def test_timing_calibration_restores_information_without_phase_double_counting():
    panel, regions = _bimodal_regions()
    nuisance = NuisancePosterior.from_material(Material())
    experiment = Experiment(0.05, 0.05, 0.2, 0.15)
    design = NuisanceArrivalTimeDesign(panel, 16_000)
    nuisance.parameter("timing_offset").std = 0.003
    uncertain = design.analyze(experiment, regions, nuisance)
    nuisance.parameter("timing_offset").std = 1e-6
    calibrated = design.analyze(experiment, regions, nuisance)
    assert calibrated.information_bits > uncertain.information_bits
    assert calibrated.diagnostics["nuisance_penalty_bits"] < uncertain.diagnostics["nuisance_penalty_bits"]
    # Frequency alone cannot multiply evidence when the observation is arrival
    # time and the assumed arrival noise is the same.
    changed_frequency = design.analyze(replace(experiment, frequency_start_hz=4000, frequency_end_hz=6000), regions, nuisance)
    assert changed_frequency.information_bits == pytest.approx(calibrated.information_bits)


def test_within_region_spread_and_pose_uncertainty_are_retained():
    panel = Panel(0.8, 0.2)
    hypotheses = [{"x": 0.2, "y": 0.5}, {"x": 0.8, "y": 0.5}]
    regions = SpatialDesignRegions.from_posterior(np.ones((20, 20)), hypotheses, panel)
    nuisance = NuisancePosterior.from_material(Material())
    analysis = NuisanceArrivalTimeDesign(panel, 16_000).analyze(Experiment(0.05, 0.2, 0.4, 0.9), regions, nuisance)
    budget = analysis.diagnostics["variance_budget_s2"]
    assert budget["within_region"] > 0
    assert budget["pose"] > 0
    assert budget["timing"] > 0
    assert budget["velocity"] > 0
    total = np.asarray(analysis.diagnostics["arrival_std_s"]) ** 2 @ regions.probabilities
    assert sum(budget.values()) == pytest.approx(total)


def test_single_region_and_coincident_probe_remain_finite():
    posterior = np.zeros((10, 10)); posterior[5, 5] = 1
    panel = Panel()
    regions = SpatialDesignRegions.from_posterior(posterior, [{"x": 0.55, "y": 0.55}], panel)
    result = NuisanceArrivalTimeDesign(panel, 16_000).analyze(Experiment(0.55, 0.55, 0.9, 0.9), regions, NuisancePosterior.from_material(Material()))
    assert result.information_bits == 0
    assert result.diagnostics["variance_budget_s2"]["pose"] > 0


def test_opt_in_changes_planning_diagnostics_without_changing_posterior_or_truth():
    config = ArgusConfig(seed=672, candidate_count=8, enable_nuisance_aware_design=True)
    engine = ArgusEngine(config, seed=672)
    before = engine.belief.posterior.copy()
    nuisance_before = engine.joint_state.nuisance.to_dict()
    truth_before = engine.truth
    acquisition_before = engine.acquisition_simulator.material
    recommendation = engine.neo_planner.recommend(engine.joint_state, [])
    diag = recommendation.structured_explanation["nuisance_design"]
    assert diag["enabled"]
    assert 0 <= diag["information_bits"] <= diag["hypothesis_entropy_bits"]
    assert diag["posterior_mass"] == pytest.approx(1)
    assert diag["field_calibrated"] is False
    assert diag["quadrature_error_bits"] >= 0
    assert recommendation.selected.nuisance_information_bits == diag["information_bits"]
    np.testing.assert_array_equal(before, engine.belief.posterior)
    assert nuisance_before == engine.joint_state.nuisance.to_dict()
    assert engine.truth == truth_before
    assert engine.acquisition_simulator.material == acquisition_before


def test_legacy_default_and_strict_flag_validation():
    assert not ArgusConfig().enable_nuisance_aware_design
    engine = ArgusEngine(ArgusConfig(candidate_count=8), seed=672)
    assert engine.current_recommendation.structured_explanation["nuisance_design"]["enabled"] is False
    for malformed in (1, "true", None):
        with pytest.raises(ValueError):
            ArgusConfig(enable_nuisance_aware_design=malformed)
        with pytest.raises(ValueError):
            CreateSessionRequest(enable_nuisance_aware_design=malformed)


def test_api_opt_in_survives_database_restore(tmp_path):
    from fastapi.testclient import TestClient
    from backend.app.main import create_app

    database = tmp_path / "nuisance-design.db"
    first = TestClient(create_app(database), base_url="http://localhost")
    response = first.post("/sessions", json={"seed": 672, "enable_nuisance_aware_design": True})
    assert response.status_code == 201
    created = response.json()
    assert created["config"]["enable_nuisance_aware_design"] is True
    restored = TestClient(create_app(database), base_url="http://localhost").get(f"/sessions/{created['id']}").json()
    assert restored["config"]["enable_nuisance_aware_design"] is True
    recommendation = TestClient(create_app(database), base_url="http://localhost").get(f"/sessions/{created['id']}/recommendation").json()
    assert recommendation["structured_explanation"]["nuisance_design"]["enabled"] is True


@pytest.mark.parametrize("probabilities,means,variances", [
    ([], [], []), ([1], [0], [0]), ([1, -0.1], [0, 1], [1, 1]),
    ([1], [float("nan")], [1]), ([1, 0], [0], [1]),
])
def test_invalid_mixture_inputs_fail_explicitly(probabilities, means, variances):
    with pytest.raises(ValueError):
        gaussian_mixture_information(probabilities, means, variances)
