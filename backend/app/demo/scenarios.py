from __future__ import annotations

from dataclasses import replace

from backend.app.core.config import ArgusConfig
from backend.app.evaluation.neo_benchmark import run_benchmark_matrix
from backend.app.models.domain import Defect, Material
from backend.app.services.engine import ArgusEngine


SCENARIOS = {
    "rival_hypotheses": {
        "title": "Rival Hypotheses",
        "purpose": "Demonstrate legitimate counterfactual separation and diagnostic/calibration switching.",
        "evidence_source": "deterministic simulation",
    },
    "model_mismatch": {
        "title": "Model Mismatch",
        "purpose": "Compare discrepancy-aware ARGUS NEO with a deliberately naive ablation under propagation mismatch.",
        "evidence_source": "deterministic simulation",
    },
    "measurement_compression": {
        "title": "Measurement Compression",
        "purpose": "Compare fixed-grid and adaptive policies under one shared reliability criterion over paired seeds.",
        "evidence_source": "paired simulation benchmark",
    },
}


def _trace_engine(engine: ArgusEngine, maximum: int, progress=None, cancelled=None) -> dict:
    trace = []
    for index in range(maximum):
        if cancelled and cancelled():
            break
        before = engine.status()
        recommendation = engine.current_recommendation
        result = engine.run_recommended()
        after = engine.status()
        trace.append({
            "step": index + 1, "action_type": result.action_type,
            "experiment": result.parameters.to_dict(), "explanation": recommendation.explanation,
            "structural_uncertainty_before": before["structural_uncertainty"],
            "structural_uncertainty_after": after["structural_uncertainty"],
            "metrology_uncertainty_before": before["metrology_uncertainty"],
            "metrology_uncertainty_after": after["metrology_uncertainty"],
            "model_trust_after": after["model_trust"], "ood_status_after": after["ood_status"],
            "map_after": [after["map_x"], after["map_y"]],
            "top_hypotheses_after": after["top_hypotheses"][:2],
            "measurement_accepted": bool(result.quality.get("accepted", True)),
        })
        if progress:
            progress((index + 1) / maximum)
        if after["should_stop"] and not engine.automatic_recovery_available():
            break
    final = engine.status()
    return {
        "trace": trace,
        "summary": {
            "measurements": len(engine.experiments), "localization_error_mm": engine.localization_error() * 1_000,
            "final_entropy": final["normalized_entropy"], "decision_confidence": final["decision_confidence"],
            "model_trust": final["model_trust"], "ood_status": final["ood_status"],
            "stop_reason": final["stop_reason"],
            "action_counts": {name: sum(item["action_type"] == name for item in trace) for name in ("diagnostic", "calibration", "verification", "exploration")},
        },
        "sealed_truth": engine.truth.to_dict(),
    }


def rival_hypotheses(seed: int = 17, progress=None, cancelled=None) -> dict:
    config = ArgusConfig(
        seed=seed, max_experiments=15, candidate_count=28, planner_horizon=2,
        expected_value_stop_threshold=-1.0, profile="demo",
    )
    engine = ArgusEngine(config=config, seed=seed, preset="easy")
    result = _trace_engine(engine, config.max_experiments, progress, cancelled)
    result["metadata"] = {
        **SCENARIOS["rival_hypotheses"], "seed": seed,
        "truth_policy": "sealed during execution and included only in the completed report",
        "presentation_note": "The action sequence is simulator-produced, not scripted; inspect trace/action_counts before claiming a calibration switch.",
    }
    return result


def model_mismatch(seed: int = 17, progress=None, cancelled=None) -> dict:
    assumed = Material()
    actual = replace(assumed, wave_velocity=assumed.wave_velocity * 1.02, attenuation=assumed.attenuation * 1.04)
    truth = ArgusEngine(ArgusConfig(seed=seed), seed=seed, preset="easy").truth
    neo_config = ArgusConfig(
        seed=seed, max_experiments=17, candidate_count=28, planner_horizon=2,
        expected_value_stop_threshold=-1.0,
    )
    naive_config = replace(
        neo_config, enable_nuisance_inference=False, enable_discrepancy_model=False,
        enable_calibration_actions=False, enable_ood_layer=False,
    )
    neo = ArgusEngine(neo_config, material=assumed, acquisition_material=actual, seed=seed, truth=truth)
    naive = ArgusEngine(naive_config, material=assumed, acquisition_material=actual, seed=seed, truth=truth)
    neo_result = _trace_engine(neo, neo_config.max_experiments, (lambda value: progress(value * 0.6)) if progress else None, cancelled)
    naive_result = _trace_engine(naive, naive_config.max_experiments, (lambda value: progress(0.6 + value * 0.4)) if progress else None, cancelled)
    return {
        "metadata": {
            **SCENARIOS["model_mismatch"], "seed": seed,
            "assumed_material": assumed.to_dict(), "acquisition_material": actual.to_dict(),
            "paired_truth": truth.to_dict(), "comparison": "same truth, seed, budget and acquisition mismatch",
        },
        "argus_neo": neo_result,
        "naive_ablation": naive_result,
        "observed_effect": {
            "neo_error_advantage_mm": naive_result["summary"]["localization_error_mm"] - neo_result["summary"]["localization_error_mm"],
            "neo_calibrations": neo_result["summary"]["action_counts"]["calibration"],
            "neo_final_trust": neo_result["summary"]["model_trust"],
            "naive_error_mm": naive_result["summary"]["localization_error_mm"],
            "naive_confidence_gap": (
                naive_result["summary"]["decision_confidence"]
                - neo_result["summary"]["decision_confidence"]
            ),
        },
    }


def measurement_compression(seed: int = 100, cases: int = 4, progress=None, cancelled=None) -> dict:
    benchmark = run_benchmark_matrix(cases=cases, max_experiments=7, seed=seed, progress=progress, cancelled=cancelled)
    fixed = benchmark["summary"]["uniform_grid"]
    adaptive = benchmark["summary"]["full_argus_neo"]
    return {
        "metadata": {**SCENARIOS["measurement_compression"], "seed": seed, "cases": cases},
        "fixed_mean_measurements": fixed["measurements"]["mean"],
        "adaptive_mean_measurements": adaptive["measurements"]["mean"],
        "observed_compression": adaptive["inspection_compression"],
        "adaptive_measurement_ci": adaptive["measurements"]["bootstrap_95ci"],
        "paired_comparison": benchmark["paired_comparisons"]["full_vs_uniform_grid"],
        "criterion": benchmark["metadata"]["criterion"],
        "benchmark": benchmark,
    }


def run_demo_scenario(name: str, *, seed: int | None = None, cases: int = 4, progress=None, cancelled=None) -> dict:
    if name == "rival_hypotheses":
        return rival_hypotheses(seed if seed is not None else 17, progress, cancelled)
    if name == "model_mismatch":
        return model_mismatch(seed if seed is not None else 17, progress, cancelled)
    if name == "measurement_compression":
        return measurement_compression(seed if seed is not None else 100, cases, progress, cancelled)
    raise ValueError(f"Unknown demo scenario: {name}")
