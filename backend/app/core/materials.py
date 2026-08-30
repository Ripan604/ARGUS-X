from __future__ import annotations

from dataclasses import dataclass

from backend.app.models.domain import Material


@dataclass(frozen=True)
class MaterialProfile:
    profile_id: str
    label: str
    material: Material
    supported_frequency_hz: tuple[float, float]
    relative_parameter_uncertainty: dict[str, float]
    evidence: str = "synthetic_demo_prior"
    disclaimer: str = "Illustrative prior for simulation; not a sourced or certified material characterization."

    def to_dict(self) -> dict:
        return {
            "profile_id": self.profile_id,
            "label": self.label,
            "material": self.material.to_dict(),
            "supported_frequency_hz": list(self.supported_frequency_hz),
            "relative_parameter_uncertainty": self.relative_parameter_uncertainty,
            "evidence": self.evidence,
            "disclaimer": self.disclaimer,
        }


MATERIAL_PROFILES = {
    "generic_plate": MaterialProfile(
        "generic_plate", "Generic synthetic plate", Material(), (500.0, 7_000.0),
        {"wave_velocity": 0.18, "attenuation": 0.25, "timing_offset": 0.35},
    ),
    "aluminum_demo": MaterialProfile(
        "aluminum_demo", "Aluminum-like audio demo", Material(235.0, 1.05, 3_650.0, 82.0, 0.006, 0.00065),
        (700.0, 7_000.0), {"wave_velocity": 0.14, "attenuation": 0.22, "timing_offset": 0.30},
    ),
    "cfrp_demo": MaterialProfile(
        "cfrp_demo", "CFRP-like synthetic demo", Material(155.0, 2.15, 2_850.0, 118.0, 0.009, 0.00092),
        (600.0, 6_500.0), {"wave_velocity": 0.25, "attenuation": 0.35, "timing_offset": 0.38},
    ),
}


def get_material_profile(profile_id: str) -> MaterialProfile:
    try:
        return MATERIAL_PROFILES[profile_id]
    except KeyError as exc:
        raise ValueError(f"Unknown material profile: {profile_id}") from exc

