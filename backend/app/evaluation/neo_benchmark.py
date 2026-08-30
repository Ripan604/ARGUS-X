from __future__ import annotations

from dataclasses import replace
from statistics import mean
from time import perf_counter

import numpy as np
from scipy.stats import ttest_rel, wilcoxon

from backend.app.active_learning.planner import PlannedExperiment
from backend.app.core.config import ArgusConfig
from backend.app.evaluation.benchmark import uniform_grid_experiments
from backend.app.models.domain import Experiment
from backend.app.services.engine import ArgusEngine


STRATEGIES = (
    "random", "uniform_grid", "greedy_heuristic", "existing_argus",
    "information_gain", "bayes_risk", "dual_control", "receding_horizon", "full_argus_neo",
)


def _configuration(strategy: str, seed: int, maximum: int, overrides: dict | None = None) -> ArgusConfig:
    values = {
        "seed": seed, "candidate_count": 16, "max_experiments": maximum,
        "planner_objective": "MULTIOBJECTIVE", "planner_horizon": 1,
    }
    if strategy == "information_gain":
        values["planner_objective"] = "INFORMATION_GAIN"
    elif strategy == "bayes_risk":
        values["planner_objective"] = "BAYES_RISK"
    elif strategy == "receding_horizon":
        values["planner_horizon"] = 2
    elif strategy == "full_argus_neo":
        values.update({"planner_horizon": 2, "candidate_count": 20})
    values.update(overrides or {})
    return ArgusConfig(**values)


def _baseline_plan(engine: ArgusEngine, experiment: Experiment, strategy: str) -> PlannedExperiment:
    plan = engine.planner.recommend(engine.belief.posterior, engine.experiments)
    selected = next((item for item in engine.planner.score_candidates(engine.belief.posterior, [experiment], engine.experiments)), plan.selected)
    return replace(
        plan,
        selected=selected,
        explanation=f"{strategy} benchmark policy; evaluated under the same sealed scenario and stopping criterion.",
        strategy=strategy,
        action_type="diagnostic",
        structured_explanation={"action_type": "diagnostic", "primary_reason": f"Benchmark policy {strategy}"},
    )


def _select_experiment(engine: ArgusEngine, strategy: str, fixed: list[Experiment]) -> tuple[Experiment, PlannedExperiment | None]:
    if strategy == "random":
        experiment = engine.planner.random_experiment()
        return experiment, _baseline_plan(engine, experiment, strategy)
    if strategy == "uniform_grid":
        experiment = fixed[len(engine.experiments) % len(fixed)]
        return experiment, _baseline_plan(engine, experiment, strategy)
    if strategy == "existing_argus":
        plan = engine.planner.recommend(engine.belief.posterior, engine.experiments)
        return plan.selected.experiment, plan
    if strategy == "greedy_heuristic":
        candidates = engine.planner.generate_candidates(engine.belief.posterior, engine.experiments, 16)
        scores = engine.planner.score_candidates(engine.belief.posterior, candidates, engine.experiments)
        selected = max(scores, key=lambda item: item.uncertainty_coverage - 0.25 * item.experiment_cost)
        return selected.experiment, _baseline_plan(engine, selected.experiment, strategy)
    return engine.current_recommendation.selected.experiment, engine.current_recommendation


def _criterion(engine: ArgusEngine) -> bool:
    status = engine.status()
    return bool(
        status["ood_status"] not in {"OUT_OF_DISTRIBUTION", "ABSTAIN"}
        and status["confidence"] >= 0.72
        and status["credible_region_90"]["area_fraction"] <= 0.08
        and len(engine.experiments) >= 2
    )


