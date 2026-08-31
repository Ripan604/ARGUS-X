from pathlib import Path

import numpy as np

from backend.app.models.sim2real import CovarianceTransport
from backend.app.ood.acoustic_reference import AcousticReferenceMonitor
from backend.app.ood.detection import OODDetector
from scripts.benchmark_ae_sim2real import SENSORS, localize
from scripts.prepare_ae_impact_dataset import FEATURE_NAMES as AE_FEATURE_NAMES, ultrasonic_features
from scripts.prepare_tud_gfrp_dataset import parse_waveform_name, point_to_xy


def test_tud_filename_and_grid_contract():
    row = parse_waveform_name(Path("defect/Schaum_P7_Zusatz_A_D2_30.wav"))
    assert row["plate"] == 7
    assert row["point"] == 30
    assert row["label"] == 1
    assert row["damage_type"] == "delamination"
    assert point_to_xy(1) == (0.0, 0.0)
    assert point_to_xy(48) == (1.0, 1.0)


def test_covariance_transport_reduces_moment_gap():
    rng = np.random.default_rng(4)
    source = rng.normal(size=(400, 3))
    target = source @ np.asarray([[1.5, 0.2, 0.0], [0.0, 0.7, 0.3], [0.1, 0.0, 1.2]]) + 3.0
    fitted = CovarianceTransport.fit(source, target, ["a", "b", "c"])
    metrics = fitted.alignment_metrics(source, target)
    assert metrics["mean_standardized_wasserstein_after"] < metrics["mean_standardized_wasserstein_before"]
    assert metrics["relative_covariance_error_after"] < metrics["relative_covariance_error_before"]
    restored = CovarianceTransport.from_dict(fitted.to_dict())
    assert np.allclose(restored.transform(source[:3]), fitted.transform(source[:3]))


def test_measured_reference_only_penalizes_upper_tail():
    rng = np.random.default_rng(9)
    names = ["a", "b"]
    reference = rng.normal(size=(500, 2))
    monitor = AcousticReferenceMonitor.fit(reference, names, selected_features=("a", "b"))
    center = monitor.assess({"a": 0.0, "b": 0.0})
    outlier = monitor.assess({"a": 50.0, "b": -50.0})
    assert center.score == 0.0
    assert outlier.score > 0.9
    assessment = OODDetector().assess(
        np.zeros(4), ensemble_disagreement=0.0, measurement_quality=1.0, acoustic_reference_score=1.0
    )
    assert assessment.method_scores["real_acoustic_reference"] == 1.0
    assert assessment.status in {"OUT_OF_DISTRIBUTION", "ABSTAIN"}


def test_ae_feature_and_localization_contract():
    sample_rate = 2_000_000
    time = np.arange(1_600) / sample_rate
    signal = np.zeros_like(time)
    burst = np.sin(2 * np.pi * 250_000 * np.arange(24) / sample_rate) * np.hanning(24)
    signal[400:424] = burst
    features = ultrasonic_features(signal)
    assert features.shape == (len(AE_FEATURE_NAMES),)
    assert np.all(np.isfinite(features))
    truth = np.asarray([0.43, 0.61])
    speed = 3_000.0
    times = np.linalg.norm(SENSORS - truth, axis=1) / speed
    estimate = localize(times, speed)
    assert np.linalg.norm(estimate - truth) < 0.01
