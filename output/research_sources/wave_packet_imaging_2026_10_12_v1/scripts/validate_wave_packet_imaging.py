"""Exploratory, healthy-calibrated packet imaging on previously inspected OGW data.

The new image is a raw diagnostic intensity, not a posterior or a damage test.
All three comparisons reveal the same geometry-only recorded path permutation.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
from time import perf_counter

import h5py
import numpy as np
import scipy
from threadpoolctl import threadpool_limits

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.app.evaluation.measured_guided_waves import (  # noqa: E402
    POSITIONS, SENSORS, damage_index, geometry_order, grid_points, kernel,
)
from backend.app.evaluation.wave_packet_imaging import (  # noqa: E402
    fit_packet_model, image_summary, residual_path_image,
)
from scripts.validate_measured_guided_waves import (  # noqa: E402
    SOURCE, TEMPERATURES, load_sources, stream_digest,
)

BUDGETS = (16, 32, 66)
CONTEXTS = ("condition_matched_baseline", "twenty_degree_baseline")
METHODS = ("raw_RAPID", "isotropic_packet", "directional_packet")
OUTPUT = ROOT / "research_results/wave_packet_imaging_development_2026_10_12.json"


def fingerprints() -> dict[str, str]:
    """Only the original, already inspected source subset is accessed here."""
    paths = [Path(__file__), ROOT / "backend/app/evaluation/wave_packet_imaging.py",
             ROOT / "backend/app/evaluation/measured_guided_waves.py",
             ROOT / "scripts/validate_measured_guided_waves.py",
             ROOT / "docs/WAVE_PACKET_IMAGING_PROTOCOL.md",
             SOURCE / "argus_manifest.json", SOURCE / "metadata/geometry.json",
             SOURCE / "metadata/primary_article.xml",
             *sorted((SOURCE / "numeric").rglob("*.h5"))]
    test_file = ROOT / "backend/tests/test_wave_packet_imaging.py"
    if test_file.exists():
        paths.append(test_file)
    return {path.relative_to(ROOT).as_posix(): stream_digest(path) for path in paths}


def healthy_pitch_banks(records: list[dict]) -> dict[int, np.ndarray]:
    """Pitch is read only after load_sources validated its schema and checksum.

    End-of-run source fingerprints detect any changed files during this read.
    Only healthy cycle 1 sources can influence propagation calibration.
    """
    pitch = {}
    for record in records:
        state, cycle, temperature = record["bank_key"]
        if state != "healthy" or cycle != 1:
            continue
        path = (ROOT / record["file"]).resolve()
        if not path.is_relative_to(SOURCE.resolve()) or stream_digest(path) != record["sha256"]:
            raise ValueError("Validated healthy pitch source changed or escaped its source directory")
        with h5py.File(path, "r") as h5:
            if not isinstance(h5.get("pitchcatch", getlink=True), h5py.HardLink):
                raise ValueError("Healthy pitch group must be an internal hard link")
            group = h5["pitchcatch"]
            if not isinstance(group.get("pitch", getlink=True), h5py.HardLink):
                raise ValueError("Healthy pitch must be an internal hard-linked dataset")
            node = group["pitch"]
            if (not isinstance(node, h5py.Dataset) or node.shape != (66, 13108)
                    or node.dtype.kind not in "iuf" or node.dtype.itemsize > 8
                    or node.is_virtual or node.external):
                raise ValueError("Healthy pitch numeric schema changed")
            values = node[()].astype(float)
            if not np.isfinite(values).all():
                raise ValueError("Healthy pitch contains nonfinite samples")
            pitch[int(temperature)] = values
    if set(pitch) != set(TEMPERATURES):
        raise ValueError("All three healthy cycle 1 pitch banks are required")
    return pitch


def replay_case(reference: np.ndarray, trial: np.ndarray, pitch: np.ndarray,
                pairs: np.ndarray, points: np.ndarray, spatial_kernel: np.ndarray,
                order: list[int], calibrations: dict) -> list[dict]:
    """Fixed geometry reveals paths; this function receives no reference location."""
    scores = {method: np.zeros(len(points)) for method in METHODS}
    failures = {method: [] for method in METHODS}
    results = []
    started = perf_counter()
    for step, path_index in enumerate(order, start=1):
        try:
            scores["raw_RAPID"] += damage_index(reference[path_index], trial[path_index]) * spatial_kernel[path_index]
        except (ValueError, RuntimeError, FloatingPointError) as exc:
            failures["raw_RAPID"].append({"path_index": path_index, "error": str(exc)})
        for method in METHODS[1:]:
            calibration = calibrations[method]
            if not calibration.supported:
                continue
            try:
                start, end = SENSORS[pairs[path_index]]
                contribution = residual_path_image(reference[path_index], trial[path_index],
                    pitch[path_index], start, end, points, calibration)
                scores[method] += contribution
            except (ValueError, RuntimeError, FloatingPointError) as exc:
                failures[method].append({"path_index": path_index, "error": str(exc)})
        if step not in BUDGETS:
            continue
        for method in METHODS:
            supported = method == "raw_RAPID" or calibrations[method].supported
            summary = image_summary(scores[method], points) if supported else {
                "map_m": None, "peak_to_mean": None, "flat_image": True,
                "scores_are_probabilities": False,
            }
            results.append({"method": method, "budget": step,
                "queried_path_indices": order[:step], "calibration_supported": bool(supported),
                "failed_opportunities": len(failures[method]), "path_failures": failures[method].copy(),
                "image_max": float(scores[method].max()) if supported else None,
                "image_mean": float(scores[method].mean()) if supported else None,
                "raw_intensity": scores[method].tolist() if supported else None,
                "damage_detection_supported": False, "damage_decision": None,
                "elapsed_s": perf_counter() - started, **summary})
    return results


def aggregate(runs: list[dict]) -> list[dict]:
    summaries = []
    for context in CONTEXTS:
        for method in METHODS:
            for budget in BUDGETS:
                cases = [row for row in runs if row["context"] == context
                         and row["method"] == method and row["budget"] == budget]
                damage = [row for row in cases if row["test_state"] != "healthy"]
                usable = [row for row in damage if row["location_error_mm"] is not None]
                healthy = [row for row in cases if row["test_state"] == "healthy"]
                mean_error = float(np.mean([row["location_error_mm"] for row in usable])) if usable else None
                per_position = {state: [row["location_error_mm"] for row in usable
                                       if row["test_state"] == state] for state in POSITIONS}
                controls = {(row["test_state"], row["nominal_temperature_c"]): row
                            for row in runs if row["context"] == context
                            and row["method"] == "raw_RAPID" and row["budget"] == budget}
                paired = [(row, controls[(row["test_state"], row["nominal_temperature_c"])])
                          for row in usable
                          if controls[(row["test_state"], row["nominal_temperature_c"])]["location_error_mm"] is not None]
                paired_deltas = [control["location_error_mm"] - row["location_error_mm"]
                                 for row, control in paired]
                summaries.append({"context": context, "method": method, "budget": budget,
                    "attempted_damage_conditions": 12, "usable_damage_conditions": len(usable),
                    "attempted_healthy_conditions": 3, "healthy_conditions": len(healthy),
                    "complete_condition_coverage": len(usable) == 12 and len(healthy) == 3,
                    "mean_location_error_mm": mean_error,
                    "median_location_error_mm": float(np.median([row["location_error_mm"] for row in usable])) if usable else None,
                    "per_position_mean_error_mm": {state: float(np.mean(values)) if values else None
                                                   for state, values in per_position.items()},
                    "paired_usable_conditions": len(paired),
                    "paired_raw_RAPID_mean_error_mm": float(np.mean([control["location_error_mm"] for _, control in paired])) if paired else None,
                    "paired_method_mean_error_mm": float(np.mean([row["location_error_mm"] for row, _ in paired])) if paired else None,
                    "paired_mean_error_reduction_vs_raw_RAPID_mm": float(np.mean(paired_deltas)) if paired else None,
                    "paired_conditions_improved_vs_raw_RAPID": sum(delta > 0 for delta in paired_deltas),
                    **{f"success_{radius}_mm": float(np.mean([row["location_error_mm"] <= radius for row in usable])) if usable else None
                       for radius in (25, 50, 100)},
                    "failed_opportunities": sum(row["failed_opportunities"] for row in cases),
                    "flat_healthy_images": sum(row["flat_image"] for row in healthy),
                    "healthy_image_max": [row["image_max"] for row in healthy],
                    "healthy_peak_to_mean": [row["peak_to_mean"] for row in healthy],
                    "healthy_false_positive_rate": None, "damage_detection_supported": False,
                    "scores_are_probabilities": False})
    return summaries


def run_study() -> dict:
    before = fingerprints()
    started = perf_counter()
    banks, pairs, records, failures = load_sources()
    result = {"metadata": {"study_kind": "exploratory_previously_inspected_measured_data",
        "protocol": "docs/WAVE_PACKET_IMAGING_PROTOCOL.md", "client_date": "2026-10-12",
        "native_sample_rate_hz": 10000000, "excitation_hz": 40000,
        "data_collection_doi": "10.6084/m9.figshare.c.4488089.v1", "data_license": "CC0",
        "independent_specimens": 1, "independent_reference_damage_positions": 4,
        "positions_collinear": True, "unique_damage_banks": 12, "unique_healthy_test_banks": 3,
        "contexts": list(CONTEXTS), "budgets": list(BUDGETS), "methods": list(METHODS),
        "propagation_training": "healthy_cycle1_only", "damaged_waveform_or_label_fit": False,
        "confirmation_dataset_accessed": False, "untouched_confirmation_claim": False,
        "scores_are_probabilities": False, "damage_detection_supported": False,
        "numpy_version": np.__version__, "scipy_version": scipy.__version__,
        "h5py_version": h5py.__version__, "numerical_thread_limit": 1,
        "source_sha256_before": before,
        "limitations": ["one_specimen_four_collinear_removable_surface_mass_surrogates",
            "all_original_cases_previously_inspected_exploratory_only",
            "first_packet_mode_not_independently_identified",
            "multiple_modes_dispersion_crosstalk_and_boundary_reflections",
            "test_source_timing_and_gain_are_not_aligned_to_the_healthy_pitch_template",
            "twofold_slowness_is_a_bounded_empirical_approximation",
            "condition_matching_does_not_establish_unseen_temperature_generalization",
            "fixed20_speed_does_not_compensate_temperature_shift",
            "raw_images_do_not_establish_detection_or_calibrated_probabilities",
            "offline_path_reveal_is_not_new_physical_adaptive_acquisition",
            "native40kHz_is_not_ARGUS_audio_range_hardware_validation",
            "delay_and_sum_and_directional_calibration_are_established_methods"]},
        "source_banks": records, "bank_failures": failures, "calibrations": [],
        "calibration_failures": [], "runs": [], "summary": []}
    if not failures:
        pitches = healthy_pitch_banks(records)
        points = grid_points()
        spatial_kernel = kernel(points, pairs)
        order = geometry_order(spatial_kernel, pairs)
        result["metadata"].update({"geometry_only_order": order, "points_m": points.tolist()})
        models = {}
        for temperature in TEMPERATURES:
            reference = banks[("healthy", 1, temperature)]
            models[temperature] = {}
            for method in METHODS[1:]:
                calibration = fit_packet_model(reference, pitches[temperature], pairs,
                                                directional=method == "directional_packet")
                models[temperature][method] = calibration
                details = {"method": method, "reference_temperature_c": temperature,
                           "training_bank_key": ["healthy", 1, temperature], **calibration.to_dict()}
                result["calibrations"].append(details)
                if not calibration.supported:
                    result["calibration_failures"].append(details)
        # No damaged observation is processed until every healthy model is fitted.
        for context in CONTEXTS:
            for state in (*POSITIONS, "healthy"):
                for temperature in TEMPERATURES:
                    reference_temperature = temperature if context == "condition_matched_baseline" else 20
                    rows = replay_case(banks[("healthy", 1, reference_temperature)],
                        banks[(state, 2 if state == "healthy" else 1, temperature)],
                        pitches[reference_temperature], pairs, points, spatial_kernel,
                        order, models[reference_temperature])
                    # Reference truth is used only after the fixed replay ends.
                    truth = np.asarray(POSITIONS[state]) if state != "healthy" else None
                    for row in rows:
                        location = row["map_m"]
                        row.update({"context": context, "test_state": state,
                            "nominal_temperature_c": temperature,
                            "reference_nominal_temperature_c": reference_temperature,
                            "reference_truth_m": truth.tolist() if truth is not None else None,
                            "location_error_mm": float(np.linalg.norm(np.asarray(location) - truth) * 1000)
                                if truth is not None and location is not None and not row["flat_image"] else None})
                    result["runs"].extend(rows)
        result["summary"] = aggregate(result["runs"])
    after = fingerprints()
    result["metadata"].update({"source_sha256_after": after,
        "source_changed_during_run": before != after, "elapsed_s": perf_counter() - started,
        "comparison_rows": len(result["runs"])})
    result["completed"] = not failures and before == after and len(result["runs"]) == 270
    result["all_packet_calibrations_supported"] = not result["calibration_failures"] and not failures
    return result


if __name__ == "__main__":
    if OUTPUT.exists():
        raise SystemExit("Development result exists; preserve it instead of overwriting")
    with threadpool_limits(limits=1):
        result = run_study()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation retains the no-overwrite boundary if another process races.
    with OUTPUT.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(result, separators=(",", ":"), allow_nan=False) + "\n")
    print(json.dumps({"output": str(OUTPUT), "completed": result["completed"],
        "all_packet_calibrations_supported": result["all_packet_calibrations_supported"],
        "source_changed_during_run": result["metadata"]["source_changed_during_run"],
        "budget66": [row for row in result["summary"] if row["budget"] == 66]}, indent=2))