def _run_policy(seed: int, strategy: str, maximum: int, overrides: dict | None = None) -> dict:
    started = perf_counter()
    engine = ArgusEngine(config=_configuration(strategy, seed, maximum, overrides), seed=seed, preset="medium")
    fixed = uniform_grid_experiments(maximum)
    movement = energy = acquisition_time = 0.0
    previous: Experiment | None = None
    action_trace = []
    for _ in range(maximum):
        if _criterion(engine):
            break
        experiment, plan = _select_experiment(engine, strategy, fixed)
        step_movement = 0.0
        if previous:
            step_movement += float(np.hypot(experiment.source_x - previous.source_x, experiment.source_y - previous.source_y))
            step_movement += float(np.hypot(experiment.receiver_x - previous.receiver_x, experiment.receiver_y - previous.receiver_y))
            movement += step_movement
        energy += experiment.amplitude**2 * experiment.duration_s
        acquisition_time += experiment.duration_s + 0.6 * step_movement
        result = engine.run_experiment(experiment, plan)
        action_trace.append({"action_type": result.action_type, "experiment": experiment.to_dict(), "entropy": engine.status()["normalized_entropy"]})
        previous = experiment
    status = engine.status()
    error_mm = engine.localization_error() * 1_000
    true_velocity = engine.material.wave_velocity
    estimated_velocity = engine.joint_state.nuisance.parameter("wave_velocity").mean
    return {
        "seed": seed,
        "strategy": strategy,
        "localization_error_mm": error_mm,
        "normalized_entropy": float(status["normalized_entropy"]),
        "credible_region_area": float(status["credible_region_90"]["area_fraction"]),
        "measurements": len(engine.experiments),
        "movement": movement,
        "energy_proxy": energy,
        "simulated_acquisition_time": acquisition_time,
        "calibration_error": abs(estimated_velocity - true_velocity) / true_velocity,
        "false_confidence": bool(status["decision_confidence"] >= 0.70 and error_mm > 30),
        "abstained": bool(status["ood_status"] in {"OUT_OF_DISTRIBUTION", "ABSTAIN"}),
        "success": bool(error_mm <= 20 and not status["ood_status"] == "ABSTAIN"),
        "criterion_reached": _criterion(engine),
        "computation_seconds": perf_counter() - started,
        "action_trace": action_trace,
        "failure_class": (
            "overconfident" if status["decision_confidence"] >= 0.70 and error_mm > 30
            else "localization_failed" if error_mm > 30
            else "excessive_measurements" if len(engine.experiments) >= maximum and not _criterion(engine)
            else "ood_abstention" if status["ood_status"] == "ABSTAIN"
            else None
        ),
    }


def _bootstrap(values: list[float], seed: int, draws: int = 1_000) -> list[float]:
    array = np.asarray(values, dtype=np.float64)
    if len(array) < 2:
        return [float(array[0]), float(array[0])]
    rng = np.random.default_rng(seed)
    samples = rng.choice(array, size=(draws, len(array)), replace=True).mean(axis=1)
    return [float(np.percentile(samples, 2.5)), float(np.percentile(samples, 97.5))]


def _summarize(rows: list[dict], strategy: str, seed: int) -> dict:
    subset = [row for row in rows if row["strategy"] == strategy]
    metrics = {}
    for field in (
        "localization_error_mm", "normalized_entropy", "credible_region_area", "measurements",
        "movement", "energy_proxy", "simulated_acquisition_time", "calibration_error", "computation_seconds",
    ):
        values = [float(row[field]) for row in subset]
        metrics[field] = {
            "mean": mean(values), "median": float(np.median(values)),
            "std": float(np.std(values, ddof=1)) if len(values) > 1 else 0.0,
            "bootstrap_95ci": _bootstrap(values, seed + len(field)),
        }
    metrics.update({
        "success_rate": mean(float(row["success"]) for row in subset),
        "false_confidence_rate": mean(float(row["false_confidence"]) for row in subset),
        "abstention_rate": mean(float(row["abstained"]) for row in subset),
        "criterion_rate": mean(float(row["criterion_reached"]) for row in subset),
        "sample_size": len(subset),
    })
    return metrics


