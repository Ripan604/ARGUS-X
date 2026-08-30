from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class StoppingDecision:
    should_stop: bool
    reason: str | None
    explanation: str
    triggered: dict[str, bool]

    def to_dict(self) -> dict:
        return asdict(self)


class StoppingEngine:
    def evaluate(
        self,
        *,
        confidence: float,
        confidence_threshold: float,
        entropy: float,
        entropy_threshold: float,
        credible_area: float,
        credible_area_threshold: float,
        expected_value: float,
        expected_value_threshold: float,
        bayes_risk: float,
        bayes_risk_threshold: float,
        experiment_count: int,
        maximum_experiments: int,
        ood_status: str,
        verification_count: int,
    ) -> StoppingDecision:
        triggered = {
            "posterior_mass": bool(confidence >= confidence_threshold),
            "entropy": bool(entropy <= entropy_threshold),
            "credible_region": bool(credible_area <= credible_area_threshold),
            "low_value_of_information": bool(expected_value <= expected_value_threshold),
            "bayes_risk": bool(bayes_risk <= bayes_risk_threshold),
            "budget": bool(experiment_count >= maximum_experiments),
            "ood": bool(ood_status in {"OUT_OF_DISTRIBUTION", "ABSTAIN"}),
            "verification": bool(verification_count > 0),
        }
        if triggered["ood"]:
            return StoppingDecision(True, "STOP_OOD", "ARGUS abstained because the response is outside the trusted model domain.", triggered)
        if triggered["budget"]:
            return StoppingDecision(True, "STOP_BUDGET", "The configured research measurement budget is exhausted.", triggered)
        defensible = triggered["verification"] and (
            (triggered["posterior_mass"] and triggered["credible_region"])
            or (triggered["entropy"] and triggered["low_value_of_information"])
            or triggered["bayes_risk"]
        )
        if defensible:
            return StoppingDecision(True, "STOP_CONFIDENT", "Posterior concentration is supported by a verification action.", triggered)
        if triggered["low_value_of_information"] and experiment_count >= 4:
            return StoppingDecision(True, "STOP_LOW_VALUE_OF_INFORMATION", "Another modeled measurement has insufficient expected value.", triggered)
        return StoppingDecision(False, None, "Continue the research inspection loop.", triggered)
