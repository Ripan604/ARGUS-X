from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

import numpy as np


REFERENCE_FEATURES = (
    "crest_factor",
    "zero_crossing_rate",
    "spectral_centroid_hz",
    "spectral_bandwidth_hz",
    "spectral_rolloff_hz",
    "dominant_frequency_hz",
    "spectral_entropy",
    "band_energy_low",
    "band_energy_mid",
    "band_energy_high",
    "envelope_peak_time_s",
    "decay_time_s",
    "snr_db",
)


@dataclass(frozen=True)
class AcousticReferenceAssessment:
    distance: float
    empirical_quantile: float
    score: float


@dataclass(frozen=True)
class AcousticReferenceMonitor:
    feature_names: tuple[str, ...]
    median: np.ndarray
    scale: np.ndarray
    reference_distances: np.ndarray
    provenance: dict

    @classmethod
    def fit(
        cls,
        features: np.ndarray,
        all_feature_names: list[str] | tuple[str, ...],
        selected_features: tuple[str, ...] = REFERENCE_FEATURES,
        provenance: dict | None = None,
    ) -> "AcousticReferenceMonitor":
        values = np.asarray(features, dtype=np.float64)
        name_to_index = {name: index for index, name in enumerate(all_feature_names)}
        missing = set(selected_features) - name_to_index.keys()
        if missing:
            raise ValueError(f"Missing acoustic reference features: {sorted(missing)}")
        selected = values[:, [name_to_index[name] for name in selected_features]]
        if selected.ndim != 2 or len(selected) < 20 or not np.all(np.isfinite(selected)):
            raise ValueError("A finite measured reference set with at least 20 rows is required")
        median = np.median(selected, axis=0)
        scale = 1.4826 * np.median(np.abs(selected - median), axis=0)
        scale = np.maximum(scale, np.maximum(np.abs(median) * 1e-6, 1e-8))
        distances = np.sqrt(np.mean(np.clip((selected - median) / scale, -12, 12) ** 2, axis=1))
        return cls(tuple(selected_features), median, scale, np.sort(distances), provenance or {})

    def assess(self, feature_mapping: dict[str, float]) -> AcousticReferenceAssessment:
        vector = np.asarray([feature_mapping[name] for name in self.feature_names], dtype=np.float64)
        if not np.all(np.isfinite(vector)):
            return AcousticReferenceAssessment(float("inf"), 1.0, 1.0)
        distance = float(np.sqrt(np.mean(np.clip((vector - self.median) / self.scale, -12, 12) ** 2)))
        quantile = float(np.searchsorted(self.reference_distances, distance, side="right") / len(self.reference_distances))
        # Preserve a 90% empirical acceptance region; only the upper reference
        # tail contributes to OOD caution/abstention.
        score = float(np.clip((quantile - 0.90) / 0.10, 0, 1))
        return AcousticReferenceAssessment(distance, quantile, score)

    def to_dict(self) -> dict:
        return {
            "method": "robust_empirical_acoustic_reference_v1",
            "feature_names": list(self.feature_names),
            "median": self.median.tolist(),
            "scale": self.scale.tolist(),
            "reference_distances": self.reference_distances.tolist(),
            "provenance": self.provenance,
        }

    @classmethod
    def from_dict(cls, payload: dict) -> "AcousticReferenceMonitor":
        return cls(
            tuple(payload["feature_names"]),
            np.asarray(payload["median"], dtype=np.float64),
            np.asarray(payload["scale"], dtype=np.float64),
            np.asarray(payload["reference_distances"], dtype=np.float64),
            dict(payload.get("provenance", {})),
        )

    @classmethod
    def from_file(cls, path: Path) -> "AcousticReferenceMonitor":
        return cls.from_dict(json.loads(path.read_text(encoding="utf-8")))
