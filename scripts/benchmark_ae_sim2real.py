from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import numpy as np
from scipy.optimize import lsq_linear
from sklearn.ensemble import ExtraTreesRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import GroupKFold
from sklearn.neighbors import KNeighborsRegressor
from sklearn.preprocessing import StandardScaler


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA = ROOT / "datasets" / "generated" / "ae_impact_features.npz"
SENSORS = np.asarray([[0.05, 0.95], [0.05, 0.05], [0.95, 0.05]], dtype=np.float64)


def effective_speed(tx: np.ndarray, rx: np.ndarray, toa: np.ndarray) -> tuple[float, float, float]:
    distance = np.linalg.norm(tx - rx, axis=1)
    design = np.column_stack([distance, np.ones(len(distance))])
    slope, intercept = np.linalg.lstsq(design, toa, rcond=None)[0]
    prediction = design @ np.asarray([slope, intercept])
    return float(1 / slope), float(intercept), float(np.sqrt(np.mean((toa - prediction) ** 2)))


def centered(values: np.ndarray) -> np.ndarray:
    return values - np.mean(values, axis=-1, keepdims=True)


def fit_timing_transport(raw_times: np.ndarray, positions: np.ndarray, speed: float) -> tuple[float, np.ndarray]:
    observed = centered(raw_times)
    distances = np.linalg.norm(positions[:, None, :] - SENSORS[None, :, :], axis=2)
    target = centered(distances / speed)
    rows = []
    values = []
    for event in range(len(positions)):
        for sensor in range(3):
            # Sensor offsets use sensor 0 as the reference; centering is applied
            # after fitting before the values are used for localization.
            rows.append([observed[event, sensor], float(sensor == 1), float(sensor == 2)])
            values.append(target[event, sensor])
    solution = lsq_linear(
        np.asarray(rows),
        np.asarray(values),
        bounds=(np.asarray([0.05, -5e-4, -5e-4]), np.asarray([20.0, 5e-4, 5e-4])),
    ).x
    offsets = np.asarray([0.0, solution[1], solution[2]])
    return float(solution[0]), offsets - np.mean(offsets)


def localize(times: np.ndarray, speed: float, scale: float = 1.0, offsets: np.ndarray | None = None) -> np.ndarray:
    offsets = np.zeros(3) if offsets is None else np.asarray(offsets, dtype=np.float64)
    observed = centered(scale * np.asarray(times, dtype=np.float64) + offsets)
    axis = np.linspace(0.0, 1.0, 201)
    xx, yy = np.meshgrid(axis, axis)
    candidates = np.column_stack([xx.ravel(), yy.ravel()])
    distance = np.linalg.norm(candidates[:, None, :] - SENSORS[None, :, :], axis=2)
    predicted = centered(distance / speed)
    return candidates[int(np.argmin(np.mean((predicted - observed) ** 2, axis=1)))]


