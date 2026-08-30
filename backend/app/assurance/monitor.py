from __future__ import annotations

from dataclasses import asdict, dataclass, field
from math import exp, log
from typing import Any

import numpy as np

from backend.app.inference.diagnostics import QualityEstimate
from backend.app.inference.structural_posterior import StructuralPosterior


def _clip01(value: float) -> float:
    return float(np.clip(value, 0.0, 1.0))


@dataclass
class SensorReliabilityState:
    """Small beta-binomial channel-health model with transparent evidence counts."""

    sensor_id: str
    accepted_evidence: float = 3.0
    rejected_evidence: float = 1.0
    measurement_count: int = 0
    rejected_count: int = 0
    consecutive_rejections: int = 0
    last_quality: dict[str, Any] = field(default_factory=dict)
    last_failure_reasons: tuple[str, ...] = ()

    @property
    def reliability_mean(self) -> float:
        return float(self.accepted_evidence / (self.accepted_evidence + self.rejected_evidence))

    @property
    def status(self) -> str:
        if self.consecutive_rejections >= 2 or self.reliability_mean < 0.45:
            return "UNRELIABLE"
        if self.reliability_mean < 0.70 or self.last_failure_reasons:
            return "DEGRADED"
        return "NOMINAL"

    def update(self, quality: QualityEstimate) -> None:
        self.measurement_count += 1
        self.last_quality = quality.to_dict()
        self.last_failure_reasons = tuple(quality.reasons)
        if quality.accepted:
            # Soft evidence prevents one merely adequate reading from erasing a fault history.
            self.accepted_evidence += max(0.05, quality.evidence_weight)
            self.rejected_evidence += max(0.0, 0.20 - 0.20 * quality.evidence_weight)
            self.consecutive_rejections = 0
        else:
            self.rejected_evidence += 1.0
            self.rejected_count += 1
            self.consecutive_rejections += 1

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result.update({
            "reliability_mean": self.reliability_mean,
            "status": self.status,
            "last_failure_reasons": list(self.last_failure_reasons),
        })
        return result

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "SensorReliabilityState":
        accepted = payload.get("accepted_evidence", 3.0)
        rejected = payload.get("rejected_evidence", 1.0)
        return cls(
            sensor_id=str(payload.get("sensor_id", "unknown")),
            accepted_evidence=float(accepted),
            rejected_evidence=float(rejected),
            measurement_count=int(payload.get("measurement_count", 0)),
            rejected_count=int(payload.get("rejected_count", 0)),
            consecutive_rejections=int(payload.get("consecutive_rejections", 0)),
            last_quality=dict(payload.get("last_quality", {})),
            last_failure_reasons=tuple(payload.get("last_failure_reasons", ())),
        )


