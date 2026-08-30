from __future__ import annotations

from dataclasses import dataclass, field

from backend.app.inference.diagnostics import QualityEstimate
from backend.app.inference.nuisance_posterior import NuisancePosterior
from backend.app.inference.structural_posterior import StructuralPosterior
from backend.app.models.domain import Material


@dataclass
class JointInferenceState:
    structural: StructuralPosterior
    nuisance: NuisancePosterior
    discrepancy_state: dict = field(default_factory=lambda: {"uncertainty": 0.15, "model_trust": 0.85, "sample_count": 0})
    ood_state: dict = field(default_factory=lambda: {"score": 0.0, "status": "NOMINAL", "method_scores": {}})
    last_quality: QualityEstimate | None = None
    last_calibration: dict | None = None
    revision: int = 0

    @classmethod
    def nominal(cls, structural: StructuralPosterior, material: Material) -> "JointInferenceState":
        return cls(structural, NuisancePosterior.from_material(material))

    def uncertainty_summary(self) -> dict:
        return {
            "structural": self.structural.uncertainty_summary(),
            "metrology": self.nuisance.uncertainty_summary(),
            "model_discrepancy": self.discrepancy_state,
            "ood": self.ood_state,
        }

    def to_dict(self) -> dict:
        return {
            "version": 1,
            "structural": self.structural.to_state(),
            "nuisance": self.nuisance.to_dict(),
            "discrepancy_state": self.discrepancy_state,
            "ood_state": self.ood_state,
            "last_quality": self.last_quality.to_dict() if self.last_quality else None,
            "last_calibration": self.last_calibration,
            "revision": self.revision,
        }

    @classmethod
    def from_dict(cls, payload: dict, material: Material) -> "JointInferenceState":
        quality_payload = payload.get("last_quality")
        if quality_payload:
            quality_payload = {**quality_payload, "reasons": tuple(quality_payload.get("reasons", ())) }
        return cls(
            structural=StructuralPosterior.from_state(payload["structural"]),
            nuisance=NuisancePosterior.from_dict(payload.get("nuisance", {}), material),
            discrepancy_state=payload.get("discrepancy_state", {"uncertainty": 0.15, "model_trust": 0.85, "sample_count": 0}),
            ood_state=payload.get("ood_state", {"score": 0.0, "status": "NOMINAL", "method_scores": {}}),
            last_quality=QualityEstimate(**quality_payload) if quality_payload else None,
            last_calibration=payload.get("last_calibration"),
            revision=int(payload.get("revision", 0)),
        )

