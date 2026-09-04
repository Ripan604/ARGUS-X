from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

import numpy as np

from backend.app.core.config import ArgusConfig
from backend.app.models.domain import Experiment
from backend.app.services.engine import ArgusEngine


SCALES = {
    "tiny": {"scenarios": 2, "actions": 8},
    "demo": {"scenarios": 8, "actions": 20},
    "research": {"scenarios": 48, "actions": 48},
}


def _write_manifest(path: Path, manifest: dict) -> None:
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    temporary.replace(path)


def generate_counterfactual_bank(
    destination: str | Path,
    *,
    scale: str = "tiny",
    seed: int = 71,
    resume: bool = True,
    progress=None,
    cancelled=None,
) -> dict:
    if scale not in SCALES:
        raise ValueError(f"Unknown bank scale: {scale}")
    root = Path(destination)
    root.mkdir(parents=True, exist_ok=True)
    specification = SCALES[scale]
    manifest_path = root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if resume and manifest_path.exists() else {
        "schema_version": 1, "scale": scale, "seed": seed, "chunks": [], "completed_scenarios": [],
    }
    if manifest.get("schema_version") != 1 or manifest.get("scale") != scale or int(manifest.get("seed", -1)) != seed:
        raise ValueError("Existing response-bank manifest does not match the requested schema, scale, and seed")
    valid_chunks = []
    valid_completed: set[int] = set()
    for item in manifest.get("chunks", []):
        scenario = int(item.get("scenario", -1))
        chunk = (root / str(item.get("path", ""))).resolve()
        expected_name = f"scenario_{scenario:05d}.npz"
        if (
            0 <= scenario < specification["scenarios"]
            and chunk.parent == root.resolve()
            and chunk.name == expected_name
            and chunk.exists()
            and sha256(chunk.read_bytes()).hexdigest() == item.get("sha256")
        ):
            valid_chunks.append(item)
            valid_completed.add(scenario)
    manifest["chunks"] = valid_chunks
    manifest["completed_scenarios"] = sorted(valid_completed)
    completed = set(manifest.get("completed_scenarios", []))
    for scenario_index in range(specification["scenarios"]):
        if cancelled and cancelled():
            break
        if scenario_index in completed:
            continue
        scenario_seed = seed + scenario_index
        engine = ArgusEngine(
            config=ArgusConfig(candidate_count=min(24, specification["actions"]), max_experiments=4, seed=scenario_seed),
            seed=scenario_seed,
            preset="medium",
        )
        actions = engine.planner.generate_candidates(engine.belief.posterior, [], specification["actions"])
        signals = np.stack([engine.acquisition_simulator.simulate(engine.truth, action) for action in actions])
        metadata = {
            "scenario_index": scenario_index,
            "seed": scenario_seed,
            "sample_rate": engine.config.sample_rate,
            "evidence_source": "simulated",
            "material": engine.material.to_dict(),
        }
        chunk = root / f"scenario_{scenario_index:05d}.npz"
        np.savez_compressed(
            chunk,
            signals=signals,
            actions_json=json.dumps([action.to_dict() for action in actions]),
            truth_json=json.dumps(engine.truth.to_dict()),
            metadata_json=json.dumps(metadata),
        )
        digest = sha256(chunk.read_bytes()).hexdigest()
        manifest["chunks"].append({"scenario": scenario_index, "path": chunk.name, "sha256": digest})
        completed.add(scenario_index)
        manifest["completed_scenarios"] = sorted(completed)
        _write_manifest(manifest_path, manifest)
        if progress:
            progress(len(completed) / specification["scenarios"])
    manifest["complete"] = len(completed) == specification["scenarios"]
    _write_manifest(manifest_path, manifest)
    return manifest
