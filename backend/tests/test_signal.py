import numpy as np

from backend.app.signal.processing import analyze_signal, extract_features, preprocess_signal


def test_preprocessing_removes_dc_and_extracts_frequency():
    sample_rate = 16_000
    time = np.arange(1_920) / sample_rate
    samples = 0.5 + np.sin(2 * np.pi * 2_000 * time)
    processed = preprocess_signal(samples, sample_rate)
    features = extract_features(samples, sample_rate)
    assert abs(float(processed.mean())) < 1e-3
    assert abs(features["dominant_frequency_hz"] - 2_000) < 25
    assert features["rms"] > 0


def test_analysis_payload_is_downsampled():
    result = analyze_signal(np.random.default_rng(1).normal(size=5_000), 16_000, max_points=500)
    assert len(result["waveform"]) <= 500
    assert result["spectrogram_db"]
