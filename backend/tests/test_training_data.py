import numpy as np
import pytest
import torch
from torch.utils.data import DataLoader, TensorDataset

from scripts.prepare_lmsd_dataset import response_to_signal, scenario_geometry
from scripts.train_model import split_indices, evaluate_loss
from scripts.compare_surrogates import compare_predictions


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


def test_evaluation_loss_weights_partial_batch_by_samples():
    inputs = torch.zeros((5, 1))
    targets = torch.tensor([[0.], [0.], [0.], [0.], [10.]])
    model = torch.nn.Identity()
    loader = DataLoader(TensorDataset(inputs, targets), batch_size=4)
    expected = float(torch.nn.functional.smooth_l1_loss(inputs, targets))
    assert evaluate_loss(model, loader, torch.device("cpu")) == pytest.approx(expected)


def test_training_split_rejects_empty_partitions_and_bad_mode():
    with pytest.raises(ValueError):
        split_indices({}, 2, 23, "random")
    with pytest.raises(ValueError):
        split_indices({}, 100, 23, "typo")


def test_paired_comparison_uses_one_scale_and_correct_advantage_direction():
    y = np.arange(12, dtype=float).reshape(6, 2)
    report = compare_predictions(y, y + 2, y + 1, np.array([1., 2.]), ["a", "b"])
    assert report["paired_mae_advantage"]["mean"] == pytest.approx(.75)
    assert report["features_with_over_10_percent_mae_regression"] == []
    assert report["paired_mae_advantage"]["bootstrap_95ci"] == pytest.approx([.75, .75])
    with pytest.raises(ValueError):
        compare_predictions(y, y, y, np.zeros(2), ["a", "b"])
