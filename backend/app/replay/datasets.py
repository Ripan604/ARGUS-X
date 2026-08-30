from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
import json
from pathlib import Path

import numpy as np

from backend.app.models.domain import Experiment


def action_key(action: Experiment | dict) -> str:
    payload = action.to_dict() if isinstance(action, Experiment) else action
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


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
        return self._truth()

    def end_blind_evaluation(self) -> dict:
        self._evaluation_unsealed = True
        return self._truth()

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

    def list_available_actions(self) -> list[dict]:
        return self.actions

    def get_observation(self, action: Experiment | dict) -> np.ndarray:
        key = action_key(action)
        if key not in self.observations:
            raise KeyError("The selected action is not available in this counterfactual bank")
        return np.asarray(self.observations[key], dtype=np.float32).copy()

    def get_metadata(self) -> dict:
        return {**self.metadata, "truth_sealed": not self._evaluation_unsealed}

    def _truth(self) -> dict:
        return self.truth


class NPZCounterfactualDataset(InMemoryCounterfactualDataset):
    def __init__(self, path: str | Path) -> None:
        source = Path(path)
        with np.load(source, allow_pickle=False) as payload:
            actions = json.loads(str(payload["actions_json"]))
            signals = payload["signals"].astype(np.float32)
            truth = json.loads(str(payload["truth_json"]))
            metadata = json.loads(str(payload["metadata_json"]))
        observations = {action_key(action): signal for action, signal in zip(actions, signals)}
        super().__init__(observations, actions, truth, {**metadata, "source_path": str(source)})


class CSVCounterfactualDataset(InMemoryCounterfactualDataset):
    """CSV adapter for rows containing action_json and signal_npz_path."""

    def __init__(self, manifest_path: str | Path) -> None:
        import csv

        manifest = Path(manifest_path)
        actions, observations = [], {}
        truth, metadata = {}, {"format": "csv_manifest"}
        with manifest.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                action = json.loads(row["action_json"])
                signal_path = (manifest.parent / row["signal_path"]).resolve()
                if manifest.parent.resolve() not in signal_path.parents:
                    raise ValueError("Signal path escapes the dataset directory")
                signal = np.load(signal_path, allow_pickle=False)["signal"]
                actions.append(action)
                observations[action_key(action)] = np.asarray(signal, dtype=np.float32)
                if row.get("truth_json"):
                    truth = json.loads(row["truth_json"])
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
        payload = json.loads(manifest.read_text(encoding="utf-8"))
        root = manifest.parent
        actions: list[dict] = []
        observations: dict[str, np.ndarray] = {}
        sample_rates: dict[str, int] = {}
        for item in payload.get("actions", []):
            action = dict(item["experiment"])
            wav_path = (root / item["wav"]).resolve()
            if root != wav_path.parent and root not in wav_path.parents:
                raise ValueError("WAV path escapes the dataset directory")
            rate, signal = wavfile.read(wav_path)
            array = np.asarray(signal)
            if array.ndim == 2:
                array = array.astype(np.float64).mean(axis=1)
            if np.issubdtype(array.dtype, np.integer):
                limit = float(max(abs(np.iinfo(array.dtype).min), np.iinfo(array.dtype).max))
                array = array.astype(np.float32) / limit
            else:
                array = array.astype(np.float32)
            key = action_key(action)
            actions.append(action)
            observations[key] = np.nan_to_num(array, nan=0.0, posinf=1.0, neginf=-1.0)
            sample_rates[key] = int(rate)
        if not actions:
            raise ValueError("WAV collection manifest contains no actions")
        metadata = {
            **payload.get("metadata", {}),
            "format": "wav_collection",
            "manifest": str(manifest),
            "sample_rates": sample_rates,
            "evidence_source": payload.get("evidence_source", "user_imported"),
        }
        super().__init__(observations, actions, payload.get("truth", {}), metadata)
