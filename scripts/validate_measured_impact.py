"""Source-bound, position-held-out reanalysis of nine measured AE CSVs."""
from __future__ import annotations
from hashlib import md5, sha256
import json
from pathlib import Path
import sys
from time import perf_counter

import numpy as np
from scipy.optimize import lsq_linear
from sklearn.neighbors import KNeighborsRegressor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.prepare_ae_impact_dataset import EXPERIMENT_PATTERN, FEATURE_NAMES, ultrasonic_features

SOURCE = ROOT / "datasets/external/ae_impact_2024"
SENSORS = np.array([[.05,.95],[.05,.05],[.95,.05]])
POLICIES = ("train_centroid", "knn_1", "knn_3", "calibrated_tdoa_q05")


def fingerprints() -> dict:
    paths = [Path(__file__), ROOT/"scripts/prepare_ae_impact_dataset.py",
             ROOT/"backend/tests/test_measured_impact_validation.py",
             ROOT/"docs/MEASURED_IMPACT_VALIDATION_PROTOCOL.md",
             SOURCE/"current_record_2026_10_08.json", *sorted(SOURCE.glob("Test*.csv"))]
    return {p.relative_to(ROOT).as_posix(): sha256(p.read_bytes()).hexdigest() for p in paths}


def load_measured() -> tuple[np.ndarray, np.ndarray, list[dict]]:
    record = json.loads((SOURCE/"current_record_2026_10_08.json").read_text())
    if record["metadata"]["license"]["id"] != "cc-by-4.0":
        raise ValueError("Expected source license declaration missing")
    published = {f["key"]: f for f in record["files"] if f["key"].endswith(".csv")}
    files = sorted(SOURCE.glob("Test*.csv"))
    if len(files) != 9 or {p.name for p in files} != set(published):
        raise ValueError("Measured file set differs from the official nine-position record")
    X, coordinates, provenance = [], [], []
    seen = set()
    for path in files:
        content = path.read_bytes()
        item = published[path.name]
        if len(content) != item["size"] or "md5:"+md5(content).hexdigest() != item["checksum"]:
            raise ValueError("Measured source checksum or size mismatch")
        with path.open() as handle:
            if handle.readline().strip() != "s1,s2,s3":
                raise ValueError("Measured channel identity mismatch")
        signal = np.loadtxt(path, delimiter=",", skiprows=1)
        if signal.shape != (5000,3) or not np.isfinite(signal).all():
            raise ValueError("Measured CSV must contain exactly 5000 by 3 finite samples")
        digest = sha256(signal.astype("<f8").tobytes()).hexdigest()
        if digest in seen:
            raise ValueError("Duplicate raw measurement")
        seen.add(digest)
        match = EXPERIMENT_PATTERN.match(path.stem)
        if match is None:
            raise ValueError("Measured source location missing from publisher filename")
        position = [float(match.group("x")), float(match.group("y"))]
        coordinates.append(position)
        features = np.asarray([ultrasonic_features(signal[1500:3100,s]) for s in range(3)])
        X.append(features)
        provenance.append({"file": path.name, "sha256": sha256(content).hexdigest(),
            "published_md5_verified": True, "position_m": position, "rows": 5000,
            "channels": 3, "sampling_rate_hz": 2000000, "distinct_repeat_axis": False})
    return np.asarray(X), np.asarray(coordinates), provenance


def train_tdoa(times: np.ndarray, positions: np.ndarray) -> dict:
    if times.shape != (len(positions),3) or positions.shape[1:] != (2,):
        raise ValueError("Training arrival geometry shape mismatch")
    distance = np.linalg.norm(positions[:,None,:]-SENSORS[None,:,:], axis=2)
    differences = distance[:,1:]-distance[:,[0]]
    design = np.zeros((2*len(positions),3))
    design[:,0] = differences.ravel()
    design[0::2,1] = 1
    design[1::2,2] = 1
    response = (times[:,1:]-times[:,[0]]).ravel()
    fit = lsq_linear(design*1e6, response*1e6,
                     bounds=([1/7000,-.001,-.001],[1/500,.001,.001]))
    if not fit.success or not np.isfinite(fit.x).all():
        raise RuntimeError("TDoA calibration did not converge")
    return {"inverse_speed_s_per_m": float(fit.x[0]), "effective_speed_m_s": float(1/fit.x[0]),
            "relative_sensor_offsets_s": fit.x[1:].tolist(),
            "training_difference_rmse_us": float(np.sqrt(np.mean((design@fit.x-response)**2))*1e6),
            "speed_at_bound": bool(np.isclose(fit.x[0],1/500) or np.isclose(fit.x[0],1/7000))}


