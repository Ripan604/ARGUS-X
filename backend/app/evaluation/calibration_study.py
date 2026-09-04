from __future__ import annotations

from collections import Counter
import csv
from pathlib import Path

import numpy as np

from backend.app.core.config import ArgusConfig
from backend.app.services.engine import ArgusEngine


TRIALS = {"quick": 4, "standard": 16, "research": 64}


def _truth_rank_and_coverage(engine: ArgusEngine) -> tuple[float, dict[float, bool]]:
    posterior = engine.belief.posterior
    column = min(engine.config.grid_size - 1, int(engine.truth.center_x * engine.config.grid_size))
    row = min(engine.config.grid_size - 1, int(engine.truth.center_y * engine.config.grid_size))
    flat_index = row * engine.config.grid_size + column
    order = np.argsort(posterior.ravel())[::-1]
    rank = int(np.flatnonzero(order == flat_index)[0]) + 1
    normalized_rank = rank / posterior.size
    cumulative = np.cumsum(posterior.ravel()[order])
    truth_position = int(np.flatnonzero(order == flat_index)[0])
    cumulative_before_truth = float(cumulative[truth_position] - posterior.ravel()[flat_index])
    # The HPD set includes the cell that first crosses the requested mass.
    coverages = {mass: bool(cumulative_before_truth < mass) for mass in (0.50, 0.80, 0.90, 0.95)}
    return normalized_rank, coverages


def run_calibration_study(mode: str = "quick", seed: int = 200, progress=None, cancelled=None) -> dict:
    if mode not in TRIALS:
        raise ValueError(f"Unknown calibration mode: {mode}")
    trials = TRIALS[mode]
    rows = []
    for index in range(trials):
        if cancelled and cancelled():
            break
        trial_seed = seed + index
        engine = ArgusEngine(
            config=ArgusConfig(seed=trial_seed, candidate_count=16, max_experiments=6),
            seed=trial_seed,
            preset="medium",
        )
        for _ in range(engine.config.max_experiments):
            if engine.status()["should_stop"] and not engine.automatic_recovery_available():
                break
            engine.run_recommended()
        rank, coverage = _truth_rank_and_coverage(engine)
        error_mm = engine.localization_error() * 1_000
        status = engine.status()
        rows.append({
            "seed": trial_seed,
            "posterior_rank_fraction": rank,
            "coverage": {str(int(mass * 100)): covered for mass, covered in coverage.items()},
            "reported_confidence": float(status["decision_confidence"]),
            "success_20mm": bool(error_mm <= 20),
            "localization_error_mm": error_mm,
            "experiments": len(engine.experiments),
            "ood_status": status["ood_status"],
        })
        if progress:
            progress((index + 1) / trials)
    confidence_bins = np.linspace(0, 1, 6)
    reliability = []
    ece = 0.0
    for low, high in zip(confidence_bins[:-1], confidence_bins[1:]):
        subset = [row for row in rows if low <= row["reported_confidence"] < high or (high == 1 and row["reported_confidence"] == 1)]
        if not subset:
            reliability.append({"confidence_low": float(low), "confidence_high": float(high), "count": 0, "mean_confidence": None, "empirical_success": None})
            continue
        mean_confidence = float(np.mean([row["reported_confidence"] for row in subset]))
        empirical = float(np.mean([row["success_20mm"] for row in subset]))
        ece += len(subset) / max(len(rows), 1) * abs(mean_confidence - empirical)
        reliability.append({"confidence_low": float(low), "confidence_high": float(high), "count": len(subset), "mean_confidence": mean_confidence, "empirical_success": empirical})
    histogram_edges = np.linspace(0, 1, 11)
    histogram, _ = np.histogram([row["posterior_rank_fraction"] for row in rows], bins=histogram_edges)
    coverage_table = {
        level: float(np.mean([row["coverage"][level] for row in rows])) if rows else 0.0
        for level in ("50", "80", "90", "95")
    }
    return {
        "metadata": {"mode": mode, "requested_trials": trials, "completed_trials": len(rows), "seed": seed, "evidence_source": "simulated"},
        "coverage": coverage_table,
        "expected_calibration_error": float(ece),
        "posterior_rank_histogram": {"edges": histogram_edges.tolist(), "counts": histogram.tolist()},
        "reliability_plot": reliability,
        "ood_status_counts": dict(Counter(row["ood_status"] for row in rows)),
        "trials": rows,
    }


def write_calibration_artifacts(result: dict, directory: str | Path) -> dict:
    """Write dependency-free SVG/CSV artifacts from an observed study result."""

    root = Path(directory); root.mkdir(parents=True, exist_ok=True)
    table = root / "calibration_table.csv"
    with table.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["coverage_level", "empirical_coverage", "completed_trials"])
        writer.writeheader()
        for level, value in result["coverage"].items():
            writer.writerow({"coverage_level": level, "empirical_coverage": value, "completed_trials": result["metadata"]["completed_trials"]})

    points = [item for item in result["reliability_plot"] if item["mean_confidence"] is not None]
    coordinates = " ".join(f"{45 + float(item['mean_confidence']) * 300:.1f},{340 - float(item['empirical_success']) * 300:.1f}" for item in points)
    reliability = root / "reliability.svg"
    reliability.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="400" height="400" viewBox="0 0 400 400">'
        '<rect width="400" height="400" fill="#07100d"/><path d="M45 340L345 40" stroke="#52665e" stroke-dasharray="5 5"/>'
        '<path d="M45 40V340H345" fill="none" stroke="#9badA5"/><text x="160" y="385" fill="#9badA5" font-size="12">reported confidence</text>'
        '<text x="10" y="210" fill="#9badA5" font-size="12" transform="rotate(-90 10 210)">empirical success</text>'
        f'<polyline points="{coordinates}" fill="none" stroke="#b7f55a" stroke-width="3"/>'
        + ''.join(f'<circle cx="{45 + float(item["mean_confidence"]) * 300:.1f}" cy="{340 - float(item["empirical_success"]) * 300:.1f}" r="5" fill="#f19554"/>' for item in points)
        + '</svg>', encoding="utf-8",
    )

    counts = result["posterior_rank_histogram"]["counts"]
    maximum = max(max(counts), 1)
    bars = ''.join(
        f'<rect x="{48 + index * 30}" y="{340 - count / maximum * 280:.1f}" width="20" height="{count / maximum * 280:.1f}" fill="#b7f55a"/>'
        for index, count in enumerate(counts)
    )
    ranks = root / "posterior_rank_histogram.svg"
    ranks.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="400" height="400" viewBox="0 0 400 400">'
        '<rect width="400" height="400" fill="#07100d"/><path d="M45 40V340H355" fill="none" stroke="#9badA5"/>'
        f'{bars}<text x="130" y="380" fill="#9badA5" font-size="12">posterior rank fraction</text></svg>',
        encoding="utf-8",
    )
    return {"calibration_table": str(table), "reliability_plot": str(reliability), "rank_histogram": str(ranks)}
