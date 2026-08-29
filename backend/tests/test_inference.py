import numpy as np

from backend.app.inference.belief import BeliefState, entropy, normalize_probability_grid, posterior_update


def test_probability_normalization_and_entropy():
    grid = normalize_probability_grid(np.ones((20, 20)))
    assert np.isclose(grid.sum(), 1.0)
    assert np.isclose(entropy(grid, normalized=True), 1.0)


def test_bayesian_update_concentrates_consistent_evidence():
    prior = np.ones((8, 8))
    likelihood = np.ones((8, 8))
    likelihood[3, 5] = 12
    posterior = posterior_update(prior, likelihood)
    assert np.isclose(posterior.sum(), 1.0)
    assert np.unravel_index(np.argmax(posterior), posterior.shape) == (3, 5)
    assert entropy(posterior) < entropy(prior)


def test_belief_estimate_is_in_panel():
    belief = BeliefState(20)
    estimate = belief.estimate()
    assert 0 <= estimate["mean_x"] <= 1
    assert 0 <= estimate["mean_y"] <= 1
    assert np.isclose(belief.posterior.sum(), 1.0)
