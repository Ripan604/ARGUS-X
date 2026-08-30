from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class FidelityDecision:
    level: int
    model_id: str
    reason: str
    abstain: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


class MultiFidelityController:
    def choose(
        self,
        *,
        structural_uncertainty: float,
        hypothesis_ambiguity: float,
        model_trust: float,
        frequency_hz: float,
        surrogate_available: bool = False,
        imported_available: bool = False,
    ) -> FidelityDecision:
        if model_trust < 0.18:
            return FidelityDecision(-1, "none", "Model trust is too low for defensible prediction; acquire calibration evidence.", True)
        if frequency_hz > 7_000:
            return FidelityDecision(-1, "none", "Requested frequency is outside the validated local model support.", True)
        if structural_uncertainty > 0.72 and hypothesis_ambiguity < 0.75:
            return FidelityDecision(0, "analytical_geometry_v1", "A broad posterior only requires the inexpensive geometry model.")
        if hypothesis_ambiguity > 0.78 and imported_available:
            return FidelityDecision(3, "imported_response_bank", "Close rival hypotheses justify an available imported high-fidelity response.")
        if hypothesis_ambiguity > 0.62 and surrogate_available and model_trust > 0.55:
            return FidelityDecision(2, "cpu_surrogate_ensemble", "Close rival hypotheses justify the calibrated surrogate ensemble.")
        return FidelityDecision(1, "physics_signature_v1", "The physics-inspired signature model balances fidelity and live planning cost.")

