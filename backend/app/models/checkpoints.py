"""Bounded, pickle-free persistence for the fixed forward-surrogate architecture.

Legacy torch/pickle checkpoints are deliberately not deserialized. Retrain with
the current trainer; no automatic conversion executes a legacy pickle.
"""
from __future__ import annotations

from hashlib import sha256
import io
import json
from pathlib import Path
import zipfile

import numpy as np
import torch

from backend.app.models.surrogate import ForwardSurrogate
from backend.app.replay.safe_io import load_bounded_npy, read_bounded, strict_json_loads, validate_archive

FORMAT = "argus-forward-npz-v1"
MAX_CHECKPOINT_BYTES = 16 * 1024 * 1024
NORMALIZERS = ("input_mean", "input_std", "target_mean", "target_std")


def load_forward_dataset(source: str | Path) -> tuple[np.ndarray, np.ndarray, dict]:
    """Preflight training matrices before allocation; metadata stays JSON."""
    content = read_bounded(Path(source))
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            validate_archive(archive, maximum_members=16)
            required = {'inputs.npy', 'targets.npy', 'metadata.npy'}
            if not required <= set(archive.namelist()):
                raise ValueError('Training bank requires inputs, targets, and JSON metadata')
            x = load_bounded_npy(archive.read('inputs.npy'), maximum_elements=5_000_000, allowed_ndim=(2,))
            y = load_bounded_npy(archive.read('targets.npy'), maximum_elements=5_000_000, allowed_ndim=(2,))
            m = load_bounded_npy(archive.read('metadata.npy'), maximum_elements=1, allowed_ndim=(0,), allowed_kinds='US')
            metadata = strict_json_loads(str(m.item()), maximum_nodes=500_000)
            if (x.shape[0] != y.shape[0] or not 1 <= x.shape[1] <= 512 or not 1 <= y.shape[1] <= 512
                    or not np.isfinite(x).all() or not np.isfinite(y).all() or not isinstance(metadata, dict)):
                raise ValueError('Training matrices must be bounded finite aligned observations')
            return x.astype(np.float32), y.astype(np.float32), metadata
    except (zipfile.BadZipFile, KeyError, TypeError) as exc:
        raise ValueError('Invalid training data bank') from exc


def _dimensions(value: dict) -> tuple[int, int]:
    dimensions = (value.get("input_size"), value.get("output_size"))
    if any(isinstance(v, bool) or not isinstance(v, int) or not 1 <= v <= 512 for v in dimensions):
        raise ValueError("Checkpoint dimensions must be bounded integers")
    return dimensions


def save_forward_checkpoint(checkpoint: dict, destination: str | Path) -> None:
    input_size, output_size = _dimensions(checkpoint)
    expected = ForwardSurrogate(input_size, output_size).state_dict()
    if set(checkpoint["model_state"]) != set(expected):
        raise ValueError("Checkpoint state does not match the supported surrogate")
    arrays = {}
    for key, template in expected.items():
        tensor = checkpoint["model_state"][key]
        value = tensor.detach().cpu().numpy()
        if value.shape != tuple(template.shape) or not np.isfinite(value).all():
            raise ValueError("Checkpoint weights must have supported finite shapes")
        arrays[f"weights/{key}.npy"] = value.astype(np.float32)
    for key in NORMALIZERS:
        value = np.asarray(checkpoint[key], dtype=np.float32)
        size = input_size if key.startswith("input") else output_size
        if value.shape != (size,) or not np.isfinite(value).all() or (key.endswith("std") and np.any(value <= 0)):
            raise ValueError("Checkpoint normalization must be finite and have positive scales")
        arrays[f"normalizers/{key}.npy"] = value
    content = {}
    for name, value in arrays.items():
        buffer = io.BytesIO()
        np.save(buffer, value, allow_pickle=False)
        content[name] = buffer.getvalue()
    manifest = {"format": FORMAT, "input_size": input_size, "output_size": output_size,
                "metadata": checkpoint["metadata"],
                "sha256": {name: sha256(value).hexdigest() for name, value in content.items()}}
    encoded = json.dumps(manifest, allow_nan=False, ensure_ascii=False).encode("utf-8")
    strict_json_loads(encoded, maximum_bytes=2 * 1024 * 1024, maximum_nodes=50_000)
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("wb") as output, zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", encoded)
        for name, value in content.items():
            archive.writestr(name, value)


def load_forward_checkpoint(source: str | Path) -> dict:
    content = read_bounded(Path(source), maximum=MAX_CHECKPOINT_BYTES)
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            validate_archive(archive, maximum_members=32, maximum_bytes=MAX_CHECKPOINT_BYTES)
            if "manifest.json" not in archive.namelist():
                raise ValueError("Legacy pickle checkpoint refused; retrain using the current pickle-free trainer")
            manifest = strict_json_loads(archive.read("manifest.json"), maximum_bytes=2*1024*1024, maximum_nodes=50_000)
            if not isinstance(manifest, dict) or manifest.get("format") != FORMAT:
                raise ValueError("Unsupported checkpoint format")
            input_size, output_size = _dimensions(manifest)
            expected = ForwardSurrogate(input_size, output_size).state_dict()
            names = {f"weights/{key}.npy" for key in expected} | {f"normalizers/{key}.npy" for key in NORMALIZERS}
            if set(archive.namelist()) != names | {"manifest.json"} or set(manifest.get("sha256", {})) != names:
                raise ValueError("Checkpoint members do not match the supported model contract")
            arrays = {}
            for name in names:
                member = archive.read(name)
                if sha256(member).hexdigest() != manifest["sha256"][name]:
                    raise ValueError("Checkpoint member hash mismatch")
                value = load_bounded_npy(member, maximum_elements=100_000, allowed_ndim=(1,2), allowed_kinds="f")
                if not np.isfinite(value).all():
                    raise ValueError("Checkpoint arrays must be finite")
                arrays[name] = value.astype(np.float32)
            state = {}
            for key, template in expected.items():
                value = arrays[f"weights/{key}.npy"]
                if value.shape != tuple(template.shape):
                    raise ValueError("Checkpoint weight shape mismatch")
                state[key] = torch.from_numpy(value.copy())
            result = {"input_size": input_size, "output_size": output_size, "model_state": state,
                      "metadata": manifest.get("metadata")}
            if not isinstance(result["metadata"], dict):
                raise ValueError("Checkpoint metadata must be an object")
            for key in NORMALIZERS:
                value = arrays[f"normalizers/{key}.npy"]
                size = input_size if key.startswith("input") else output_size
                if value.shape != (size,) or (key.endswith("std") and np.any(value <= 0)):
                    raise ValueError("Checkpoint normalization shape/scale mismatch")
                result[key] = value
            return result
    except (zipfile.BadZipFile, KeyError, TypeError, AttributeError) as exc:
        raise ValueError("Invalid or legacy pickle checkpoint; use the current pickle-free trainer") from exc
