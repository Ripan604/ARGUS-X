from __future__ import annotations

from abc import ABC, abstractmethod
from copy import deepcopy
from dataclasses import dataclass
import io
import json
from pathlib import Path
import zipfile

import numpy as np

from backend.app.models.domain import Defect, Experiment
from backend.app.replay.safe_io import (
    MAX_ARTIFACT_BYTES, MAX_BANK_ACTIONS, MAX_JSON_BYTES, MAX_SIGNAL_SAMPLES,
    load_bounded_npy, read_bounded, strict_json_loads, validate_archive, validate_signal,
)


def action_key(action: Experiment | dict) -> str:
    payload = action.to_dict() if isinstance(action, Experiment) else action
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _validate_action(action: dict) -> dict:
    try:
        experiment = Experiment(**action)
    except (TypeError, ValueError) as exc:
        raise ValueError("Invalid response-bank experiment") from exc
    if (not 0.005 <= experiment.duration_s <= 1.0 or experiment.frequency_end_hz > 192_000
            or isinstance(experiment.code_length, bool) or not isinstance(experiment.code_length, int)
            or experiment.code_length > 4_096 or len(experiment.spectral_notches_hz) > 64
            or (experiment.phase_code is not None and
                (not isinstance(experiment.phase_code, str) or len(experiment.phase_code) > 4_096))):
        raise ValueError("Response-bank experiment exceeds supported bounds")
    if experiment.sample_rate_hz is not None:
        _validate_rate(experiment.sample_rate_hz)
    return experiment.to_dict()


def _validate_rate(value) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 1_000 <= value <= 384_000:
        raise ValueError("Response-bank sample rate is outside supported bounds")
    return value


def _validate_metadata(metadata: dict) -> dict:
    if not isinstance(metadata, dict):
        raise ValueError("Response-bank metadata must be an object")
    # Operational blinding includes metadata: evaluation labels must remain in
    # the separate truth field, rather than leaking into planner-facing data.
    validated = strict_json_loads(json.dumps(metadata, allow_nan=False))
    stack = [validated]
    while stack:
        item = stack.pop()
        if isinstance(item, dict):
            if any(str(key).lower() in {"truth", "ground_truth", "hidden_truth", "sealed_truth", "revealed_truth"} for key in item):
                raise ValueError("Ground truth must not appear in response-bank metadata")
            stack.extend(item.values())
        elif isinstance(item, (list, tuple)):
            stack.extend(item)
    if "sample_rate" in validated:
        _validate_rate(validated["sample_rate"])
    if "sample_rates" in validated:
        if not isinstance(validated["sample_rates"], dict):
            raise ValueError("Response-bank sample_rates must be an object")
        for rate in validated["sample_rates"].values():
            _validate_rate(rate)
    if "action_types" in validated:
        if not isinstance(validated["action_types"], dict) or any(
                kind not in {"diagnostic", "calibration"} for kind in validated["action_types"].values()):
            raise ValueError("Response-bank action types are invalid")
    calibration_types = validated.get("calibration_types", {})
    if not isinstance(calibration_types, dict) or any(kind != "direct_path" for kind in calibration_types.values()):
        raise ValueError("Response-bank calibration types are invalid")
    if any(kind == "calibration" and calibration_types.get(key) != "direct_path"
           for key, kind in validated.get("action_types", {}).items()):
        raise ValueError("Replay calibration requires an explicitly labelled direct-path reference")
    return validated


def _dataset_path(root: Path, value: str) -> Path:
    if not isinstance(value, str) or not value or Path(value).is_absolute():
        raise ValueError("Response-bank paths must be relative to the dataset directory")
    path = (root / value).resolve()
    if not path.is_relative_to(root.resolve()) or path == root.resolve():
        raise ValueError("Signal path escapes the dataset directory")
    return path


def _load_npz(path: Path, expected: set[str]) -> dict[str, bytes]:
    try:
        with zipfile.ZipFile(io.BytesIO(read_bounded(path))) as archive:
            validate_archive(archive, maximum_members=len(expected))
            if set(archive.namelist()) != expected:
                raise ValueError("Response-bank NumPy members do not match its schema")
            return {name: archive.read(name) for name in expected}
    except (zipfile.BadZipFile, RuntimeError, NotImplementedError) as exc:
        raise ValueError("Invalid response-bank NumPy archive") from exc


def _json_array(content: bytes):
    array = load_bounded_npy(content, maximum_elements=1, allowed_ndim=(0,), allowed_kinds="US")
    return strict_json_loads(array.item())


