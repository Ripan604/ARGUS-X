import numpy as np

from scripts.prepare_lmsd_dataset import response_to_signal, scenario_geometry
from scripts.train_model import split_indices


def test_lmsd_response_adapter_and_geometry():
    frequency = np.linspace(0, 1_600, 8_192)
    frf = np.exp(-1j * 2 * np.pi * frequency * 0.01)
    signal, sample_rate = response_to_signal(frf, frequency)
    assert sample_rate == 3_200
    assert len(signal) == 384
    nodes = np.array([[25.0, 25.0], [75.0, 25.0], [25.0, 75.0]])
    center_x, center_y, radius_x, radius_y, severity = scenario_geometry(np.array([0, 1]), nodes)
    assert 0 < center_x < 1 and 0 < center_y < 1
    assert radius_x > radius_y > 0
    assert 0 < severity <= 1


def test_group_split_keeps_scenarios_disjoint():
    rows = [{"scenario": f"case-{index // 4}"} for index in range(24)]
    train, validation, test, detail = split_indices({"rows": rows}, len(rows), seed=9, mode="auto")
    groups = np.asarray([row["scenario"] for row in rows])
    assert detail["mode"] == "group"
    assert set(groups[train]).isdisjoint(groups[validation])
    assert set(groups[train]).isdisjoint(groups[test])
    assert set(groups[validation]).isdisjoint(groups[test])
