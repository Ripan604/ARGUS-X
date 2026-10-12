"""Separate exploratory replay restricted to qualified healthy packet paths.

Previously seen results remain unchanged and supply descriptive paired controls.
Rejections consume common recorded opportunities and are never hidden as savings.
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
from backend.app.evaluation.wave_packet_qualification import qualify_packet_reference  # noqa: E402
from scripts.validate_measured_guided_waves import (  # noqa: E402
    SOURCE, TEMPERATURES, load_sources, stream_digest,
)
from scripts.validate_wave_packet_imaging import healthy_pitch_banks  # noqa: E402

BUDGETS = (16, 32, 66)
CONTEXTS = ("condition_matched_baseline", "twenty_degree_baseline")
METHODS = ("raw_RAPID", "qualified_isotropic_packet", "qualified_directional_packet")
FIRST_METHOD = {"raw_RAPID": "raw_RAPID", "qualified_isotropic_packet": "isotropic_packet",
                "qualified_directional_packet": "directional_packet"}
FIRST_RESULT = ROOT / "research_results/wave_packet_imaging_development_2026_10_12.json"
SNAPSHOT = ROOT / "output/research_sources/wave_packet_imaging_2026_10_12_v1"
OUTPUT = ROOT / "research_results/qualified_wave_packet_imaging_development_2026_10_12.json"


def fingerprints() -> dict[str, str]:
    paths = [Path(__file__), ROOT / "docs/QUALIFIED_WAVE_PACKET_PROTOCOL.md",
        ROOT / "backend/app/evaluation/wave_packet_qualification.py",
        ROOT / "backend/app/evaluation/wave_packet_imaging.py",
        ROOT / "backend/app/evaluation/measured_guided_waves.py",
        ROOT / "scripts/validate_wave_packet_imaging.py",
        ROOT / "scripts/validate_measured_guided_waves.py", FIRST_RESULT,
        SOURCE / "argus_manifest.json", SOURCE / "metadata/geometry.json",
        SOURCE / "metadata/primary_article.xml", *sorted((SOURCE / "numeric").rglob("*.h5")),
        *sorted(path for path in SNAPSHOT.rglob("*") if path.is_file())]
    for name in ("test_wave_packet_qualification.py", "test_wave_packet_imaging.py"):
        path = ROOT / "backend/tests" / name
        if path.exists():
            paths.append(path)
    return {path.relative_to(ROOT).as_posix(): stream_digest(path) for path in paths}


def retained_first_study(before: dict[str, str]) -> tuple[dict, dict]:
    first = json.loads(FIRST_RESULT.read_text(encoding="utf-8"))
    if not first.get("completed") or first["metadata"]["source_changed_during_run"]:
        raise ValueError("A completed unchanged first development study is required")
    manifest = json.loads((SNAPSHOT / "manifest.json").read_text(encoding="utf-8"))
    if len(manifest["files"]) != 6:
        raise ValueError("The six frozen first-study code/protocol sources are required")
    for row in manifest["files"]:
        archive = (ROOT / row["archive_path"]).resolve()
        if (not archive.is_relative_to(SNAPSHOT.resolve())
                or stream_digest(archive) != row["sha256"]
                or first["metadata"]["source_sha256_before"][row["original_path"]] != row["sha256"]):
            raise ValueError("Retained first-study source snapshot does not match its evidence hashes")
    for name, digest in first["metadata"]["source_sha256_before"].items():
        if name.startswith("datasets/external/open_guided_waves/") and before.get(name) != digest:
            raise ValueError("The original measured dataset changed since the first study")
    index = {(row["context"], row["test_state"], row["nominal_temperature_c"],
              row["method"], row["budget"]): row for row in first["runs"]}
    if len(index) != 270:
        raise ValueError("First-study comparison identities are incomplete or duplicated")
    return first, index


def replay_case(reference, trial, pitch, pairs, points, spatial_kernel, order,
                calibrations: dict, qualifications: dict) -> list[dict]:
    """No damage truth or retained test result reaches this fixed replay."""
    scores = {method: np.zeros(len(points)) for method in METHODS}
    used = {method: [] for method in METHODS}
    rejected = {method: [] for method in METHODS}
    failures = {method: [] for method in METHODS}
    eligible = {method: set(qualification.eligible_indices)
                for method, qualification in qualifications.items()}
    results = []
    started = perf_counter()
    for step, path_index in enumerate(order, start=1):
        try:
            scores["raw_RAPID"] += damage_index(reference[path_index], trial[path_index]) * spatial_kernel[path_index]
            used["raw_RAPID"].append(path_index)
        except (ValueError, RuntimeError, FloatingPointError) as exc:
            failures["raw_RAPID"].append({"path_index": path_index, "error": str(exc)})
        for method in METHODS[1:]:
            qualification = qualifications[method]
            if not qualification.supported or path_index not in eligible[method]:
                rejected[method].append(path_index)
                continue
            try:
                start, end = SENSORS[pairs[path_index]]
                contribution = residual_path_image(reference[path_index], trial[path_index],
                    pitch[path_index], start, end, points, calibrations[method])
                scores[method] += contribution
                used[method].append(path_index)
            except (ValueError, RuntimeError, FloatingPointError) as exc:
                failures[method].append({"path_index": path_index, "error": str(exc)})
        if step not in BUDGETS:
            continue
        for method in METHODS:
            supported = method == "raw_RAPID" or qualifications[method].supported
            summary = image_summary(scores[method], points) if supported else {
                "map_m": None, "peak_to_mean": None, "flat_image": True,
                "scores_are_probabilities": False}
            results.append({"method": method, "budget": step,
                "queried_path_indices": order[:step], "opportunities_consumed": step,
                "calibration_supported": method == "raw_RAPID" or calibrations[method].supported,
                "qualification_supported": bool(supported),
                "used_path_indices": used[method].copy(), "used_path_count": len(used[method]),
                "qualification_rejected_path_indices": rejected[method].copy(),
                "qualification_rejected_opportunities": len(rejected[method]),
                "processing_failures": failures[method].copy(),
                "processing_failed_opportunities": len(failures[method]),
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
                usable = [row for row in cases if row["test_state"] != "healthy"
                          and row["location_error_mm"] is not None]
                healthy = [row for row in cases if row["test_state"] == "healthy"]
                supported_healthy = [row for row in healthy if row["qualification_supported"]]
                paired = [row for row in usable if row["paired_raw_RAPID_error_mm"] is not None
                          and row["first_study_all_path_error_mm"] is not None]
                raw_deltas = [row["paired_raw_RAPID_error_mm"] - row["location_error_mm"] for row in paired]
                first_deltas = [row["first_study_all_path_error_mm"] - row["location_error_mm"] for row in paired]
                mean = lambda values: float(np.mean(values)) if values else None
                summaries.append({"context": context, "method": method, "budget": budget,
                    "attempted_damage_conditions": 12, "usable_damage_conditions": len(usable),
                    "healthy_conditions": len(healthy), "supported_healthy_conditions": len(supported_healthy),
                    "complete_condition_coverage": len(usable) == 12 and len(supported_healthy) == 3,
                    "mean_location_error_mm": mean([row["location_error_mm"] for row in usable]),
                    "paired_usable_conditions": len(paired),
                    "paired_raw_RAPID_mean_error_mm": mean([row["paired_raw_RAPID_error_mm"] for row in paired]),
                    "paired_first_study_all_path_mean_error_mm": mean([row["first_study_all_path_error_mm"] for row in paired]),
                    "paired_qualified_mean_error_mm": mean([row["location_error_mm"] for row in paired]),
                    "paired_mean_error_reduction_vs_raw_RAPID_mm": mean(raw_deltas),
                    "paired_mean_error_reduction_vs_first_all_path_mm": mean(first_deltas),
                    "paired_conditions_improved_vs_raw_RAPID": sum(delta > 0 for delta in raw_deltas),
                    "paired_conditions_improved_vs_first_all_path": sum(delta > 0 for delta in first_deltas),
                    **{f"success_{radius}_mm": mean([row["location_error_mm"] <= radius for row in usable])
                       for radius in (25, 50, 100)},
                    "used_path_counts": sorted(set(row["used_path_count"] for row in cases)),
                    "qualification_rejected_opportunities": sum(row["qualification_rejected_opportunities"] for row in cases),
                    "processing_failed_opportunities": sum(row["processing_failed_opportunities"] for row in cases),
                    "flat_supported_healthy_images": sum(row["flat_image"] for row in supported_healthy),
                    "healthy_image_max": [row["image_max"] for row in healthy],
                    "healthy_peak_to_mean": [row["peak_to_mean"] for row in healthy],
                    "healthy_false_positive_rate": None, "damage_detection_supported": False,
                    "scores_are_probabilities": False})
    return summaries


def run_study() -> dict:
    before = fingerprints()
    started = perf_counter()
    first, first_index = retained_first_study(before)
    banks, pairs, records, failures = load_sources()
    result = {"metadata": {"study_kind": "exploratory_previously_inspected_measured_data",
        "protocol": "docs/QUALIFIED_WAVE_PACKET_PROTOCOL.md", "client_date": "2026-10-12",
        "first_study_result": FIRST_RESULT.relative_to(ROOT).as_posix(),
        "first_study_sha256": before[FIRST_RESULT.relative_to(ROOT).as_posix()],
        "first_study_source_snapshot": SNAPSHOT.relative_to(ROOT).as_posix(),
        "first_study_snapshot_verified": True, "contexts": list(CONTEXTS),
        "methods": list(METHODS), "budgets": list(BUDGETS), "recorded_paths": 66,
        "native_sample_rate_hz": 10000000, "excitation_hz": 40000,
        "data_collection_doi": "10.6084/m9.figshare.c.4488089.v1", "data_license": "CC0",
        "independent_specimens": 1, "reference_damage_positions": 4, "positions_collinear": True,
        "unique_damage_banks": 12, "unique_healthy_test_banks": 3,
        "propagation_and_reference_qualification_training": "healthy_cycle1_only",
        "test_response_or_damage_label_fit": False, "test_pitch_alignment": False,
        "confirmation_dataset_accessed": False, "untouched_confirmation_claim": False,
        "damage_detection_supported": False, "scores_are_probabilities": False,
        "numpy_version": np.__version__, "scipy_version": scipy.__version__,
        "h5py_version": h5py.__version__, "numerical_thread_limit": 1,
        "source_sha256_before": before,
        "limitations": ["same_original_banks_and_first_study_previously_seen",
            "gate_motivated_by_healthy40_near_zero_reference_path_observation",
            "one_specimen_four_collinear_surface_mass_surrogates",
            "qualification_does_not_establish_full_scatter_model_validity",
            "common_opportunities_include_qualification_rejections",
            "test_source_timing_and_gain_unaligned",
            "no_threshold_sensitivity_specificity_or_calibrated_probability_claim",
            "directional_delay_and_sum_is_established_prior_work",
            "offline_native40kHz_does_not_validate_ARGUS_audio_range_hardware"]},
        "source_banks": records, "bank_failures": failures, "calibrations": [],
        "qualifications": [], "runs": [], "summary": []}
    if not failures:
        pitches = healthy_pitch_banks(records)
        catch_stack = np.stack([banks[("healthy", 1, temperature)] for temperature in TEMPERATURES])
        pitch_stack = np.stack([pitches[temperature] for temperature in TEMPERATURES])
        points = grid_points()
        spatial_kernel = kernel(points, pairs)
        order = geometry_order(spatial_kernel, pairs)
        if order != first["metadata"]["geometry_only_order"]:
            raise ValueError("Common recorded opportunity order changed from the first study")
        result["metadata"].update({"geometry_only_order": order, "points_m": points.tolist()})
        models, qualifications = {}, {}
        for baseline_index, temperature in enumerate(TEMPERATURES):
            models[temperature], qualifications[temperature] = {}, {}
            for method in METHODS[1:]:
                calibration = fit_packet_model(catch_stack[baseline_index], pitch_stack[baseline_index],
                                                pairs, directional=method == "qualified_directional_packet")
                qualification = qualify_packet_reference(catch_stack, pitch_stack, baseline_index, calibration)
                models[temperature][method], qualifications[temperature][method] = calibration, qualification
                identity = {"method": method, "reference_temperature_c": temperature,
                            "healthy_training_bank_keys": [["healthy", 1, t] for t in TEMPERATURES]}
                result["calibrations"].append({**identity, **calibration.to_dict()})
                result["qualifications"].append({**identity, **qualification.to_dict()})
        # Fit every healthy model and qualification before processing new trial images.
        for context in CONTEXTS:
            for state in (*POSITIONS, "healthy"):
                for temperature in TEMPERATURES:
                    reference_temperature = temperature if context == "condition_matched_baseline" else 20
                    rows = replay_case(banks[("healthy", 1, reference_temperature)],
                        banks[(state, 2 if state == "healthy" else 1, temperature)], pitches[reference_temperature],
                        pairs, points, spatial_kernel, order, models[reference_temperature],
                        qualifications[reference_temperature])
                    truth = np.asarray(POSITIONS[state]) if state != "healthy" else None
                    for row in rows:
                        location = row["map_m"]
                        identity = (context, state, temperature, FIRST_METHOD[row["method"]], row["budget"])
                        retained = first_index[identity]
                        raw_control = first_index[(context, state, temperature, "raw_RAPID", row["budget"])]
                        row.update({"context": context, "test_state": state, "nominal_temperature_c": temperature,
                            "reference_nominal_temperature_c": reference_temperature,
                            "reference_truth_m": truth.tolist() if truth is not None else None,
                            "location_error_mm": float(np.linalg.norm(np.asarray(location) - truth) * 1000)
                                if truth is not None and location is not None and not row["flat_image"] else None,
                            "first_study_all_path_method": FIRST_METHOD[row["method"]],
                            "first_study_all_path_error_mm": retained["location_error_mm"],
                            "first_study_all_path_map_m": retained["map_m"],
                            "first_study_all_path_image_max": retained["image_max"],
                            "paired_raw_RAPID_error_mm": raw_control["location_error_mm"]})
                    result["runs"].extend(rows)
        result["summary"] = aggregate(result["runs"])
    after = fingerprints()
    raw_rows = [row for row in result["runs"] if row["method"] == "raw_RAPID"]
    raw_match = all(row["map_m"] == row["first_study_all_path_map_m"]
                    and row["location_error_mm"] == row["first_study_all_path_error_mm"] for row in raw_rows)
    result["metadata"].update({"source_sha256_after": after, "source_changed_during_run": before != after,
        "elapsed_s": perf_counter() - started, "comparison_rows": len(result["runs"]),
        "raw_RAPID_matches_retained_first_study": len(raw_rows) == 90 and raw_match})
    result["completed"] = not failures and before == after and len(result["runs"]) == 270 and raw_match
    result["all_packet_qualifications_supported"] = bool(result["qualifications"]) and all(
        row["supported"] for row in result["qualifications"])
    return result


if __name__ == "__main__":
    if OUTPUT.exists():
        raise SystemExit("Qualified development result exists; preserve it instead of overwriting")
    with threadpool_limits(limits=1):
        result = run_study()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(result, separators=(",", ":"), allow_nan=False) + "\n")
    print(json.dumps({"output": str(OUTPUT), "completed": result["completed"],
        "source_changed_during_run": result["metadata"]["source_changed_during_run"],
        "raw_RAPID_matches_first_study": result["metadata"]["raw_RAPID_matches_retained_first_study"],
        "budget66": [row for row in result["summary"] if row["budget"] == 66]}, indent=2))
