import numpy as np

from backend.app.active_learning.planner import ExperimentPlanner
from backend.app.core.config import ArgusConfig
from backend.app.simulation.physics import AcousticSimulator


def test_candidate_generation_and_recommendation_are_valid():
    config = ArgusConfig(candidate_count=32)
    planner = ExperimentPlanner(AcousticSimulator(seed=4), config, seed=4)
    posterior = np.ones((20, 20)) / 400
    candidates = planner.generate_candidates(posterior, [])
    recommendation = planner.recommend(posterior, [])
    assert len(candidates) == 32
    assert len(recommendation.top_candidates) == 5
    assert recommendation.selected.experiment in candidates
    assert all(0 <= candidate.source_x <= 1 for candidate in candidates)
    assert np.isfinite(recommendation.selected.final_score)


def test_repetition_has_a_penalty():
    planner = ExperimentPlanner(AcousticSimulator(), ArgusConfig())
    experiment = planner.random_experiment()
    assert planner._repetition_penalty(experiment, [experiment]) > 0.99
