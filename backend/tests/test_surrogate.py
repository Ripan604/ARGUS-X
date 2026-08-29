from pathlib import Path

import numpy as np
import torch

from backend.app.models.surrogate import ForwardSurrogate


def test_reference_surrogate_checkpoint_loads_and_predicts():
    checkpoint_path = Path(__file__).resolve().parents[2] / "models" / "forward_surrogate.pt"
    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    model = ForwardSurrogate(checkpoint["input_size"], checkpoint["output_size"])
    model.load_state_dict(checkpoint["model_state"])
    model.eval()
    standardized_input = torch.zeros((2, checkpoint["input_size"]), dtype=torch.float32)
    with torch.no_grad():
        prediction = model(standardized_input).numpy()
    physical_prediction = prediction * np.asarray(checkpoint["target_std"]) + np.asarray(checkpoint["target_mean"])
    assert physical_prediction.shape == (2, checkpoint["output_size"])
    assert np.all(np.isfinite(physical_prediction))
    assert checkpoint["metadata"]["held_out_metrics"]["mean_feature_r2"] > 0
