from __future__ import annotations

from dataclasses import asdict, dataclass, field

import numpy as np


@dataclass(frozen=True)
class OODAssessment:
    score: float
    status: str
    method_scores: dict[str, float]
    decision_confidence_cap: float
    recommendation: str
    calibration_count: int

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class OODDetector:
    caution_threshold: float = 0.55
    abstain_threshold: float = 0.82
    calibration_nonconformity: list[float] = field(default_factory=list)
    residual_vectors: list[list[float]] = field(default_factory=list)

    def assess(
        self,
        residual_vector: np.ndarray,
        *,
        ensemble_disagreement: float,
        measurement_quality: float,
    ) -> OODAssessment:
        residual = np.asarray(residual_vector, dtype=np.float64).reshape(-1)
        scale = np.asarray([0.0008, 1.2, 1.0, 1.0], dtype=np.float64)[: len(residual)]
        standardized = residual / np.maximum(scale, 1e-12)
        if len(self.residual_vectors) >= 6:
            history = np.asarray(self.residual_vectors, dtype=np.float64)
            median = np.median(history, axis=0)
            mad = np.median(np.abs(history - median), axis=0) * 1.4826 + 0.35
            robust_distance = float(np.sqrt(np.mean(((standardized - median) / mad) ** 2)))
        else:
            robust_distance = float(np.sqrt(np.mean(standardized**2)))
        statistical_score = float(np.clip(1 - np.exp(-0.30 * robust_distance), 0, 1))
        nonconformity = float(np.linalg.norm(standardized))
        # Small conformal sets are too discrete to support a useful tail claim.
        # Until ten reference scores exist, retain the continuous statistical baseline.
        if len(self.calibration_nonconformity) >= 10:
            calibration = np.asarray(self.calibration_nonconformity)
            conformal_p = float((1 + np.sum(calibration >= nonconformity)) / (len(calibration) + 1))
            conformal_score = 1 - conformal_p
        else:
            conformal_score = float(np.clip(1 - np.exp(-0.20 * nonconformity), 0, 1))
        ensemble_score = float(np.clip(ensemble_disagreement, 0, 1))
        quality_penalty = float(np.clip(1 - measurement_quality, 0, 1))
        combined = float(np.clip(max(statistical_score, conformal_score, ensemble_score) * 0.82 + 0.18 * quality_penalty, 0, 1))
        if combined >= self.abstain_threshold:
            status, cap, recommendation = "ABSTAIN", 0.20, "Do not issue a confident structural result; perform calibration or escalate to a reference method."
        elif combined >= max(self.caution_threshold + 0.15, self.abstain_threshold - 0.12):
            status, cap, recommendation = "OUT_OF_DISTRIBUTION", 0.38, "Acquire a calibration or verification measurement before localization."
        elif combined >= self.caution_threshold:
            status, cap, recommendation = "CAUTION", 0.68, "Collect an additional diverse measurement and monitor residuals."
        else:
            status, cap, recommendation = "NOMINAL", 1.0, "Response is within the current empirical model envelope."
        self.residual_vectors.append(standardized.tolist())
        self.residual_vectors = self.residual_vectors[-128:]
        return OODAssessment(
            combined, status,
            {"robust_residual": statistical_score, "conformal_nonconformity": conformal_score, "ensemble_disagreement": ensemble_score, "quality_penalty": quality_penalty},
            cap, recommendation, len(self.calibration_nonconformity),
        )

    def register_calibration(self, residual_vector: np.ndarray) -> None:
        residual = np.asarray(residual_vector, dtype=np.float64).reshape(-1)
        scale = np.asarray([0.0008, 1.2, 1.0, 1.0], dtype=np.float64)[: len(residual)]
        self.calibration_nonconformity.append(float(np.linalg.norm(residual / np.maximum(scale, 1e-12))))
        self.calibration_nonconformity = self.calibration_nonconformity[-256:]

    def to_dict(self) -> dict:
        return {
            "caution_threshold": self.caution_threshold,
            "abstain_threshold": self.abstain_threshold,
            "calibration_nonconformity": self.calibration_nonconformity,
            "residual_vectors": self.residual_vectors,
        }

    @classmethod
    def from_dict(cls, payload: dict | None) -> "OODDetector":
        if not payload:
            return cls()
        return cls(
            caution_threshold=float(payload.get("caution_threshold", 0.55)),
            abstain_threshold=float(payload.get("abstain_threshold", 0.82)),
            calibration_nonconformity=payload.get("calibration_nonconformity", []),
            residual_vectors=payload.get("residual_vectors", []),
        )