@dataclass
class RuntimeAssuranceMonitor:
    """Accumulates independent health, damage-screening, and drift evidence.

    Outputs are deliberately framed as screening decisions. They are not airworthiness,
    maintenance-release, or structural-safety certification decisions.
    """

    sensor_states: dict[str, SensorReliabilityState] = field(default_factory=dict)
    damage_log_odds: float = field(default_factory=lambda: log(0.15 / 0.85))
    accepted_measurements: int = 0
    rejected_measurements: int = 0
    environment_baseline: dict[str, float] = field(default_factory=dict)
    environment_latest: dict[str, float] = field(default_factory=dict)
    drift_flags: list[str] = field(default_factory=list)
    failure_conditions: list[dict[str, Any]] = field(default_factory=list)
    last_update: dict[str, Any] = field(default_factory=dict)

    def update(
        self,
        quality: QualityEstimate,
        diagnostics: dict[str, Any],
        context: dict[str, Any] | None = None,
        *,
        action_type: str = "diagnostic",
    ) -> dict[str, Any]:
        context = context or {}
        sensor_id = str(context.get("sensor_id") or context.get("node_id") or "simulation")[:128]
        state = self.sensor_states.setdefault(sensor_id, SensorReliabilityState(sensor_id))
        state.update(quality)

        if quality.accepted:
            self.accepted_measurements += 1
        else:
            self.rejected_measurements += 1

        if action_type != "calibration" and quality.accepted:
            # Baseline residual SNR is used only as bounded screening evidence. The
            # spatial posterior still carries the localization inference.
            residual_snr_db = float(diagnostics.get("residual_snr_db", 0.0))
            increment = float(np.clip((residual_snr_db - 2.5) / 5.0, -0.65, 1.05))
            self.damage_log_odds = float(np.clip(
                self.damage_log_odds + increment * quality.evidence_weight,
                -5.0,
                5.0,
            ))

        self._update_environment(context)
        failure_type = self._classify_failure(quality, context)
        if failure_type:
            condition = {
                "measurement_index": self.accepted_measurements + self.rejected_measurements,
                "sensor_id": sensor_id,
                "category": failure_type,
                "reasons": list(quality.reasons),
            }
            self.failure_conditions.append(condition)
            self.failure_conditions = self.failure_conditions[-50:]

        self.last_update = {
            "sensor_id": sensor_id,
            "accepted": quality.accepted,
            "evidence_weight": quality.evidence_weight,
            "action_type": action_type,
            "failure_type": failure_type,
        }
        return self.to_dict()

    def _update_environment(self, context: dict[str, Any]) -> None:
        thresholds = {"temperature_c": 12.0, "humidity_pct": 25.0, "battery_voltage": 0.8}
        self.drift_flags = []
        for name, threshold in thresholds.items():
            raw = context.get(name)
            if raw is None:
                continue
            try:
                value = float(raw)
            except (TypeError, ValueError):
                self.drift_flags.append(f"invalid_{name}")
                continue
            if not np.isfinite(value):
                self.drift_flags.append(f"invalid_{name}")
                continue
            if name not in self.environment_baseline:
                self.environment_baseline[name] = value
            self.environment_latest[name] = value
            if abs(value - self.environment_baseline[name]) > threshold:
                self.drift_flags.append(f"{name}_outside_session_envelope")

    @staticmethod
    def _classify_failure(quality: QualityEstimate, context: dict[str, Any]) -> str | None:
        reasons = set(quality.reasons)
        if "sensor_dropout_or_silence" in reasons:
            return "sensor_failure"
        if "clipping" in reasons or "non_finite_samples" in reasons:
            return "data_corruption"
        if "placement_motion" in reasons:
            return "physical_execution_error"
        if context.get("timestamp_warning"):
            return "timing_error"
        if not quality.accepted:
            return "insufficient_data"
        return None

    @property
    def damage_probability(self) -> float:
        return float(1.0 / (1.0 + exp(-self.damage_log_odds)))

    def structural_assessment(
        self,
        posterior: StructuralPosterior,
        *,
        ood_state: dict[str, Any],
        model_trust: float,
        should_stop: bool = False,
    ) -> dict[str, Any]:
        unknown_probability = _clip01(max(
            float(ood_state.get("score", 0.0)),
            1.0 - float(model_trust),
        ))
        damage_probability = _clip01(self.damage_probability * (1.0 - 0.55 * unknown_probability))
        healthy_probability = _clip01((1.0 - self.damage_probability) * (1.0 - 0.35 * unknown_probability))
        total = healthy_probability + damage_probability + unknown_probability
        healthy_probability /= total
        damage_probability /= total
        unknown_probability /= total

        ambiguity = posterior.ambiguity()
        multi_share = _clip01(0.60 * ambiguity)
        count_probabilities = {
            "healthy_or_no_detectable_damage": healthy_probability,
            "one_candidate_region": damage_probability * (1.0 - multi_share),
            "two_or_more_candidate_regions": damage_probability * multi_share,
            "unknown_or_unsupported": unknown_probability,
        }
        count_total = sum(count_probabilities.values()) or 1.0
        count_probabilities = {key: value / count_total for key, value in count_probabilities.items()}

        unreliable = [item for item in self.sensor_states.values() if item.status == "UNRELIABLE"]
        ood_status = str(ood_state.get("status", "NOMINAL"))
        if ood_status in {"OUT_OF_DISTRIBUTION", "ABSTAIN"} or unknown_probability >= 0.50:
            action = "HUMAN_INSPECTION_REQUIRED"
            basis = "Unknown-domain or model-discrepancy evidence prevents an automated structural conclusion."
        elif unreliable:
            action = "REACQUIRE_OR_REPAIR_SENSOR"
            basis = "At least one sensing channel is unreliable; structural evidence must not be interpreted as healthy."
        elif damage_probability >= 0.70:
            action = "MARK_REGION_AND_VERIFY_WITH_REFERENCE_METHOD"
            basis = "Damage-screening evidence is elevated; the posterior region requires independent confirmation."
        elif healthy_probability >= 0.85 and self.accepted_measurements >= 3 and model_trust >= 0.70:
            action = "NO_DAMAGE_EVIDENCE_UNDER_TESTED_CONDITIONS"
            basis = "Accepted measurements support the healthy hypothesis only within the tested operating envelope."
        elif should_stop:
            action = "REVIEW_BEFORE_ENDING_RESEARCH_SESSION"
            basis = "A research stopping rule fired, but a human remains responsible for engineering disposition."
        else:
            action = "CONTINUE_INSPECTION"
            basis = "Evidence is not yet sufficient for a conservative screening disposition."

        return {
            "scope": "research_screening_only",
            "integrity_state": max(
                {
                    "HEALTHY_OR_NO_DETECTABLE_DAMAGE": healthy_probability,
                    "KNOWN_DAMAGE_CANDIDATE": damage_probability,
                    "UNKNOWN_OR_UNSUPPORTED": unknown_probability,
                },
                key=lambda key: {
                    "HEALTHY_OR_NO_DETECTABLE_DAMAGE": healthy_probability,
                    "KNOWN_DAMAGE_CANDIDATE": damage_probability,
                    "UNKNOWN_OR_UNSUPPORTED": unknown_probability,
                }[key],
            ),
            "state_probabilities": {
                "healthy_or_no_detectable_damage": healthy_probability,
                "known_damage_candidate": damage_probability,
                "unknown_or_unsupported": unknown_probability,
            },
            "defect_count_screening": count_probabilities,
            "candidate_regions": posterior.top_hypotheses(5),
            "engineering_action": action,
            "decision_basis": basis,
            "human_authority_required": action != "CONTINUE_INSPECTION",
            "minimum_detectable_damage_size": "not_established_without_POD_campaign",
            "characterization_status": "size/type/severity are unvalidated screening estimates",
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": 1,
            "accepted_measurements": self.accepted_measurements,
            "rejected_measurements": self.rejected_measurements,
            "damage_log_odds": self.damage_log_odds,
            "damage_screening_probability": self.damage_probability,
            "sensors": {key: value.to_dict() for key, value in self.sensor_states.items()},
            "environment_baseline": self.environment_baseline,
            "environment_latest": self.environment_latest,
            "drift_flags": self.drift_flags,
            "failure_conditions": self.failure_conditions,
            "last_update": self.last_update,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> "RuntimeAssuranceMonitor":
        if not payload:
            return cls()
        return cls(
            sensor_states={
                key: SensorReliabilityState.from_dict(value)
                for key, value in payload.get("sensors", {}).items()
            },
            damage_log_odds=float(payload.get("damage_log_odds", log(0.15 / 0.85))),
            accepted_measurements=int(payload.get("accepted_measurements", 0)),
            rejected_measurements=int(payload.get("rejected_measurements", 0)),
            environment_baseline=dict(payload.get("environment_baseline", {})),
            environment_latest=dict(payload.get("environment_latest", {})),
            drift_flags=list(payload.get("drift_flags", [])),
            failure_conditions=list(payload.get("failure_conditions", [])),
            last_update=dict(payload.get("last_update", {})),
        )