class CounterfactualDataset(ABC):
    """Sealed response-bank contract. Truth is unavailable during execution."""

    def __init__(self) -> None:
        self._evaluation_unsealed = False

    @abstractmethod
    def list_available_actions(self) -> list[dict]: ...

    @abstractmethod
    def get_observation(self, action: Experiment | dict) -> np.ndarray: ...

    @abstractmethod
    def get_metadata(self) -> dict: ...

    def get_hidden_truth(self) -> dict:
        if not self._evaluation_unsealed:
            raise PermissionError("Ground truth is sealed until evaluation is explicitly ended")
        return deepcopy(self._truth())

    def end_blind_evaluation(self) -> dict:
        self._evaluation_unsealed = True
        return deepcopy(self._truth())

    @property
    def truth_is_sealed(self) -> bool:
        return not self._evaluation_unsealed

    @abstractmethod
    def _truth(self) -> dict: ...


@dataclass
class InMemoryCounterfactualDataset(CounterfactualDataset):
    observations: dict[str, np.ndarray]
    actions: list[dict]
    truth: dict
    metadata: dict

    def __post_init__(self) -> None:
        CounterfactualDataset.__init__(self)
        if not isinstance(self.actions, list) or not 1 <= len(self.actions) <= MAX_BANK_ACTIONS:
            raise ValueError("Response-bank action count must be between 1 and 1000")
        input_keys = [action_key(action) for action in self.actions]
        actions = [_validate_action(action) for action in self.actions]
        keys = [action_key(action) for action in actions]
        if len(set(keys)) != len(keys):
            raise ValueError("Duplicate action in response bank; use separate replicate manifests")
        if not isinstance(self.observations, dict) or set(self.observations) != set(input_keys):
            raise ValueError("Response-bank actions and observations must match exactly")
        observations = {key: validate_signal(self.observations[input_key]) for key, input_key in zip(keys, input_keys)}
        if sum(array.nbytes for array in observations.values()) > MAX_ARTIFACT_BYTES:
            raise ValueError("Expanded response bank exceeds the 100 MB limit")
        if not isinstance(self.truth, dict):
            raise ValueError("Response-bank truth must be an object")
        if self.truth:
            try:
                Defect(**self.truth)
            except (TypeError, ValueError) as exc:
                raise ValueError("Response-bank truth is invalid") from exc
        self.actions, self.observations = actions, observations
        self.truth = deepcopy(self.truth)
        self.metadata = _validate_metadata(self.metadata)
        if any(set(self.metadata.get(field, {})) - set(keys) for field in ("sample_rates", "action_types", "calibration_types")):
            raise ValueError("Response-bank metadata refers to unavailable actions")

    def list_available_actions(self) -> list[dict]:
        return deepcopy(self.actions)

    def get_observation(self, action: Experiment | dict) -> np.ndarray:
        key = action_key(action)
        if key not in self.observations:
            raise KeyError("The selected action is not available in this counterfactual bank")
        return np.asarray(self.observations[key], dtype=np.float32).copy()

    def get_metadata(self) -> dict:
        return {**deepcopy(self.metadata), "truth_sealed": self.truth_is_sealed}

    def _truth(self) -> dict:
        return deepcopy(self.truth)