def localize_tdoa(times: np.ndarray, calibration: dict) -> np.ndarray:
    axis = np.linspace(0,1,201)
    yy,xx = np.meshgrid(axis,axis,indexing="ij")
    grid = np.column_stack([xx.ravel(),yy.ravel()])
    d = np.linalg.norm(grid[:,None,:]-SENSORS[None,:,:],axis=2)
    expected = (d[:,1:]-d[:,[0]])*calibration["inverse_speed_s_per_m"]+calibration["relative_sensor_offsets_s"]
    target = np.asarray(times)[1:]-times[0]
    return grid[int(np.argmin(np.sum((expected-target)**2,axis=1)))].copy()


def evaluate_fold(features: np.ndarray, positions: np.ndarray, held_out: int) -> dict:
    if not 0 <= held_out < len(positions) or len(positions) < 4:
        raise ValueError("Position holdout is outside the supported dataset")
    train = np.flatnonzero(np.arange(len(positions)) != held_out)
    if np.any(np.all(positions[train] == positions[held_out],axis=1)):
        raise ValueError("A held-out source position leaked into training")
    flat = features.reshape(len(features),-1)
    predictions = {"train_centroid": positions[train].mean(axis=0).tolist()}
    scalers = {}
    for k in (1,3):
        model = make_pipeline(StandardScaler(), KNeighborsRegressor(n_neighbors=k,weights="distance"))
        model.fit(flat[train],positions[train])
        predictions[f"knn_{k}"] = model.predict(flat[held_out:held_out+1])[0].tolist()
        scalers[f"knn_{k}"] = model[0].mean_.tolist()
    calibration = train_tdoa(features[train,:,1],positions[train])
    predictions["calibrated_tdoa_q05"] = localize_tdoa(features[held_out,:,1],calibration).tolist()
    return {"held_out_index": held_out,"train_indices": train.tolist(),"test_indices":[held_out],
            "truth_m": positions[held_out].tolist(),"predictions_m":predictions,
            "train_scaler_means":scalers,"tdoa_calibration":calibration,
            "errors_mm":{p:float(np.linalg.norm(np.asarray(x)-positions[held_out])*1000)
                         for p,x in predictions.items()}}


def run_study() -> dict:
    before = fingerprints()
    started = perf_counter()
    X,y,provenance = load_measured()
    folds = [evaluate_fold(X,y,i) for i in range(len(y))]
    summary = {}
    for policy in POLICIES:
        errors = np.array([f["errors_mm"][policy] for f in folds])
        summary[policy] = {"attempted_positions":len(y),"completed_positions":len(folds),
            "mean_error_mm":float(errors.mean()),"median_error_mm":float(np.median(errors)),
            "rmse_mm":float(np.sqrt(np.mean(errors**2))),
            **{f"success_within_{radius}_mm":float(np.mean(errors <= radius)) for radius in (20,50,100)}}
    after = fingerprints()
    return {"metadata":{"evidence_source":"measured_source_localization_reanalysis",
        "doi":"10.5281/zenodo.10875042","license":"CC-BY-4.0","independent_specimens":1,
        "position_records":9,"simultaneous_channels_per_record":3,"sample_rate_hz":2000000,
        "pretrigger_samples":1500,"source_frequency_hz":250000,"feature_names":list(FEATURE_NAMES),
        "protocol":"docs/MEASURED_IMPACT_VALIDATION_PROTOCOL.md","source_sha256_before":before,
        "source_sha256_after":after,"source_changed_during_run":before != after,
        "run_elapsed_s":perf_counter()-started,"evaluation":"leave_one_complete_source_position_out",
        "limitations":["previously_seen_record_reanalysis_not_new_unseen_validation",
            "one_plate_nine_positions_no_independent_repeat_axis","transient_source_not_persistent_hidden_defect",
            "operator_lowfrequency_apparatus_not_validated","no_specimen_generalization_intervals",
            "TDoA_energy_picker_and_isotropic_speed_are_approximations","units_from_record_are_not_host_normalized"]},
        "source_files":provenance,"summary":summary,"folds":folds,
        "paired_descriptive_advantage_mm":{p:float(np.mean([f["errors_mm"]["train_centroid"]-f["errors_mm"][p] for f in folds]))
                                            for p in POLICIES[1:]}}


if __name__ == "__main__":
    output = ROOT/"research_results/measured_impact_validation_2026_10_08.json"
    if output.exists():
        raise SystemExit("Final evidence exists; preserve it instead of overwriting")
    result = run_study()
    output.write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    print(json.dumps({"output":str(output),"summary":result["summary"],
                      "source_changed":result["metadata"]["source_changed_during_run"]},indent=2))