def benchmark(
    data: Path,
    model_output: Path,
    few_shot_output: Path,
    calibration_output: Path,
    metrics_output: Path,
    seed: int,
) -> dict:
    with np.load(data) as payload:
        simulation_features = payload["simulation_features"].astype(np.float64)
        simulation_toa = payload["simulation_toa"].astype(np.float64)
        simulation_tx = payload["simulation_tx"].astype(np.float64)
        simulation_rx = payload["simulation_rx"].astype(np.float64)
        groups = payload["simulation_groups"].astype(int)
        experimental_features = payload["experimental_features"].astype(np.float64)
        positions = payload["experimental_positions"].astype(np.float64)[::3]
        metadata = json.loads(str(payload["metadata"]))

    splitter = GroupKFold(n_splits=5)
    held_out_prediction = np.zeros(len(simulation_toa), dtype=np.float64)
    for fold, (train, test) in enumerate(splitter.split(simulation_features, simulation_toa, groups), start=1):
        model = ExtraTreesRegressor(
            n_estimators=350,
            min_samples_leaf=2,
            max_features=0.85,
            n_jobs=-1,
            random_state=seed + fold,
        )
        model.fit(simulation_features[train], simulation_toa[train])
        held_out_prediction[test] = model.predict(simulation_features[test])
    simulation_metrics = {
        "tx_group_held_out_mae_us": float(mean_absolute_error(simulation_toa, held_out_prediction) * 1e6),
        "tx_group_held_out_r2": float(r2_score(simulation_toa, held_out_prediction)),
    }
    model = ExtraTreesRegressor(
        n_estimators=500,
        min_samples_leaf=2,
        max_features=0.85,
        n_jobs=-1,
        random_state=seed,
    )
    model.fit(simulation_features, simulation_toa)
    real_times = model.predict(experimental_features).reshape(-1, 3)
    speed, intercept, geometric_rmse = effective_speed(simulation_tx, simulation_rx, simulation_toa)

    baseline_predictions = np.asarray([localize(times, speed) for times in real_times])
    baseline_errors = np.linalg.norm(baseline_predictions - positions, axis=1)
    calibrated_predictions = []
    fold_calibrations = []
    for held_out in range(len(positions)):
        train = np.arange(len(positions)) != held_out
        scale, offsets = fit_timing_transport(real_times[train], positions[train], speed)
        calibrated_predictions.append(localize(real_times[held_out], speed, scale, offsets))
        fold_calibrations.append({"held_out_position": positions[held_out].tolist(), "scale": scale, "sensor_offsets_us": (offsets * 1e6).tolist()})
    calibrated_predictions = np.asarray(calibrated_predictions)
    calibrated_errors = np.linalg.norm(calibrated_predictions - positions, axis=1)
    final_scale, final_offsets = fit_timing_transport(real_times, positions, speed)
    event_features = experimental_features.reshape(len(positions), -1)
    few_shot_predictions = []
    for held_out in range(len(positions)):
        train = np.arange(len(positions)) != held_out
        scaler = StandardScaler().fit(event_features[train])
        localizer = KNeighborsRegressor(n_neighbors=3, weights="distance")
        localizer.fit(scaler.transform(event_features[train]), positions[train])
        few_shot_predictions.append(localizer.predict(scaler.transform(event_features[held_out : held_out + 1]))[0])
    few_shot_predictions = np.asarray(few_shot_predictions)
    few_shot_errors = np.linalg.norm(few_shot_predictions - positions, axis=1)
    timing_correction_accepted = bool(np.mean(calibrated_errors) < np.mean(baseline_errors))
    final_scaler = StandardScaler().fit(event_features)
    final_localizer = KNeighborsRegressor(n_neighbors=3, weights="distance")
    final_localizer.fit(final_scaler.transform(event_features), positions)
    calibration = {
        "method": "simulation-trained ToA regressor plus measured affine TDoA correction v1",
        "effective_simulation_speed_m_s": speed,
        "simulation_intercept_us": intercept * 1e6,
        "simulation_geometric_rmse_us": geometric_rmse * 1e6,
        "measured_timing_scale": final_scale,
        "measured_sensor_offsets_us": (final_offsets * 1e6).tolist(),
        "timing_correction_accepted": timing_correction_accepted,
        "negative_transfer_guard": (
            "accepted" if timing_correction_accepted else "rejected because leave-one-position-out error increased"
        ),
        "deployed_strategy": "measured_few_shot_knn_with_three_neighbors",
        "sensor_coordinates_m": SENSORS.tolist(),
        "source": metadata["source"],
        "doi": metadata["doi"],
        "license": metadata["license"],
        "scope": "250 kHz aluminium impact localization only; do not apply this speed or timing correction to the low-frequency GFRP/phone path.",
    }
    metrics = {
        "dataset": metadata["source"],
        "doi": metadata["doi"],
        "license": metadata["license"],
        "simulation": simulation_metrics,
        "real_localization": {
            "evaluation": "leave-one-impact-position-out timing calibration across nine measured positions",
            "baseline_mean_error_m": float(np.mean(baseline_errors)),
            "baseline_median_error_m": float(np.median(baseline_errors)),
            "calibrated_mean_error_m": float(np.mean(calibrated_errors)),
            "calibrated_median_error_m": float(np.median(calibrated_errors)),
            "few_shot_mean_error_m": float(np.mean(few_shot_errors)),
            "few_shot_median_error_m": float(np.median(few_shot_errors)),
            "few_shot_improvement_vs_simulation_percent": float(
                100 * (np.mean(baseline_errors) - np.mean(few_shot_errors)) / np.mean(baseline_errors)
            ),
            "baseline_predictions": baseline_predictions.tolist(),
            "calibrated_predictions": calibrated_predictions.tolist(),
            "few_shot_predictions": few_shot_predictions.tolist(),
            "truth": positions.tolist(),
            "fold_calibrations": fold_calibrations,
        },
        "limitations": [
            "Only nine measured impact positions and three sensor channels are available.",
            "The experiment concerns transient impacts at 250 kHz, not persistent delamination/cavity localization.",
            "The measured calibration is evaluated leave-one-position-out but not specimen-held-out because the record contains one plate.",
        ],
    }
    model_output.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": model, "feature_names": metadata["feature_names"], "metadata": metadata}, model_output)
    joblib.dump(
        {
            "scaler": final_scaler,
            "model": final_localizer,
            "per_sensor_feature_names": metadata["feature_names"],
            "sensor_coordinates_m": SENSORS.tolist(),
            "source": metadata["source"],
            "scope": "Few-shot interpolation within the measured 0.4-0.7 m impact grid; not extrapolation or hidden-defect validation.",
        },
        few_shot_output,
    )
    calibration_output.write_text(json.dumps(calibration, indent=2), encoding="utf-8")
    metrics_output.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark paired AE simulation-to-experiment timing transfer")
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--model-output", type=Path, default=ROOT / "models" / "ae_toa_regressor.joblib")
    parser.add_argument("--few-shot-output", type=Path, default=ROOT / "models" / "ae_real_fewshot_localizer.joblib")
    parser.add_argument("--calibration-output", type=Path, default=ROOT / "models" / "ae_timing_calibration.json")
    parser.add_argument("--metrics-output", type=Path, default=ROOT / "models" / "ae_sim2real_metrics.json")
    parser.add_argument("--seed", type=int, default=79)
    args = parser.parse_args()
    metrics = benchmark(
        args.data,
        args.model_output,
        args.few_shot_output,
        args.calibration_output,
        args.metrics_output,
        args.seed,
    )
    sim = metrics["simulation"]
    real = metrics["real_localization"]
    print(f"simulation ToA held-out: MAE={sim['tx_group_held_out_mae_us']:.2f} us, R2={sim['tx_group_held_out_r2']:.3f}")
    print(
        f"measured localization mean error: simulation transfer {real['baseline_mean_error_m']:.3f} m; "
        f"few-shot measured calibration {real['few_shot_mean_error_m']:.3f} m "
        f"({real['few_shot_improvement_vs_simulation_percent']:.1f}% improvement)"
    )


if __name__ == "__main__":
    main()
