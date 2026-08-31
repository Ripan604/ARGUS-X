from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.stats import wasserstein_distance


def _symmetric_power(matrix: np.ndarray, power: float, floor: float = 1e-6) -> np.ndarray:
    values, vectors = np.linalg.eigh((matrix + matrix.T) / 2)
    values = np.maximum(values, floor) ** power
    return (vectors * values) @ vectors.T


@dataclass(frozen=True)
class CovarianceTransport:
    """Robust CORAL transport from simulated features to a measured domain.

    The transform is deliberately feature-level. It does not claim to turn a
    simulated waveform into a physical measurement; it aligns first- and
    second-order feature statistics while the OOD layer retains authority to
    reject unsupported measurements.
    """

    feature_names: tuple[str, ...]
    source_median: np.ndarray
    source_scale: np.ndarray
    target_median: np.ndarray
    target_scale: np.ndarray
    source_center: np.ndarray
    target_center: np.ndarray
    matrix: np.ndarray
    regularization: float = 1e-3

    @classmethod
    def fit(
        cls,
        source: np.ndarray,
        target: np.ndarray,
        feature_names: list[str] | tuple[str, ...],
        regularization: float = 1e-3,
    ) -> "CovarianceTransport":
        source = np.asarray(source, dtype=np.float64)
        target = np.asarray(target, dtype=np.float64)
        if source.ndim != 2 or target.ndim != 2 or source.shape[1] != target.shape[1]:
            raise ValueError("Source and target must be finite 2-D arrays with equal feature counts")
        if min(len(source), len(target)) < 3 or not np.all(np.isfinite(source)) or not np.all(np.isfinite(target)):
            raise ValueError("At least three finite source and target rows are required")
        names = tuple(feature_names)
        if len(names) != source.shape[1]:
            raise ValueError("Feature-name count does not match the arrays")

        source_median = np.median(source, axis=0)
        target_median = np.median(target, axis=0)
        source_scale = np.maximum(np.subtract(*np.percentile(source, [75, 25], axis=0)), 1e-8)
        target_scale = np.maximum(np.subtract(*np.percentile(target, [75, 25], axis=0)), 1e-8)
        source_z = (source - source_median) / source_scale
        target_z = (target - target_median) / target_scale
        source_center = source_z.mean(axis=0)
        target_center = target_z.mean(axis=0)
        source_cov = np.cov(source_z - source_center, rowvar=False) + regularization * np.eye(source.shape[1])
        target_cov = np.cov(target_z - target_center, rowvar=False) + regularization * np.eye(target.shape[1])
        matrix = _symmetric_power(source_cov, -0.5) @ _symmetric_power(target_cov, 0.5)
        return cls(
            names,
            source_median,
            source_scale,
            target_median,
            target_scale,
            source_center,
            target_center,
            matrix,
            regularization,
        )

    def transform(self, values: np.ndarray) -> np.ndarray:
        rows = np.asarray(values, dtype=np.float64)
        one_row = rows.ndim == 1
        rows = np.atleast_2d(rows)
        if rows.shape[1] != len(self.feature_names):
            raise ValueError("Feature count does not match the fitted transport")
        standardized = (rows - self.source_median) / self.source_scale
        transported = (standardized - self.source_center) @ self.matrix + self.target_center
        result = transported * self.target_scale + self.target_median
        return result[0] if one_row else result

    def alignment_metrics(self, source: np.ndarray, target: np.ndarray) -> dict[str, float]:
        source = np.asarray(source, dtype=np.float64)
        target = np.asarray(target, dtype=np.float64)
        transported = self.transform(source)
        scale = self.target_scale
        before = (source - np.median(source, axis=0)) / np.maximum(
            np.subtract(*np.percentile(source, [75, 25], axis=0)), 1e-8
        )
        target_z = (target - self.target_median) / scale
        after = (transported - self.target_median) / scale
        before_w = np.mean([wasserstein_distance(before[:, i], target_z[:, i]) for i in range(source.shape[1])])
        after_w = np.mean([wasserstein_distance(after[:, i], target_z[:, i]) for i in range(source.shape[1])])
        before_cov = np.cov(before, rowvar=False)
        after_cov = np.cov(after, rowvar=False)
        target_cov = np.cov(target_z, rowvar=False)
        denominator = max(float(np.linalg.norm(target_cov, ord="fro")), 1e-12)
        return {
            "mean_standardized_wasserstein_before": float(before_w),
            "mean_standardized_wasserstein_after": float(after_w),
            "relative_covariance_error_before": float(np.linalg.norm(before_cov - target_cov, ord="fro") / denominator),
            "relative_covariance_error_after": float(np.linalg.norm(after_cov - target_cov, ord="fro") / denominator),
        }

    def to_dict(self) -> dict:
        return {
            "method": "robust_class_conditional_coral_v1",
            "feature_names": list(self.feature_names),
            "source_median": self.source_median.tolist(),
            "source_scale": self.source_scale.tolist(),
            "target_median": self.target_median.tolist(),
            "target_scale": self.target_scale.tolist(),
            "source_center": self.source_center.tolist(),
            "target_center": self.target_center.tolist(),
            "matrix": self.matrix.tolist(),
            "regularization": self.regularization,
        }

    @classmethod
    def from_dict(cls, payload: dict) -> "CovarianceTransport":
        return cls(
            tuple(payload["feature_names"]),
            np.asarray(payload["source_median"], dtype=np.float64),
            np.asarray(payload["source_scale"], dtype=np.float64),
            np.asarray(payload["target_median"], dtype=np.float64),
            np.asarray(payload["target_scale"], dtype=np.float64),
            np.asarray(payload["source_center"], dtype=np.float64),
            np.asarray(payload["target_center"], dtype=np.float64),
            np.asarray(payload["matrix"], dtype=np.float64),
            float(payload.get("regularization", 1e-3)),
        )
