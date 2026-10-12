from __future__ import annotations

import hashlib
import json
from pathlib import Path
from zipfile import ZipFile

import numpy as np
import pytest

from scripts.validate_measured_gfrp import (
    MODEL_NAMES, cluster_bootstrap, cross_plate_duplicates, evaluate_grouped,
    load_feature_cache, make_model, metrics, normalized_pcm, permute_within_plates,
    publisher_label, run_study, verify_archive_members,
)
from scripts.prepare_tud_gfrp_dataset import parse_waveform_name


def toy_data():
    groups = np.repeat(np.arange(1, 9), 8)
    labels = np.tile([0, 0, 0, 0, 1, 1, 1, 1], 8)
    x = np.column_stack((labels * 2 + groups * 0.01, np.arange(len(labels)) * 0.1)).astype(float)
    return x, labels, groups


def test_plate_fold_separation_and_train_only_scaler_survive_extreme_test_data():
    x, labels, groups = toy_data()
    result = evaluate_grouped(x, labels, groups, model_names=("logistic_regression",))
    covered = []
    for fold in result["folds"]:
        assert set(fold["train_plates"]).isdisjoint(fold["test_plates"])
        train = np.asarray(fold["train_indices"])
        assert np.allclose(fold["models"]["logistic_regression"]["training_scaler_mean"], x[train].mean(axis=0))
        covered.extend(fold["test_indices"])
    assert sorted(covered) == list(range(len(labels)))
    first = result["folds"][0]
    changed = x.copy()
    changed[first["test_indices"]] += 100000
    second = evaluate_grouped(changed, labels, groups, model_names=("logistic_regression",))["folds"][0]
    assert second["models"]["logistic_regression"]["training_scaler_mean"] == first["models"]["logistic_regression"]["training_scaler_mean"]


def test_single_class_test_folds_remain_rejected_with_missing_predictions():
    groups = np.repeat([1, 2, 3, 4], 4)
    labels = np.repeat([0, 1, 0, 1], 4)
    result = evaluate_grouped(np.ones((16, 2)), labels, groups, model_names=("majority_no_features",))
    assert len(result["folds"]) == 4
    assert all(fold["status"] == "rejected_single_class_partition" for fold in result["folds"])
    output = result["models"]["majority_no_features"]
    assert output["aggregate"] is None
    assert output["valid_prediction_count"] == 0
    assert output["missing_prediction_indices"] == list(range(16))


def test_majority_baseline_cannot_use_feature_or_filename_shortcuts():
    x, labels, groups = toy_data()
    x[:, 0] = labels * 1e9
    output = evaluate_grouped(x, labels, groups, model_names=("majority_no_features",))["models"]["majority_no_features"]
    assert output["aggregate"]["balanced_accuracy"] == 0.5
    assert output["aggregate"]["roc_auc"] == 0.5
    assert output["aggregate"]["confusion_counts"] == {"tn": 32, "fp": 0, "fn": 32, "tp": 0}


def test_model_factory_contains_only_frozen_baselines_and_finite_train_scaler():
    for name in MODEL_NAMES:
        assert list(make_model(name, 4).named_steps) == ["scale", "model"]
    forest = make_model("random_forest", 4).named_steps["model"]
    assert forest.n_estimators == 300
    assert forest.min_samples_leaf == 3
    assert forest.n_jobs == 1
    with pytest.raises(ValueError):
        make_model("tuned_after_test", 4)


@pytest.mark.parametrize("plate,point,modifier,label", [
    (1, 1, None, 0), (4, 48, "Schlagschaden", 1), (5, 9, None, 1),
    (6, 11, None, 0), (7, 25, None, 1), (7, 1, "Zusatz", 1), (8, 19, None, 1), (8, 31, None, 0),
])
def test_publisher_rules_use_documented_plate_points_and_modifiers(plate, point, modifier, label):
    assert publisher_label({"plate": plate, "point": point, "measurement_modifier": modifier}) == label
    middle = f"{modifier}_" if modifier else ""
    directory = "defect" if label else "intact"
    row = parse_waveform_name(Path(directory) / f"Schaum_P{plate}_{middle}A_D1_{point:02d}.wav")
    assert row["label"] == publisher_label(row)


