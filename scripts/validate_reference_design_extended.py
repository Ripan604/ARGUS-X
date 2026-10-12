"""Prospective, paired scalar-reference validation with strong design baselines.

This evaluates propagation prediction and declared cost, never physical defect
localization. The protocol is fixed in EXTENDED_REFERENCE_VALIDATION_PROTOCOL.md.
Importing this module neither runs a study nor writes an evidence artifact.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import sys
from time import perf_counter

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.active_learning.reference_design import reference_observation_std, select_task_reference
from backend.app.control.dual_control import AdaptiveDualControlManager
from backend.app.decision.loss import DecisionLossModel
from backend.app.inference.nuisance_posterior import NuisancePosterior
from backend.app.models.domain import Experiment, Material, Panel, physical_distance

POLICIES = ("cyclic", "random", "scaled_a_optimal", "scaled_d_optimal", "task_conditioned")
NOISE_REGIMES = {"nominal_prior_noise": 1.0, "double_acquisition_noise": 2.0}
TARGETS = (
    Experiment(.05, .10, .25, .20),
    Experiment(.05, .05, .95, .95),
    Experiment(.10, .85, .85, .15),
    Experiment(.10, .50, .45, .50),
)
SAMPLE_RATE = 16_000
ASSUMED_QUALITY = .75
REFERENCE_STEPS = 3
COST_M2_PER_UNIT = .0001
FIRST_SEED = 970001
SEED_STRIDE = 31


def source_fingerprints() -> dict[str, str]:
    paths = [Path(__file__), ROOT / "backend/tests/test_extended_reference_validation.py",
             ROOT / "docs/EXTENDED_REFERENCE_VALIDATION_PROTOCOL.md",
             *sorted((ROOT / "backend/app").rglob("*.py"))]
    return {p.relative_to(ROOT).as_posix(): sha256(p.read_bytes()).hexdigest() for p in paths}


def canonical_hash(value: dict) -> str:
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def target_paths(posterior: np.ndarray, panel: Panel, target: Experiment) -> np.ndarray:
    rows, columns = np.indices(posterior.shape)
    x, y = (columns + .5) / posterior.shape[1], (rows + .5) / posterior.shape[0]
    return (physical_distance(target.source_x, target.source_y, x, y, panel)
            + physical_distance(x, y, target.receiver_x, target.receiver_y, panel))


def scaled_covariance(covariance: np.ndarray, velocity_scale: float, delay_scale: float) -> np.ndarray:
    """Dimensionless covariance; no raw mixed-unit trace or determinant."""
    if not np.isfinite([velocity_scale, delay_scale]).all() or min(velocity_scale, delay_scale) <= 0:
        raise ValueError("Covariance scales must be positive and finite")
    scales = np.asarray([velocity_scale, delay_scale])
    covariance = np.asarray(covariance, dtype=float)
    if covariance.shape != (2, 2) or not np.isfinite(covariance).all():
        raise ValueError("Propagation covariance must be finite and 2 by 2")
    result = covariance / scales[:, None] / scales[None, :]
    if np.linalg.eigvalsh(result).min() <= 0:
        raise ValueError("Scaled propagation covariance must be positive definite")
    return result


def acquisition_cost(candidate: Experiment, previous: Experiment) -> float:
    movement = float(np.hypot(candidate.source_x - previous.source_x, candidate.source_y - previous.source_y)
                     + np.hypot(candidate.receiver_x - previous.receiver_x, candidate.receiver_y - previous.receiver_y))
    return DecisionLossModel().experiment_cost(movement, candidate.amplitude, candidate.duration_s)


def select_scaled_optimal_reference(nuisance: NuisancePosterior, panel: Panel,
                                    candidates: tuple[Experiment, ...], previous: Experiment,
                                    velocity_ref: float, policy: str) -> tuple[Experiment, dict]:
    """Posterior-independent A/D designs, with declared equal cost conversion.

    A minimizes D^2 trace(C_scaled); D minimizes D^2 sqrt(det(C_scaled)),
    where D is the panel diagonal. With zero costs these are standard A/D
    criteria. Cost-bearing proxies are declared design objectives, not errors.
    """
    if policy not in {"scaled_a_optimal", "scaled_d_optimal"}:
        raise ValueError("Unknown scaled optimal design policy")
    diagonal = float(np.hypot(panel.width_m, panel.height_m))
    std = reference_observation_std(nuisance, panel, SAMPLE_RATE)
    alternatives = []
    for index, candidate in enumerate(candidates):
        distance = float(physical_distance(candidate.source_x, candidate.source_y,
                                           candidate.receiver_x, candidate.receiver_y, panel))
        _, conditioned = nuisance.conditioned_propagation(distance, std, ASSUMED_QUALITY)
        scaled = scaled_covariance(conditioned, velocity_ref, diagonal / velocity_ref)
        proxy = (float(np.trace(scaled)) if policy == "scaled_a_optimal"
                 else float(np.exp(.5 * np.linalg.slogdet(scaled)[1]))) * diagonal**2
        cost_m2 = COST_M2_PER_UNIT * acquisition_cost(candidate, previous)
        alternatives.append({"index": index, "design_proxy_m2": proxy,
                             "acquisition_cost_m2": cost_m2, "objective_m2": proxy + cost_m2})
    selected = min(alternatives, key=lambda row: (row["objective_m2"], row["index"]))
    return candidates[selected["index"]], {"method": policy, "selected": selected,
                                            "alternatives": alternatives,
                                            "velocity_scale": velocity_ref, "delay_scale": diagonal / velocity_ref}


@dataclass(frozen=True)
class SealedCase:
    seed: int
    geometry_index: int
    panel: Panel
    target: Experiment
    posterior: np.ndarray
    prior_json: str
    references: tuple[Experiment, ...]
    starting_pose: Experiment
    true_velocity: float
    true_timing: float
    acquisition_base_std_s: float
    innovations: tuple[float, ...]
    random_indices: tuple[int, ...]
    velocity_ref: float
    seal_hash: str

    def prior(self) -> NuisancePosterior:
        return NuisancePosterior.from_dict(json.loads(self.prior_json))


def seal_case(seed: int, geometry_index: int) -> SealedCase:
    if not 0 <= geometry_index < len(TARGETS):
        raise ValueError("Geometry index is outside the prospective target bank")
    rng = np.random.default_rng(np.random.SeedSequence([seed, geometry_index, 1183]))
    panel = Panel()
    velocity_ref = float(rng.uniform(160, 210))
    timing_mean = float(rng.uniform(.0006, .0010))
    prior = NuisancePosterior.from_material(Material(wave_velocity=velocity_ref, system_delay_s=timing_mean))
    prior.parameter("wave_velocity").std = float(rng.uniform(22, 38))
    prior.parameter("timing_offset").std = float(rng.uniform(.00018, .00038))
    prior.velocity_timing_correlation = (-.6, 0., .6)[(seed + geometry_index) % 3]
    truth_draw = rng.multivariate_normal([velocity_ref, timing_mean], prior.propagation_covariance())
    true_velocity = float(np.clip(truth_draw[0], 100, 330))
    true_timing = float(np.clip(truth_draw[1], .00005, .0025))
    y, x = np.indices((20, 20)); x, y = (x + .5) / 20, (y + .5) / 20
    centers = rng.uniform(.1, .9, size=(3, 2))
    widths = ((.08, .18), (.14, .10), (.22, .07), (.10, .23))[geometry_index]
    mixture_weights = rng.dirichlet([2, 1, 1])
    posterior = np.full((20, 20), .01)
    for weight, center in zip(mixture_weights, centers):
        posterior += weight * np.exp(-.5 * (((x-center[0]) / widths[0])**2 + ((y-center[1]) / widths[1])**2))
    posterior /= posterior.sum()
    posterior.setflags(write=False)
    references = tuple(AdaptiveDualControlManager.calibration_experiment("direct_path", i) for i in range(3))
    starting_pose = Experiment(float(rng.uniform(.05, .3)), float(rng.uniform(.05, .95)),
                               float(rng.uniform(.7, .95)), float(rng.uniform(.05, .95)))
    # Sealed acquisition uncertainty depends on true physics, not a policy's
    # changing estimator. It is intentionally not supplied to policy selection.
    acquisition_nuisance = NuisancePosterior.from_material(Material(wave_velocity=true_velocity))
    acquisition_base_std = reference_observation_std(acquisition_nuisance, panel, SAMPLE_RATE) / np.sqrt(ASSUMED_QUALITY)
    innovations = tuple(map(float, rng.normal(size=REFERENCE_STEPS)))
    random_rng = np.random.default_rng(np.random.SeedSequence([seed, geometry_index, 7729]))
    random_indices = tuple(map(int, random_rng.integers(0, len(references), size=REFERENCE_STEPS)))
    prior_json = json.dumps(prior.to_dict(), sort_keys=True, allow_nan=False)
    seal = {"seed": seed, "geometry_index": geometry_index, "panel": panel.to_dict(),
            "target": TARGETS[geometry_index].to_dict(), "posterior": posterior.tolist(), "prior": json.loads(prior_json),
            "references": [e.to_dict() for e in references], "starting_pose": starting_pose.to_dict(),
            "true_velocity": true_velocity, "true_timing": true_timing,
            "acquisition_base_std_s": acquisition_base_std, "innovations": innovations,
            "random_indices": random_indices, "velocity_ref": velocity_ref,
            "cost_m2_per_unit": COST_M2_PER_UNIT, "reference_steps": REFERENCE_STEPS}
    return SealedCase(seed, geometry_index, panel, TARGETS[geometry_index], posterior, prior_json,
                      references, starting_pose, true_velocity, true_timing, acquisition_base_std,
                      innovations, random_indices, velocity_ref, canonical_hash(seal))


def run_policy(case: SealedCase, noise_regime: str, policy: str) -> dict:
    if policy not in POLICIES or noise_regime not in NOISE_REGIMES:
        raise ValueError("Policy or acquisition regime is not in the registered protocol")
    nuisance = case.prior()
    previous = case.starting_pose
    trace = []
    cost_total = 0.0
    failures = 0
    started = perf_counter()
    acquisition_std = case.acquisition_base_std_s * NOISE_REGIMES[noise_regime]
    for step in range(REFERENCE_STEPS):
        selection_started = perf_counter()
        row = {"step": step + 1, "shared_innovation": case.innovations[step],
               "acquisition_noise_std_s": acquisition_std, "seal_sha256": case.seal_hash}
        try:
            if policy == "task_conditioned":
                selection = select_task_reference(case.posterior, nuisance, case.panel, case.target,
                    list(case.references), sample_rate=SAMPLE_RATE,
                    cost_function=lambda e: acquisition_cost(e, previous), cost_m2_per_unit=COST_M2_PER_UNIT,
                    assumed_quality=ASSUMED_QUALITY)
                candidate, design = selection.experiment, selection.diagnostics
            elif policy in {"scaled_a_optimal", "scaled_d_optimal"}:
                candidate, design = select_scaled_optimal_reference(nuisance, case.panel, case.references,
                                                                    previous, case.velocity_ref, policy)
            else:
                index = step % len(case.references) if policy == "cyclic" else case.random_indices[step]
                candidate, design = case.references[index], {"method": policy, "index": index}
            row["selection_latency_ms"] = (perf_counter() - selection_started) * 1000
            row["design"] = design
        except (ValueError, RuntimeError, FloatingPointError) as exc:
            failures += 1
            cost_m2 = COST_M2_PER_UNIT * DecisionLossModel().config.additional_experiment
            cost_total += cost_m2
            row.update({"accepted": False, "failure_phase": "selection", "error": str(exc),
                        "selection_latency_ms": (perf_counter()-selection_started)*1000,
                        "charged_acquisition_cost_m2": cost_m2})
            trace.append(row)
            continue
        distance = float(physical_distance(candidate.source_x, candidate.source_y,
                                           candidate.receiver_x, candidate.receiver_y, case.panel))
        observed = case.true_timing + distance / case.true_velocity + case.innovations[step] * acquisition_std
        assumed_std = reference_observation_std(nuisance, case.panel, SAMPLE_RATE)
        cost_m2 = COST_M2_PER_UNIT * acquisition_cost(candidate, previous)
        cost_total += cost_m2
        before = nuisance.to_dict()
        row.update({"experiment": candidate.to_dict(), "reference_index": case.references.index(candidate),
                    "path_m": distance, "observed_delay_s": observed, "shared_noise_s": case.innovations[step]*acquisition_std,
                    "assumed_reference_std_s": assumed_std,
                    "actual_to_assumed_noise_ratio": acquisition_std / (assumed_std / np.sqrt(ASSUMED_QUALITY)),
                    "charged_acquisition_cost_m2": cost_m2})
        update_started = perf_counter()
        try:
            row["update"] = nuisance.update_direct_path(distance, observed, assumed_std, ASSUMED_QUALITY)
            row["accepted"] = True
        except (ValueError, RuntimeError, FloatingPointError) as exc:
            failures += 1
            row.update({"accepted": False, "failure_phase": "calibration", "error": str(exc)})
            if nuisance.to_dict() != before:
                raise RuntimeError("A rejected calibration changed state; evidence cannot be trusted") from exc
        row["update_latency_ms"] = (perf_counter()-update_started)*1000
        row["propagation_covariance_after"] = nuisance.propagation_covariance().tolist()
        trace.append(row)
        previous = candidate
    paths = target_paths(case.posterior, case.panel, case.target)
    prediction = nuisance.parameter("timing_offset").mean + paths / nuisance.parameter("wave_velocity").mean
    truth = case.true_timing + paths / case.true_velocity
    squared_error = float(np.sum(case.posterior * (prediction-truth)**2))
    variances = nuisance.arrival_variance(paths)
    modeled = float(np.sum(case.posterior * variances))
    coverage = float(np.sum(case.posterior * (np.abs(prediction-truth) <= 1.96*np.sqrt(variances))))
    path_error = case.velocity_ref**2 * squared_error
    return {"seed": case.seed, "geometry_index": case.geometry_index, "noise_regime": noise_regime,
            "policy": policy, "seal_sha256": case.seal_hash, "completed": failures == 0,
            "failures": failures, "attempted_opportunities": REFERENCE_STEPS,
            "target_arrival_rmse_us": np.sqrt(squared_error)*1e6,
            "realized_path_equivalent_mse_m2": path_error, "actual_acquisition_cost_m2": cost_total,
            "realized_path_prediction_plus_cost_m2": path_error + cost_total,
            "modeled_target_variance_s2": modeled, "posterior_weighted_95_interval_coverage": coverage,
            "evaluation_velocity_ref_m_s": case.velocity_ref,
            "velocity_absolute_error_m_s": abs(nuisance.parameter("wave_velocity").mean-case.true_velocity),
            "timing_absolute_error_us": abs(nuisance.parameter("timing_offset").mean-case.true_timing)*1e6,
            "case_elapsed_ms": (perf_counter()-started)*1000, "trace": trace}


def paired_summary(runs: list[dict], seed_list: tuple[int, ...], bootstrap_samples: int) -> list[dict]:
    """Seed-cluster bootstrap preserves geometry/regime dependence and failures."""
    lookup = {(r["seed"], r["geometry_index"], r["noise_regime"], r["policy"]): r for r in runs}
    geometries = tuple(sorted({r["geometry_index"] for r in runs}))
    groups = [("all_regimes", tuple(NOISE_REGIMES), geometries)]
    groups += [(k, (k,), geometries) for k in NOISE_REGIMES]
    groups += [(f"geometry_{g}_{k}", (k,), (g,)) for g in geometries for k in NOISE_REGIMES]
    results = []
    for group, regimes, selected_geometries in groups:
        for baseline in POLICIES[:-1]:
            for metric in ("target_arrival_rmse_us", "realized_path_prediction_plus_cost_m2"):
                differences = []
                for seed in seed_list:
                    values = [lookup[(seed, geometry, regime, baseline)][metric]
                              - lookup[(seed, geometry, regime, "task_conditioned")][metric]
                              for geometry in selected_geometries for regime in regimes
                              if (seed, geometry, regime, baseline) in lookup]
                    differences.append(float(np.mean(values)))
                values = np.asarray(differences)
                rng = np.random.default_rng(118701)
                bootstrap = values[rng.integers(len(values), size=(bootstrap_samples, len(values)))].mean(axis=1)
                results.append({"regime_group": group, "baseline": baseline, "metric": metric,
                                "mean_advantage_for_task_conditioned": float(values.mean()),
                                "seed_cluster_bootstrap_95ci": np.percentile(bootstrap, [2.5, 97.5]).tolist(),
                                "seed_cluster_differences": [{"seed": seed, "mean_difference": difference}
                                                             for seed, difference in zip(seed_list, differences)],
                                "seed_clusters": len(values), "failure_policy": "all_attempted_cases_retained",
                                "interpretation": "positive_favors_task_conditioned; exploratory_intervals_no_multiplicity_correction"})
    return results


def run_study(*, seed_count: int = 48, geometry_count: int = 4, bootstrap_samples: int = 4000) -> dict:
    if not 1 <= seed_count <= 512 or not 1 <= geometry_count <= 4 or not 100 <= bootstrap_samples <= 10000:
        raise ValueError("Study counts exceed bounded validation limits")
    before = source_fingerprints()
    seed_list = tuple(FIRST_SEED + SEED_STRIDE*i for i in range(seed_count))
    # Every acquisition realization and opportunity is sealed before a policy runs.
    cases = [seal_case(seed, geometry) for seed in seed_list for geometry in range(geometry_count)]
    started = perf_counter()
    runs = [run_policy(case, regime, policy) for case in cases for regime in NOISE_REGIMES for policy in POLICIES]
    after = source_fingerprints()
    summaries = {}
    for regime in NOISE_REGIMES:
        summaries[regime] = {}
        for policy in POLICIES:
            subset = [r for r in runs if r["noise_regime"] == regime and r["policy"] == policy]
            entry = {"attempted_runs": len(subset), "completed_runs": sum(r["completed"] for r in subset),
                     "failed_updates_or_selections": sum(r["failures"] for r in subset)}
            for metric in ("target_arrival_rmse_us", "realized_path_prediction_plus_cost_m2",
                           "actual_acquisition_cost_m2", "velocity_absolute_error_m_s", "timing_absolute_error_us",
                           "posterior_weighted_95_interval_coverage", "case_elapsed_ms"):
                entry["mean_"+metric] = float(np.mean([r[metric] for r in subset]))
            latencies = [step["selection_latency_ms"] for r in subset for step in r["trace"]]
            failed_latencies = [step["selection_latency_ms"] + step.get("update_latency_ms", 0)
                                for r in subset for step in r["trace"] if not step["accepted"]]
            entry["selection_latency_p95_ms"] = float(np.percentile(latencies, 95))
            entry["mean_failed_opportunity_latency_ms"] = float(np.mean(failed_latencies)) if failed_latencies else None
            summaries[regime][policy] = entry
    return {"metadata": {"evidence_source": "synthetic_scalar_reference_only", "protocol_version": 1,
                "seed_list": list(seed_list), "geometry_count": geometry_count, "policies": list(POLICIES),
                "noise_regimes": NOISE_REGIMES, "reference_steps": REFERENCE_STEPS,
                "sample_rate": SAMPLE_RATE, "assumed_quality": ASSUMED_QUALITY,
                "cost_m2_per_unit": COST_M2_PER_UNIT, "source_sha256_before": before,
                "source_sha256_after": after, "source_changed_during_run": before != after,
                "run_elapsed_s": perf_counter()-started, "bootstrap_samples": bootstrap_samples,
                "selection_scope": "sealed_truth_never_supplied_to_any_design_policy",
                "primary_scope": "target_arrival_prediction_and_declared_cost_not_defect_location",
                "nominal_noise_definition": "true_velocity_fixed_acquisition; estimator_noise_contract_remains_approximate",
                "cost_handling": "all_policies_charged_same_formula;cyclic_and_random_do_not_optimize_cost",
                "limitations": ["first_order_gaussian_inference_for_nonlinear_delay", "three_fixed_reference_paths",
                    "four_fixed_diagnostic_targets", "synthetic_prior_draws", "no_measured_waveforms_or_defects",
                    "A_D_cost_proxies_are_declared_dimensionless_covariance_design_choices",
                    "runtime_depends_on_host", "no_policy_hyperparameter_tuning_or_seed_removal"]},
            "sealed_cases": [{"seed": c.seed, "geometry_index": c.geometry_index, "seal_sha256": c.seal_hash,
                "true_velocity": c.true_velocity, "true_timing": c.true_timing, "prior": json.loads(c.prior_json),
                "posterior": c.posterior.tolist(), "target": c.target.to_dict(),
                "references": [e.to_dict() for e in c.references], "starting_pose": c.starting_pose.to_dict(),
                "innovations": c.innovations, "random_indices": c.random_indices,
                "acquisition_base_std_s": c.acquisition_base_std_s, "velocity_ref": c.velocity_ref,
                "panel": c.panel.to_dict(), "cost_m2_per_unit": COST_M2_PER_UNIT,
                "reference_steps": REFERENCE_STEPS} for c in cases],
            "summary": summaries, "paired": paired_summary(runs, seed_list, bootstrap_samples), "runs": runs}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=int, default=48)
    parser.add_argument("--output", type=Path, default=ROOT / "research_results/extended_reference_design_2026_10_07.json")
    args = parser.parse_args()
    report = run_study(seed_count=args.seeds)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False)+"\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "runs": len(report["runs"]),
                      "summary": report["summary"], "paired": report["paired"],
                      "source_changed_during_run": report["metadata"]["source_changed_during_run"]}, indent=2))


if __name__ == "__main__":
    main()
