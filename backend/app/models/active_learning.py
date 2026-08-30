from __future__ import annotations

from hashlib import sha256

import numpy as np
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler


def _fit_ensemble(x: np.ndarray, y: np.ndarray, seed: int, members: int = 3) -> tuple[list[MLPRegressor], StandardScaler, StandardScaler]:
    x_scaler, y_scaler = StandardScaler(), StandardScaler()
    x_normalized = x_scaler.fit_transform(x)
    y_normalized = y_scaler.fit_transform(y)
    models = []
    for index in range(members):
        model = MLPRegressor(
            hidden_layer_sizes=(48, 48), activation="relu", solver="adam",
            random_state=seed + index, max_iter=140, early_stopping=True,
            validation_fraction=0.18, n_iter_no_change=12, learning_rate_init=0.002,
        )
        model.fit(x_normalized, y_normalized)
        models.append(model)
    return models, x_scaler, y_scaler


def _predict(models: list[MLPRegressor], x_scaler: StandardScaler, y_scaler: StandardScaler, x: np.ndarray) -> np.ndarray:
    normalized = x_scaler.transform(x)
    return np.stack([y_scaler.inverse_transform(model.predict(normalized)) for model in models])


def run_active_learning_study(
    *, seed: int = 431, samples: int = 360, query_count: int = 36,
    progress=None, cancelled=None,
) -> dict:
    """Run a bounded CPU pool-based surrogate active-learning experiment.

    Candidate physics outputs act as a sealed oracle: selection uses only input
    state/action vectors and ensemble disagreement, never candidate labels.
    """

    if samples < 180:
        raise ValueError("Active-learning study requires at least 180 physics samples")
    from scripts.generate_dataset import generate

    inputs, targets, metadata = generate(samples, seed)
    rng = np.random.default_rng(seed)
    order = rng.permutation(samples)
    initial_count = max(72, samples // 4)
    test_count = max(60, samples // 4)
    initial = order[:initial_count]
    test = order[-test_count:]
    pool = order[initial_count:-test_count]
    query_count = min(max(1, query_count), len(pool))
    if progress:
        progress(0.25)
    if cancelled and cancelled():
        return {"cancelled": True, "stage": "before_initial_fit"}

    initial_models, x_scaler, y_scaler = _fit_ensemble(inputs[initial], targets[initial], seed)
    initial_prediction = _predict(initial_models, x_scaler, y_scaler, inputs[test]).mean(axis=0)
    initial_mae = float(np.mean(np.abs(initial_prediction - targets[test])))
    pool_prediction = _predict(initial_models, x_scaler, y_scaler, inputs[pool])
    disagreement = np.mean(np.std(pool_prediction, axis=0), axis=1)
    selected_order = np.argsort(disagreement)[-query_count:][::-1]
    selected = pool[selected_order]
    if progress:
        progress(0.62)
    if cancelled and cancelled():
        return {"cancelled": True, "stage": "before_retrain", "initial_mae": initial_mae}

    augmented = np.concatenate([initial, selected])
    final_models, final_x_scaler, final_y_scaler = _fit_ensemble(inputs[augmented], targets[augmented], seed + 20)
    final_prediction = _predict(final_models, final_x_scaler, final_y_scaler, inputs[test]).mean(axis=0)
    final_mae = float(np.mean(np.abs(final_prediction - targets[test])))
    if progress:
        progress(0.98)
    return {
        "metadata": {
            "evidence_source": "simulated_physics_oracle", "seed": seed,
            "ensemble": "3 x sklearn MLPRegressor(48,48)",
            "selection": "mean ensemble predictive standard deviation",
            "truth_isolation": "candidate targets remained sealed until after selection",
        },
        "sample_counts": {"initial": len(initial), "queried": len(selected), "pool": len(pool), "test": len(test)},
        "initial_test_mae": initial_mae,
        "active_test_mae": final_mae,
        "relative_mae_change": (initial_mae - final_mae) / max(initial_mae, 1e-12),
        "improved": final_mae < initial_mae,
        "selected_disagreement": {
            "mean": float(np.mean(disagreement[selected_order])),
            "minimum": float(np.min(disagreement[selected_order])),
            "pool_mean": float(np.mean(disagreement)),
        },
        "training_dataset_hash": sha256(inputs[augmented].tobytes() + targets[augmented].tobytes()).hexdigest(),
        "feature_names": metadata["feature_names"],
    }

