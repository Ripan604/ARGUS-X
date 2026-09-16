"""Controlled synthetic paired evaluation; truth is used only by acquisition/reporting.

Unlike the older policy matrix this holds candidate opportunities and acquisition
random numbers fixed by (seed, step), and reports localization uncertainty.
"""
from __future__ import annotations

from dataclasses import fields, replace
import hashlib
import json
import platform
from time import perf_counter
from typing import Callable

import numpy as np
import scipy

from backend.app.core.config import ArgusConfig
from backend.app.evaluation.benchmark import uniform_grid_experiments
from backend.app.models.domain import Experiment, Material, Panel
from backend.app.safety.constraints import ExperimentConstraintEngine
from backend.app.services.engine import ArgusEngine
from backend.app.simulation.physics import AcousticSimulator


VALIDATION_SEEDS = tuple(range(41_000, 41_020))
PILOT_SEEDS = tuple(range(31_000, 31_006))
CONTEXTS = {
    "nominal": {"velocity_multiplier": 1.0, "attenuation_multiplier": 1.0, "noise_multiplier": 1.0},
    "mismatch_noise": {"velocity_multiplier": 1.02, "attenuation_multiplier": 1.04, "noise_multiplier": 2.0},
}
VARIANTS = {"legacy_proxy": False, "nuisance_aware": True}


def candidate_banks(seed: int, steps: int, count: int = 24) -> list[list[Experiment]]:
    """Public, posterior-independent opportunities shared by all paired policies."""
    if steps < 1 or count < 8:
        raise ValueError("At least one step and eight candidates are required")
    rng = np.random.default_rng(np.random.SeedSequence([seed, 101]))
    constraints = ExperimentConstraintEngine(ArgusConfig())
    banks = []
    for step in range(steps):
        bank = uniform_grid_experiments(8)
        while len(bank) < count:
            xy = rng.uniform(0.04, 0.96, 4)
            low, high = ((1200.0, 3000.0), (2200.0, 4400.0), (3400.0, 6200.0))[int(rng.integers(3))]
            experiment = Experiment(*map(float, xy), low, high, 0.48, 0.12,
                                    ("chirp", "impulse", "tone_burst")[int(rng.integers(3))])
            if constraints.evaluate(experiment).feasible:
                bank.append(experiment)
        banks.append(bank)
    return banks