def run_benchmark_matrix(cases: int = 2, max_experiments: int = 5, seed: int = 100, progress=None, cancelled=None) -> dict:
    rows = []
    total = cases * len(STRATEGIES)
    for case in range(cases):
        for strategy in STRATEGIES:
            if cancelled and cancelled():
                break
            rows.append(_run_policy(seed + case, strategy, max_experiments))
            if progress:
                progress(len(rows) / total)
    summaries = {strategy: _summarize(rows, strategy, seed) for strategy in STRATEGIES if any(row["strategy"] == strategy for row in rows)}
    fixed_mean = summaries.get("uniform_grid", {}).get("measurements", {}).get("mean", float(max_experiments))
    for strategy, summary in summaries.items():
        summary["inspection_compression"] = fixed_mean / max(summary["measurements"]["mean"], 1e-12)
    paired = {}
    full = {row["seed"]: row for row in rows if row["strategy"] == "full_argus_neo"}
    for baseline in ("random", "uniform_grid", "existing_argus"):
        prior = {row["seed"]: row for row in rows if row["strategy"] == baseline}
        keys = sorted(set(full) & set(prior))
        differences = [prior[key]["measurements"] - full[key]["measurements"] for key in keys]
        if len(keys) >= 2 and any(differences):
            try:
                wilcoxon_p = float(wilcoxon(differences).pvalue)
            except ValueError:
                wilcoxon_p = 1.0
            paired_t_p = float(ttest_rel([prior[key]["measurements"] for key in keys], [full[key]["measurements"] for key in keys]).pvalue)
        else:
            wilcoxon_p = paired_t_p = None
        paired[f"full_vs_{baseline}"] = {
            "sample_size": len(keys), "mean_measurement_advantage": float(np.mean(differences)) if differences else None,
            "bootstrap_95ci": _bootstrap(differences, seed + 901) if differences else None,
            "wilcoxon_p": wilcoxon_p, "paired_t_p": paired_t_p,
        }
    return {
        "metadata": {"cases": cases, "max_experiments": max_experiments, "seed": seed, "evidence_source": "simulated", "criterion": "confidence>=0.72, 90%-credible-area<=0.08, non-OOD"},
        "summary": summaries,
        "paired_comparisons": paired,
        "failures": [row for row in rows if row["failure_class"]],
        "runs": rows,
    }


ABLATIONS = {
    "full": {},
    "no_nuisance_inference": {"enable_nuisance_inference": False},
    "no_discrepancy_model": {"enable_discrepancy_model": False},
    "no_calibration_actions": {"enable_calibration_actions": False},
    "no_ood_layer": {"enable_ood_layer": False},
    "no_waveform_optimization": {"enable_waveform_optimization": False},
    "greedy_only": {"planner_horizon": 1},
    "no_multifidelity_controller": {"enable_multifidelity_controller": False},
}


def run_ablation_study(cases: int = 2, seed: int = 300, progress=None, cancelled=None) -> dict:
    rows = []
    total = cases * len(ABLATIONS)
    for case in range(cases):
        for name, overrides in ABLATIONS.items():
            if cancelled and cancelled():
                break
            effective = {"planner_horizon": 2, **overrides}
            row = _run_policy(seed + case, "full_argus_neo", 5, effective)
            row["ablation"] = name
            rows.append(row)
            if progress:
                progress(len(rows) / total)
    summary = {}
    for name in ABLATIONS:
        subset = [row for row in rows if row["ablation"] == name]
        if not subset:
            continue
        summary[name] = {
            "mean_error_mm": mean(row["localization_error_mm"] for row in subset),
            "mean_measurements": mean(row["measurements"] for row in subset),
            "mean_entropy": mean(row["normalized_entropy"] for row in subset),
            "success_rate": mean(float(row["success"]) for row in subset),
            "false_confidence_rate": mean(float(row["false_confidence"]) for row in subset),
            "sample_size": len(subset),
        }
    return {"metadata": {"cases": cases, "seed": seed, "evidence_source": "simulated"}, "summary": summary, "runs": rows}
