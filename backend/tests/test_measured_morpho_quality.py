import numpy as np
import pytest

from scripts.validate_measured_morpho_quality import (
    FEATURE_NAMES, build_model, classification_metrics, features_for_signal,
    load_measured_features, run_lopo, shuffled_training_labels,
)


def test_known_confusion_counts_and_single_class_metrics_are_not_fabricated():
    metrics = classification_metrics(np.asarray([0, 0, 1, 1]), np.asarray([.1, .6, .4, .9]))
    assert (metrics["true_good"], metrics["false_bad"], metrics["missed_bad"], metrics["true_bad"]) == (1, 1, 1, 1)
    assert metrics["balanced_accuracy"] == .5
    healthy = classification_metrics(np.zeros(3), np.asarray([.1, .2, .8]))
    assert healthy["auroc"] is None
    assert healthy["balanced_accuracy"] is None
    assert healthy["bad_recall"] is None
    assert healthy["good_recall"] == pytest.approx(2/3)
    assert healthy["false_bad"] == 1


def test_native_waveform_features_distinguish_frequency_and_keep_invalid_samples():
    time = np.arange(500)/1_000_000
    wave = np.sin(2*np.pi*50000*time)
    features = features_for_signal(wave)
    assert len(features) == len(FEATURE_NAMES)
    assert features[4] > .99
    assert features[5] < 1e-20
    assert features[-1] == 1
    dirty = wave.copy(); dirty[0] = np.nan; dirty[1] = np.inf
    assert np.isfinite(features_for_signal(dirty)).all()
    assert features_for_signal(dirty)[-1] == pytest.approx(498/500)
    assert np.isfinite(features_for_signal(np.zeros(500))).all()
    with pytest.raises(ValueError): features_for_signal(wave, 16000)
    with pytest.raises(ValueError): features_for_signal(wave[:100])


def test_scaler_fits_only_training_waveforms_and_does_not_change_on_test_prediction():
    train = np.asarray([[0., 0.], [0., 1.], [1., 0.], [1., 1.]])
    model = build_model("logistic_regression").fit(train, [0, 0, 1, 1])
    mean_before = model.named_steps["scale"].mean_.copy()
    model.predict_proba(np.asarray([[1e6, 1e6]]))
    np.testing.assert_array_equal(model.named_steps["scale"].mean_, train.mean(axis=0))
    np.testing.assert_array_equal(model.named_steps["scale"].mean_, mean_before)


def test_control_shuffles_within_training_panel_and_preserves_each_prevalence():
    panels = np.asarray(["FOD3"]*20 + ["FOD4"]*20)
    labels = np.asarray([0]*2+[1]*18+[0]*18+[1]*2)
    before = labels.copy()
    shuffled = shuffled_training_labels(labels, panels)
    for panel in set(panels):
        assert labels[panels == panel].sum() == shuffled[panels == panel].sum()
    assert np.any(shuffled != labels)
    np.testing.assert_array_equal(labels, before)
    np.testing.assert_array_equal(shuffled, shuffled_training_labels(labels, panels))


def test_leave_panel_out_retains_all_rows_and_all_good_panel_without_group_leakage():
    rng = np.random.default_rng(113)
    panels = np.asarray([p for p in ("FOD3", "FOD4", "FOD5", "FOD6", "FOD7") for _ in range(8)])
    labels = np.asarray([0, 0, 0, 0, 0, 0, 1, 1]*5)
    labels[panels == "FOD6"] = 0
    features = rng.normal(size=(40, 3))
    identifiers = [f"{panels[i]}_{i}" for i in range(40)]
    folds, summaries = run_lopo(features, labels, panels, identifiers,
                                methods=("logistic_regression", "majority_dummy"))
    for fold in folds:
        assert fold["held_out_panel"] not in fold["train_panels"]
        assert not set(fold["train_ids"]) & set(fold["test_ids"])
        assert all(value.startswith(fold["held_out_panel"]) for value in fold["test_ids"])
    for method in summaries:
        assert summaries[method]["attempted_labels"] == 40
        assert summaries[method]["scored_labels"] == 40
        assert summaries[method]["bad_recall_supported_folds"] == 4
        assert summaries[method]["good_recall_supported_folds"] == 5
    healthy = next(f for f in folds if f["held_out_panel"] == "FOD6" and f["method"] == "majority_dummy")
    assert healthy["metrics"]["auroc"] is None
    assert healthy["metrics"]["balanced_accuracy"] is None
    assert healthy["metrics"]["false_bad"] == 0


def test_failed_method_retains_every_attempted_label_in_failure_denominators(monkeypatch):
    def fail(method): raise RuntimeError("Injected model failure")
    monkeypatch.setattr("scripts.validate_measured_morpho_quality.build_model", fail)
    folds, summaries = run_lopo(np.zeros((4, 2)), np.asarray([0, 1, 0, 1]),
        np.asarray(["FOD3", "FOD3", "FOD4", "FOD4"]), ["a", "b", "c", "d"], methods=("majority_dummy",))
    assert len(folds) == 2
    assert all(not fold["completed"] for fold in folds)
    assert sum(len(fold["predictions"]) for fold in folds) == 4
    assert summaries["majority_dummy"]["attempted_labels"] == 4
    assert summaries["majority_dummy"]["scored_labels"] == 0
    assert summaries["majority_dummy"]["failed_folds"] == 2


def test_acquired_numeric_hdf5_labels_bind_uniquely_and_document_real_schema_discrepancy():
    features, labels, panels, rows, audit = load_measured_features()
    assert features.shape == (1011, len(FEATURE_NAMES))
    assert labels.sum() == 136
    assert len({row["signal_id"] for row in rows}) == 1011
    assert np.isfinite(features).all()
    assert set(panels) == {"FOD3", "FOD4", "FOD5", "FOD6", "FOD7"}
    assert audit["FOD3"]["actual_distinct_cycles"] == 22
    assert audit["FOD3"]["readme_cycles"] == 9
    assert audit["FOD6"]["label_counts"].get("BAD", 0) == 0
    assert sum(row["signals"] for row in audit.values()) == 12504
    assert not any(identity in " ".join(FEATURE_NAMES) for identity in ("panel", "cycle", "actuator", "receiver", "timestamp"))