def test_unregistered_plate_or_modifier_is_not_silently_relabelled():
    for row in ({"plate": 9, "point": 1}, {"plate": 5, "point": 1, "measurement_modifier": "Schlagschaden"}):
        with pytest.raises(ValueError):
            publisher_label(row)


def test_all_cross_plate_duplicate_members_are_excluded_but_within_plate_repeats_stay():
    rows = [{"plate": 1, "pcm_sha256": "same"}, {"plate": 2, "pcm_sha256": "same"},
            {"plate": 3, "pcm_sha256": "within"}, {"plate": 3, "pcm_sha256": "within"}]
    assert cross_plate_duplicates(rows) == [0, 1]


def test_decoded_pcm_integer_scaling_precedes_stereo_averaging_and_unsigned_centering():
    stereo = np.full((32, 2), 16384, dtype=np.int16)
    assert np.allclose(normalized_pcm(stereo), 0.5)
    unsigned = np.full(32, 128, dtype=np.uint8)
    assert np.array_equal(normalized_pcm(unsigned), np.zeros(32))
    with pytest.raises(ValueError):
        normalized_pcm(np.full(32, np.nan))


def test_cached_npz_objects_are_blocked_and_numeric_cache_remains_auditable(tmp_path):
    unsafe = tmp_path / "object.npz"
    np.savez(unsafe, features=np.ones((2, 15), dtype=object), labels=np.array([0, 1]), groups=np.array([1, 2]), metadata="{}")
    with pytest.raises(ValueError, match="Object arrays"):
        load_feature_cache(unsafe)
    numeric = tmp_path / "numeric.npz"
    np.savez(numeric, features=np.ones((2, 15)), labels=np.array([0, 1]), groups=np.array([1, 2]), metadata=json.dumps({"rows": []}))
    assert load_feature_cache(numeric)[0].shape == (2, 15)


def test_extracted_bytes_must_match_publisher_archive_member(tmp_path):
    archive = tmp_path / "source.zip"
    name = "unaugmented_data/intact/clip.wav"
    with ZipFile(archive, "w") as stream:
        stream.writestr(name, b"recorded bytes")
    rows = [{"relative_path": name, "wav_sha256": hashlib.sha256(b"recorded bytes").hexdigest()}]
    assert verify_archive_members(archive, rows)["all_extracted_wav_bytes_match_archive"] is True
    rows[0]["wav_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="differs"):
        verify_archive_members(archive, rows)


def test_within_plate_permutations_preserve_counts_and_are_deterministic():
    _, labels, groups = toy_data()
    first = permute_within_plates(labels, groups, 17)
    assert np.array_equal(first, permute_within_plates(labels, groups, 17))
    assert not np.array_equal(first, labels)
    for group in np.unique(groups):
        assert sorted(first[groups == group]) == sorted(labels[groups == group])


def test_cluster_bootstrap_resamples_plates_and_retains_small_cluster_limitation():
    _, labels, groups = toy_data()
    probabilities = labels * 0.8 + 0.1
    result = cluster_bootstrap(labels, probabilities, groups, repeats=50, seed=4)
    assert result["independent_clusters"] == 8
    assert result["valid_resamples"] == 50
    assert result["ci95_percentile"]["balanced_accuracy"] == [1.0, 1.0]
    assert result == cluster_bootstrap(labels, probabilities, groups, repeats=50, seed=4)
    assert metrics(labels, probabilities)["f1"] == 1


def test_study_refuses_to_overwrite_historical_or_new_result(tmp_path):
    output = tmp_path / "retained.json"
    output.write_text("original", encoding="utf-8")
    with pytest.raises(FileExistsError):
        run_study(output)
    assert output.read_text() == "original"