def bank_digest(bank: list[Experiment]) -> str:
    payload = json.dumps([item.to_dict() for item in bank], sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def acquisition_rng(seed: int, step: int) -> np.random.Generator:
    return np.random.default_rng(np.random.SeedSequence([seed, step, 202]))


class ControlledCandidateEngine(ArgusEngine):
    """Keep production inference/control, replace only candidate opportunities."""

    def __init__(self, *, banks: list[list[Experiment]], **kwargs):
        self.validation_banks = banks
        super().__init__(**kwargs)

    def _recommend(self, no_go_regions=None, unavailable_actions=None):
        def bank(history):
            return list(self.validation_banks[min(len(history), len(self.validation_banks) - 1)])

        # The baseline also drives the dual-control diagnostic-value estimate.
        self.planner.generate_candidates = lambda posterior, history, count=None: bank(history)
        self.neo_planner.generate_candidates = lambda state, history, **kwargs: bank(history)
        return super()._recommend(no_go_regions, unavailable_actions)


def configuration(seed: int, steps: int, count: int, variant: str) -> ArgusConfig:
    if variant not in VARIANTS:
        raise ValueError(f"Unknown variant {variant}")
    values = dict(seed=seed, research_seed=71, candidate_count=count, max_experiments=steps,
                  planner_horizon=1, profile="benchmark", expected_value_stop_threshold=-1.0)
    known_fields = {item.name for item in fields(ArgusConfig)}
    if "enable_nuisance_aware_design" in known_fields:
        values["enable_nuisance_aware_design"] = VARIANTS[variant]
    elif VARIANTS[variant]:
        raise RuntimeError("Nuisance-aware implementation is not installed")
    return ArgusConfig(**values)


def run_case(seed: int, context: str, variant: str, steps: int, count: int = 24) -> dict:
    config = configuration(seed, steps, count, variant)
    assumed = Material()
    factors = CONTEXTS[context]
    actual = replace(assumed, wave_velocity=assumed.wave_velocity * factors["velocity_multiplier"],
                     attenuation=assumed.attenuation * factors["attenuation_multiplier"],
                     noise_std=assumed.noise_std * factors["noise_multiplier"])
    # Independent truth stream: method and acquisition calls cannot change it.
    truth = AcousticSimulator(Panel(), assumed, seed=seed).random_defect("medium")
    banks = candidate_banks(seed, steps, count)
    start = perf_counter()
    engine = ControlledCandidateEngine(banks=banks, config=config, seed=seed, truth=truth,
                                       material=assumed, acquisition_material=actual)
    trace = []
    for step in range(steps):
        plan = engine.current_recommendation
        # Equal-length signals get identical random innovations even if previous
        # steps used calibration (which otherwise consumes a different RNG count).
        engine.acquisition_simulator.rng = acquisition_rng(seed, step)
        result = engine.run_recommended()
        status = engine.status()
        trace.append({"step": step + 1, "candidate_bank_sha256": bank_digest(banks[step]),
                      "action_type": result.action_type, "experiment": result.parameters.to_dict(),
                      "measurement_accepted": bool(result.quality.get("accepted", True)),
                      "error_mm": engine.localization_error() * 1000,
                      "entropy": float(status["normalized_entropy"]),
                      "information_score": float(plan.selected.expected_information_gain),
                      "nuisance_design": (plan.structured_explanation or {}).get("nuisance_design")})
    status = engine.status()
    error = engine.localization_error() * 1000
    false_confidence = status["decision_confidence"] >= 0.70 and error > 30
    return {"seed": seed, "context": context, "variant": variant, "completed": True,
            "localization_error_mm": error, "normalized_entropy": float(status["normalized_entropy"]),
            "decision_confidence": float(status["decision_confidence"]),
            "credible_region_area": float(status["credible_region_90"]["area_fraction"]),
            "measurements": len(trace), "calibrations": sum(t["action_type"] == "calibration" for t in trace),
            "rejected_measurements": sum(not t["measurement_accepted"] for t in trace),
            "success_20mm": bool(error <= 20), "failure_30mm": bool(error > 30),
            "false_confidence": bool(false_confidence),
            "abstained": status["ood_status"] in {"ABSTAIN", "OUT_OF_DISTRIBUTION"},
            "computation_seconds": perf_counter() - start, "sealed_truth": truth.to_dict(),
            "assumed_material": assumed.to_dict(), "acquisition_material": actual.to_dict(), "trace": trace}


def bootstrap_mean_ci(values: list[float], seed: int = 90_071, draws: int = 10_000) -> list[float]:
    values = np.asarray(values, dtype=float)
    if values.size == 0 or not np.isfinite(values).all():
        raise ValueError("Bootstrap requires nonempty finite observations")
    rng = np.random.default_rng(seed)
    means = rng.choice(values, size=(draws, len(values)), replace=True).mean(axis=1)
    return [float(x) for x in np.quantile(means, [0.025, 0.975])]


def summarize(rows: list[dict], contexts: tuple[str, ...], variants: tuple[str, ...]) -> tuple[dict, dict]:
    summary, paired = {}, {}
    for context in contexts:
        summary[context] = {}
        for variant in variants:
            attempted = [r for r in rows if r["context"] == context and r["variant"] == variant]
            subset = [r for r in attempted if r["completed"]]
            result = {"attempted": len(attempted), "completed": len(subset), "execution_failures": len(attempted) - len(subset)}
            if subset:
                errors = [r["localization_error_mm"] for r in subset]
                result.update({"localization_error_mm": {"mean": float(np.mean(errors)), "median": float(np.median(errors)),
                                "p90": float(np.quantile(errors, 0.90)), "mean_bootstrap_95ci": bootstrap_mean_ci(errors)},
                               **{key + "_rate": float(np.mean([r[key] for r in subset])) for key in
                                  ("success_20mm", "failure_30mm", "false_confidence", "abstained")},
                               **{"mean_" + key: float(np.mean([r[key] for r in subset])) for key in
                                  ("measurements", "calibrations", "normalized_entropy", "computation_seconds", "rejected_measurements")}})
            summary[context][variant] = result
        old = {r["seed"]: r for r in rows if r["context"] == context and r["variant"] == "legacy_proxy" and r["completed"]}
        new = {r["seed"]: r for r in rows if r["context"] == context and r["variant"] == "nuisance_aware" and r["completed"]}
        keys = sorted(set(old) & set(new))
        if keys:
            differences = [old[s]["localization_error_mm"] - new[s]["localization_error_mm"] for s in keys]
            paired[context] = {"complete_pairs": len(keys), "seeds": keys,
                               "error_advantage_sign": "positive means nuisance-aware has lower error",
                               "mean_error_advantage_mm": float(np.mean(differences)),
                               "bootstrap_95ci_mm": bootstrap_mean_ci(differences),
                               "win_rate": float(np.mean(np.asarray(differences) > 1e-9)),
                               "loss_rate": float(np.mean(np.asarray(differences) < -1e-9)),
                               "tie_rate": float(np.mean(np.abs(differences) <= 1e-9)),
                               "per_seed_error_advantage_mm": differences}
    return summary, paired


def validate_pairing(rows: list[dict]) -> None:
    """Reject silently mismatched data rather than publish a nominal paired CI."""
    seen = set()
    reference = {}
    for row in rows:
        key = (row["seed"], row["context"], row["variant"])
        if key in seen:
            raise ValueError(f"Duplicate run: {key}")
        seen.add(key)
        if not row["completed"]:
            continue
        pair_key = key[:2]
        signature = {k: row[k] for k in ("sealed_truth", "assumed_material", "acquisition_material", "measurements")}
        signature["candidate_banks"] = [step["candidate_bank_sha256"] for step in row["trace"]]
        if pair_key in reference and reference[pair_key] != signature:
            raise ValueError(f"Pairing mismatch for {pair_key}")
        reference[pair_key] = signature


def run_validation(seeds=VALIDATION_SEEDS, steps: int = 8, count: int = 24,
                   contexts=tuple(CONTEXTS), variants=tuple(VARIANTS),
                   progress: Callable[[dict], None] | None = None) -> dict:
    seeds, contexts, variants = tuple(seeds), tuple(contexts), tuple(variants)
    if not seeds or len(set(seeds)) != len(seeds):
        raise ValueError("Provide unique, nonempty seeds")
    if set(contexts) - CONTEXTS.keys() or set(variants) - VARIANTS.keys():
        raise ValueError("Unknown context or variant")
    # Fail early on missing implementation/configuration, not as a scientific result.
    configs = {v: configuration(seeds[0], steps, count, v).to_dict() for v in variants}
    rows = []
    for seed in seeds:
        for context in contexts:
            for variant in variants:
                try:
                    row = run_case(seed, context, variant, steps, count)
                except Exception as exc:
                    row = {"seed": seed, "context": context, "variant": variant, "completed": False,
                           "execution_error": f"{type(exc).__name__}: {exc}"}
                rows.append(row)
                if progress:
                    progress(row)
    validate_pairing(rows)
    summary, paired = summarize(rows, contexts, variants)
    return {"metadata": {"protocol_version": "argus-paired-candidates-v1", "evidence_source": "synthetic_only",
                         "seeds": list(seeds), "steps": steps, "candidate_count": count, "contexts": CONTEXTS,
                         "configurations": configs, "preset": "medium", "panel": Panel().to_dict(),
                         "python": platform.python_version(), "numpy": np.__version__, "scipy": scipy.__version__,
                         "stopping_policy": "fixed budget; no early confidence stop",
                         "candidate_policy": "8 fixed perimeter experiments + independent random safe bank each step; shared across variants",
                         "noise_policy": "SeedSequence([case_seed, zero_based_step, 202]); equal-length signals share innovations",
                         "calibration_policy": "unchanged production dual control and deterministic calibration options",
                         "bootstrap": "10000 paired-seed resamples, percentile interval, seed 90071",
                         "limitations": ["No field defect localization measurements", "Small synthetic scenario family",
                                         "Fixed budget does not establish measurement compression", "Gaussian approximation is not field calibrated",
                                         "Intervals condition on complete pairs; execution failures are reported separately"]},
            "summary": summary, "paired_comparisons": paired,
            "failures": [{k: r[k] for k in ("seed", "context", "variant", "completed", "localization_error_mm", "execution_error") if k in r}
                         for r in rows if not r["completed"] or r.get("failure_30mm")], "runs": rows}
