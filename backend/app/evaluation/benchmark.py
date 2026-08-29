from __future__ import annotations

import csv
import json
from pathlib import Path
from statistics import mean

import numpy as np

from backend.app.core.config import ArgusConfig
from backend.app.models.domain import Experiment
from backend.app.services.engine import ArgusEngine


def uniform_grid_experiments(count: int) -> list[Experiment]:
    points = [(0.08, 0.08), (0.50, 0.08), (0.92, 0.08), (0.92, 0.50), (0.92, 0.92), (0.50, 0.92), (0.08, 0.92), (0.08, 0.50)]
    results = []
    for index in range(count):
        source = points[index % len(points)]
        receiver = points[(index + 3) % len(points)]
        band = [(1_200.0, 3_000.0), (2_200.0, 4_400.0), (3_400.0, 6_200.0)][index % 3]
        results.append(Experiment(*source, *receiver, *band, 0.48, 0.12, "chirp"))
    return results


def _run_strategy(seed: int, preset: str, strategy: str, max_experiments: int) -> dict:
    config = ArgusConfig(seed=seed, max_experiments=max_experiments)
    engine = ArgusEngine(config=config, seed=seed, preset=preset)
    fixed = uniform_grid_experiments(max_experiments)
    total_cost = 0.0
    entropy_trajectory = [engine.status()["normalized_entropy"]]
    error_trajectory_mm = [engine.localization_error() * 1_000]
    while not engine.status()["should_stop"]:
        if strategy == "argus":
            recommendation = engine.current_recommendation
            experiment = recommendation.selected.experiment
        elif strategy == "random":
            experiment = engine.planner.random_experiment()
        elif strategy == "uniform_grid":
            experiment = fixed[len(engine.experiments)]
        else:
            raise ValueError(f"Unknown strategy {strategy}")
        total_cost += engine.planner._experiment_cost(experiment, engine.experiments)
        engine.run_experiment(experiment)
        entropy_trajectory.append(engine.status()["normalized_entropy"])
        error_trajectory_mm.append(engine.localization_error() * 1_000)
    status = engine.status()
    return {
        "seed": seed,
        "preset": preset,
        "strategy": strategy,
        "localization_error_mm": engine.localization_error() * 1_000,
        "experiments": len(engine.experiments),
        "final_entropy": status["normalized_entropy"],
        "confidence": status["confidence"],
        "measurement_cost": total_cost,
        "entropy_reduction": 1.0 - status["normalized_entropy"],
        "entropy_auc": float(np.mean(entropy_trajectory)),
        "success_10mm": engine.localization_error() <= 0.010,
        "success_15mm": engine.localization_error() <= 0.015,
        "success_20mm": engine.localization_error() <= 0.020,
        "success_30mm": engine.localization_error() <= 0.030,
        "stop_reason": status["stop_reason"],
        "entropy_trajectory": entropy_trajectory,
        "error_trajectory_mm": error_trajectory_mm,
    }


def _bootstrap_interval(values: list[float], rng: np.random.Generator, draws: int = 2_000) -> list[float]:
    array = np.asarray(values, dtype=np.float64)
    if array.size == 1:
        return [float(array[0]), float(array[0])]
    samples = rng.choice(array, size=(draws, array.size), replace=True).mean(axis=1)
    return [float(np.percentile(samples, 2.5)), float(np.percentile(samples, 97.5))]


def run_benchmark(
    cases: int = 12,
    preset: str = "medium",
    max_experiments: int = 10,
    seed: int = 100,
    output_dir: str | Path | None = None,
) -> dict:
    rows = []
    for case in range(cases):
        for strategy in ("random", "uniform_grid", "argus"):
            rows.append(_run_strategy(seed + case, preset, strategy, max_experiments))
    summary = {}
    for strategy in ("random", "uniform_grid", "argus"):
        subset = [row for row in rows if row["strategy"] == strategy]
        summary[strategy] = {
            "mean_localization_error_mm": mean(row["localization_error_mm"] for row in subset),
            "median_localization_error_mm": float(np.median([row["localization_error_mm"] for row in subset])),
            "mean_experiments": mean(row["experiments"] for row in subset),
            "mean_final_entropy": mean(row["final_entropy"] for row in subset),
            "mean_entropy_reduction": mean(row["entropy_reduction"] for row in subset),
            "mean_entropy_auc": mean(row["entropy_auc"] for row in subset),
            "mean_measurement_cost": mean(row["measurement_cost"] for row in subset),
            "success_rate_10mm": mean(float(row["success_10mm"]) for row in subset),
            "success_rate_15mm": mean(float(row["success_15mm"]) for row in subset),
            "success_rate_20mm": mean(float(row["success_20mm"]) for row in subset),
            "success_rate_30mm": mean(float(row["success_30mm"]) for row in subset),
        }
    trajectories = {}
    for strategy in ("random", "uniform_grid", "argus"):
        subset = [row for row in rows if row["strategy"] == strategy]
        entropy_curve, error_curve = [], []
        for step in range(max_experiments + 1):
            entropy_curve.append(mean(row["entropy_trajectory"][min(step, len(row["entropy_trajectory"]) - 1)] for row in subset))
            error_curve.append(mean(row["error_trajectory_mm"][min(step, len(row["error_trajectory_mm"]) - 1)] for row in subset))
        trajectories[strategy] = {"mean_entropy": entropy_curve, "mean_localization_error_mm": error_curve}
    bootstrap_rng = np.random.default_rng(seed + 900_001)
    paired_comparisons = {}
    argus_by_seed = {row["seed"]: row for row in rows if row["strategy"] == "argus"}
    for baseline in ("random", "uniform_grid"):
        baseline_by_seed = {row["seed"]: row for row in rows if row["strategy"] == baseline}
        error_advantage = [baseline_by_seed[key]["localization_error_mm"] - argus_by_seed[key]["localization_error_mm"] for key in argus_by_seed]
        entropy_advantage = [baseline_by_seed[key]["final_entropy"] - argus_by_seed[key]["final_entropy"] for key in argus_by_seed]
        paired_comparisons[f"argus_vs_{baseline}"] = {
            "mean_error_advantage_mm": mean(error_advantage),
            "error_advantage_95ci_mm": _bootstrap_interval(error_advantage, bootstrap_rng),
            "error_win_rate": mean(float(value > 0) for value in error_advantage),
            "mean_entropy_advantage": mean(entropy_advantage),
            "entropy_advantage_95ci": _bootstrap_interval(entropy_advantage, bootstrap_rng),
            "entropy_win_rate": mean(float(value > 0) for value in entropy_advantage),
        }
    result = {
        "metadata": {"cases": cases, "preset": preset, "max_experiments": max_experiments, "seed": seed},
        "summary": summary,
        "trajectories": trajectories,
        "paired_comparisons": paired_comparisons,
        "runs": rows,
    }
    if output_dir is not None:
        destination = Path(output_dir)
        destination.mkdir(parents=True, exist_ok=True)
        (destination / "benchmark.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        with (destination / "benchmark.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    return result
