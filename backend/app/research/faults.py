from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np


@dataclass(frozen=True)
class FaultResult:
    fault_type: str
    applied: bool
    metadata: dict

    def to_dict(self) -> dict:
        return asdict(self)


def inject_fault(samples: np.ndarray, fault_type: str, severity: float = 0.5, seed: int = 71) -> tuple[np.ndarray, FaultResult]:
    values = np.asarray(samples, dtype=np.float32).copy()
    severity = float(np.clip(severity, 0, 1))
    rng = np.random.default_rng(seed)
    metadata: dict = {"severity": severity, "seed": seed}
    if fault_type == "clipped_measurement":
        limit = max(1e-5, float(np.quantile(np.abs(values), 1 - 0.65 * severity)))
        values = np.clip(values, -limit, limit); metadata["limit"] = limit
    elif fault_type == "missing_samples":
        count = max(1, int(len(values) * 0.35 * severity)); start = int(rng.integers(0, max(1, len(values) - count)))
        values[start : start + count] = 0; metadata.update({"start": start, "count": count})
    elif fault_type == "increased_noise":
        noise = float(np.std(values) * (0.5 + 3 * severity)); values += rng.normal(0, noise, len(values)); metadata["noise_std"] = noise
    elif fault_type == "sensor_dropout":
        values[:] = 0
    elif fault_type == "biased_measurement":
        bias = float((0.02 + np.std(values)) * severity); values += bias; metadata["bias"] = bias
    elif fault_type == "coupling_loss":
        factor = 1 - 0.90 * severity; values *= factor; metadata["gain_factor"] = factor
    elif fault_type == "corrupted_packet":
        if len(values):
            indices = rng.choice(len(values), size=max(1, int(len(values) * 0.05 * severity)), replace=False)
            values[indices] = np.nan; metadata["corrupted_count"] = len(indices)
    elif fault_type in {"wrong_timestamp", "position_error"}:
        metadata["signal_unchanged"] = True
    else:
        raise ValueError(f"Unknown fault type: {fault_type}")
    return values, FaultResult(fault_type, True, metadata)