class NPZCounterfactualDataset(InMemoryCounterfactualDataset):
    def __init__(self, path: str | Path) -> None:
        source = Path(path)
        payload = _load_npz(source, {"actions_json.npy", "signals.npy", "truth_json.npy", "metadata_json.npy"})
        actions = _json_array(payload["actions_json.npy"])
        if not isinstance(actions, list) or not 1 <= len(actions) <= MAX_BANK_ACTIONS:
            raise ValueError("Response-bank action count must be between 1 and 1000")
        signals = load_bounded_npy(payload["signals.npy"], maximum_elements=MAX_ARTIFACT_BYTES // 4, allowed_ndim=(2,))
        truth = _json_array(payload["truth_json.npy"])
        metadata = _json_array(payload["metadata_json.npy"])
        if not isinstance(metadata, dict):
            raise ValueError("Response-bank metadata must be an object")
        if len(actions) != len(signals):
            raise ValueError("Response-bank action and signal counts must match")
        observations = {action_key(action): signal for action, signal in zip(actions, signals)}
        super().__init__(observations, actions, truth, {**metadata, "source_path": str(source)})


class CSVCounterfactualDataset(InMemoryCounterfactualDataset):
    """CSV adapter for rows containing action_json and signal_npz_path."""

    def __init__(self, manifest_path: str | Path) -> None:
        import csv

        manifest = Path(manifest_path)
        actions, observations = [], {}
        truth, metadata = {}, {"format": "csv_manifest"}
        total_bytes = 0
        with io.StringIO(read_bounded(manifest, MAX_JSON_BYTES).decode("utf-8"), newline="") as handle:
            for row in csv.DictReader(handle):
                if len(actions) >= MAX_BANK_ACTIONS or not {"action_json", "signal_path"} <= set(row):
                    raise ValueError("CSV response bank has an invalid schema or too many actions")
                action = _validate_action(strict_json_loads(row["action_json"]))
                signal_path = _dataset_path(manifest.parent, row["signal_path"])
                payload = _load_npz(signal_path, {"signal.npy"})
                signal = load_bounded_npy(payload["signal.npy"])
                total_bytes += signal.nbytes
                if total_bytes > MAX_ARTIFACT_BYTES:
                    raise ValueError("Expanded response bank exceeds the 100 MB limit")
                if action_key(action) in observations:
                    raise ValueError("Duplicate action in response bank")
                actions.append(action)
                observations[action_key(action)] = np.asarray(signal, dtype=np.float32)
                if row.get("truth_json"):
                    row_truth = strict_json_loads(row["truth_json"])
                    if truth and truth != row_truth:
                        raise ValueError("CSV response bank contains inconsistent truth labels")
                    truth = row_truth
        super().__init__(observations, actions, truth, metadata)


class WAVCollectionCounterfactualDataset(InMemoryCounterfactualDataset):
    """Directory/JSON adapter for measured or synthetic WAV response banks.

    The manifest contains ``actions`` entries with ``experiment`` and ``wav``.
    Truth is stored once at manifest level and remains sealed by the base class.
    Integer WAV samples are normalized to [-1, 1]; floating-point WAVs are kept.
    """

    def __init__(self, manifest_path: str | Path) -> None:
        from scipy.io import wavfile

        manifest = Path(manifest_path).resolve()
        payload = strict_json_loads(read_bounded(manifest, MAX_JSON_BYTES))
        if not isinstance(payload, dict) or not isinstance(payload.get("actions"), list) or not 1 <= len(payload["actions"]) <= MAX_BANK_ACTIONS:
            raise ValueError("WAV manifest must contain between 1 and 1000 actions")
        root = manifest.parent
        actions: list[dict] = []
        observations: dict[str, np.ndarray] = {}
        sample_rates: dict[str, int] = {}
        action_types: dict[str, str] = {}
        calibration_types: dict[str, str] = {}
        total_bytes = 0
        for item in payload["actions"]:
            if not isinstance(item, dict) or not {"experiment", "wav"} <= set(item):
                raise ValueError("WAV manifest action is invalid")
            action = _validate_action(item["experiment"])
            wav_path = _dataset_path(root, item["wav"])
            # Passing a bounded in-memory stream also prevents a changed file
            # from growing between the size check and scipy's allocation.
            rate, signal = wavfile.read(io.BytesIO(read_bounded(wav_path, MAX_SIGNAL_SAMPLES * 16 + 65_536)))
            _validate_rate(int(rate))
            array = np.asarray(signal)
            if np.issubdtype(array.dtype, np.integer):
                info = np.iinfo(array.dtype)
                if info.min == 0:
                    midpoint = (info.max + 1) / 2
                    array = (array.astype(np.float64) - midpoint) / midpoint
                else:
                    array = array.astype(np.float64) / float(max(abs(info.min), info.max))
            else:
                array = array.astype(np.float64)
            if array.ndim == 2 and array.shape[1] in {1, 2}:
                array = array.mean(axis=1)
            array = validate_signal(array)
            total_bytes += array.nbytes
            if total_bytes > MAX_ARTIFACT_BYTES:
                raise ValueError("Expanded response bank exceeds the 100 MB limit")
            key = action_key(action)
            if key in observations:
                raise ValueError("Duplicate action in response bank; use separate replicate manifests")
            actions.append(action)
            observations[key] = array.astype(np.float32)
            sample_rates[key] = int(rate)
            kind = item.get("action_type", "diagnostic")
            if kind not in {"diagnostic", "calibration"}:
                raise ValueError("Response-bank action type must be diagnostic or calibration")
            if kind == "calibration" and item.get("calibration_type") != "direct_path":
                raise ValueError("Replay calibration requires an explicitly labelled direct-path reference")
            if kind == "calibration":
                calibration_types[key] = "direct_path"
            action_types[key] = kind
        if not actions:
            raise ValueError("WAV collection manifest contains no actions")
        source_metadata = payload.get("metadata", {})
        if not isinstance(source_metadata, dict):
            raise ValueError("Response-bank metadata must be an object")
        metadata = {
            **source_metadata,
            "format": "wav_collection",
            "manifest": str(manifest),
            "sample_rates": sample_rates,
            "action_types": action_types,
            "calibration_types": calibration_types,
            "evidence_source": payload.get("evidence_source", "user_imported"),
        }
        super().__init__(observations, actions, payload.get("truth", {}), metadata)
