"""Acquire fixed, previously unviewed OGW banks without inspecting wave responses.

Writes only open_guided_waves_confirmation. Original OGW evidence remains
byte-identical. HDF5 inspection is schema/conditions only, not a signal summary.
"""
from __future__ import annotations
import hashlib
import json
import math
import re
import sys
import zipfile
import zlib
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import requests
from scripts.download_open_guided_waves import BoundedRemoteZip, MAX_MEMBER, inspect_hdf5, safe_member

OLD = ROOT / "datasets/external/open_guided_waves"
DESTINATION = ROOT / "datasets/external/open_guided_waves_confirmation"
PROTECTED = [
    "scripts/download_open_guided_waves.py", "scripts/test_download_open_guided_waves.py",
    "scripts/validate_measured_guided_waves.py", "backend/app/evaluation/measured_guided_waves.py",
    "backend/tests/test_measured_guided_waves.py", "docs/MEASURED_GUIDED_WAVE_PROTOCOL.md",
    "docs/OPEN_GUIDED_WAVES_SOURCE_AUDIT.md", "research_results/measured_guided_wave_validation_2026_10_08.json",
    "research_results/measured_guided_wave_validation_2026_10_08_preflight_pilot.json",
    "frontend/public/research/measured-data-summary.json",
]
ARTICLES = {"healthy": 8108297, "D04": 8107889, "D12": 8107886, "D16": 8107883, "D24": 8107880}


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""): hasher.update(block)
    return hasher.hexdigest()


def write_json(path: Path, value) -> None:
    if not path.resolve().is_relative_to(DESTINATION.resolve()): raise ValueError("Output escaped confirmation directory")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def protected_hashes() -> dict:
    paths = {ROOT / relative for relative in PROTECTED if (ROOT / relative).is_file()}
    paths.update(path for path in OLD.rglob("*") if path.is_file() and "__pycache__" not in path.parts)
    report = json.loads((ROOT / "research_results/measured_guided_wave_validation_2026_10_08.json").read_text(encoding="utf-8"))
    paths.update(ROOT / name for name in report["metadata"]["source_sha256_after"])
    return {path.relative_to(ROOT).as_posix(): digest(path) for path in sorted(paths)}


def frozen_selection(state: str) -> list[dict]:
    if state == "healthy":
        calibration = [{"index": index, "role": "healthy_trajectory_calibration", "thermal_cycle": 1,
                        "ramp": "cooling", "nominal_temperature_c": 60 - .5 * (index - 80)}
                       for index in range(84, 157, 4)]
        tests = [{"index": index, "role": "confirmation_test", "thermal_cycle": 2,
                  "ramp": "ascending", "nominal_temperature_c": temperature}
                 for index, temperature in ((181, 30), (221, 50))]
        return calibration + tests
    return [{"index": index, "role": "confirmation_test", "thermal_cycle": 1,
             "ramp": "ascending", "nominal_temperature_c": temperature}
            for index, temperature in ((20, 30), (60, 50))]


def main() -> None:
    DESTINATION.mkdir(parents=True, exist_ok=True)
    previous = DESTINATION / "argus_manifest.json"
    protected = protected_hashes()
    old_manifest = json.loads((OLD / "argus_manifest.json").read_text(encoding="utf-8"))
    old_members = {(record["archive_url"], record["member_path"]) for record in old_manifest["files"]}
    budget = {"received_bytes": 0, "maximum_bytes": 900 * 1024 * 1024}
    manifest = {"schema_version": 1, "dataset": "OGW #2 separate calibration and confirmation acquisition",
                "date": "2026-10-08", "acquired_at_utc": datetime.now(timezone.utc).isoformat(),
                "data_license": "CC0", "license_url": "https://creativecommons.org/publicdomain/zero/1.0/",
                "collection_doi": "10.6084/m9.figshare.c.4488089.v1", "paper_doi": "10.1038/s41597-019-0208-1",
                "native_sampling_frequency_hz": 10000000, "excitation_frequency_hz": 40000,
                "recorded_unordered_paths": 66, "independent_specimens": 1,
                "planned_healthy_calibration_temperature_blocks": 19, "planned_confirmation_test_banks": 10,
                "selection_fixed_before_signal_analysis": True, "waveform_summary_or_result_computed": False,
                "selection": {state: frozen_selection(state) for state in ARTICLES},
                "old_evidence_sha256_before": protected, "sources": [], "files": [], "failures": [],
                "completed": False, "whole_archive_md5_verified": False}
    if previous.exists(): manifest["files"] = json.loads(previous.read_text(encoding="utf-8")).get("files", [])
    session = requests.Session()
    try:
        # Preserve original provenance and geometry as exact copies in the NEW directory.
        for name in ("geometry.json", "primary_article.xml"):
            destination = DESTINATION / "metadata" / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes((OLD / "metadata" / name).read_bytes())
        (DESTINATION / "LICENSE_AND_CITATION.txt").write_bytes((OLD / "LICENSE_AND_CITATION.txt").read_bytes())
        for state, article in ARTICLES.items():
            metadata_path = OLD / "metadata" / f"figshare_{article}.json"
            original = json.loads(metadata_path.read_text(encoding="utf-8"))
            if original["license"]["name"] != "CC0": raise ValueError("Original data license changed")
            archive = original["files"][0]
            (DESTINATION / "metadata" / f"figshare_{article}.json").write_bytes(metadata_path.read_bytes())
            manifest["sources"].append({"state": state, "article_url": f"https://api.figshare.com/v2/articles/{article}",
                                        "publisher_metadata_sha256": digest(metadata_path), "archive": archive})
            print(f"Index {state}; fixed selection {len(frozen_selection(state))} banks", flush=True)
            remote = BoundedRemoteZip(session, archive["download_url"], archive["size"], budget)
            with zipfile.ZipFile(remote) as zipped:
                if len(zipped.infolist()) > 100000: raise ValueError("Unbounded archive index")
                candidates = sorted([info for info in zipped.infolist() if re.search(r"(?:_|\s)f40kHz\.h5$", info.filename, re.I)],
                                    key=lambda info: info.filename)
                if len(candidates) != (322 if state == "healthy" else 161): raise ValueError("Published thermal schedule count changed")
                for selection in frozen_selection(state):
                    info = candidates[selection["index"]]
                    if (archive["download_url"], info.filename) in old_members:
                        raise ValueError("Confirmation selection overlaps an existing waveform bank")
                    safe_member(info)
                    timestamp = next(part for part in PurePosixPath(info.filename).parts if re.fullmatch(r"\d{8}T\d{6}", part))
                    path = DESTINATION / "numeric" / state / timestamp / PurePosixPath(info.filename).name
                    if not path.resolve().is_relative_to(DESTINATION.resolve()): raise ValueError("Numeric output escaped directory")
                    path.parent.mkdir(parents=True, exist_ok=True)
                    if not path.exists():
                        with zipped.open(info) as source: raw = source.read(MAX_MEMBER + 1)
                        if len(raw) != info.file_size: raise ValueError("Incomplete original numeric member")
                        temporary = path.with_suffix(".h5.tmp"); temporary.write_bytes(raw); temporary.replace(path)
                    if path.stat().st_size > MAX_MEMBER: raise ValueError("Existing file exceeds allocation bounds")
                    raw = path.read_bytes()
                    if len(raw) != info.file_size or zlib.crc32(raw) & 0xffffffff != info.CRC:
                        raise ValueError("Original member CRC/size mismatch")
                    # Old inspection helper reads only small numeric metadata and shapes.
                    schema = inspect_hdf5(path)
                    chamber = schema["datasets"]["CTC/Temperature"]["small_value"][0]
                    surface = schema["datasets"]["Temperature/values"]["small_value"]
                    if not math.isfinite(chamber) or abs(chamber - selection["nominal_temperature_c"]) > .25:
                        raise ValueError("Measured chamber condition conflicts with fixed nominal schedule")
                    if not all(math.isfinite(value) for value in surface): raise ValueError("Nonfinite temperature metadata")
                    for key in ("pitchcatch/catch", "pitchcatch/pitch"):
                        if schema["datasets"][key]["shape"] != [66, 13108] or schema["datasets"][key]["dtype"] != "float64":
                            raise ValueError("Native bank schema mismatch")
                    if schema["datasets"]["command/pitchcatch/sampling_frequency"]["small_value"] != [10000000.]:
                        raise ValueError("Native sampling frequency changed")
                    if schema["datasets"]["command/pitchcatch/signal_frequency"]["small_value"] != [40000.]:
                        raise ValueError("Native excitation frequency changed")
                    write_json(path.with_suffix(".schema.json"), schema)
                    record = {**selection, "state": state, "timestamp": timestamp, "chamber_temperature_c": chamber,
                              "surface_temperature_c": surface, "local_path": path.relative_to(ROOT).as_posix(),
                              "member_path": info.filename, "member_size": info.file_size, "member_crc32": f"{info.CRC:08x}",
                              "member_crc_verified": True, "sha256": hashlib.sha256(raw).hexdigest(),
                              "archive_url": archive["download_url"], "publisher_archive_md5": archive["computed_md5"],
                              "whole_archive_md5_verified": False, "waveform_summary_or_result_computed": False}
                    manifest["files"] = [item for item in manifest["files"] if item["local_path"] != record["local_path"]] + [record]
                    print(f"  {state} {selection['role']} {chamber:.1f} C: {timestamp}", flush=True)
                    write_json(previous, manifest)
        calibration = [record for record in manifest["files"] if record["role"] == "healthy_trajectory_calibration"]
        tests = [record for record in manifest["files"] if record["role"] == "confirmation_test"]
        if len(calibration) != 19 or len(tests) != 10 or len(manifest["files"]) != 29:
            raise ValueError("Incomplete fixed calibration/confirmation selection")
        after = protected_hashes()
        if after != protected: raise ValueError("Existing OGW evidence changed during new acquisition")
        manifest.update({"completed": True, "old_evidence_sha256_after": after, "old_evidence_changed": False,
                         "raw_numeric_bytes": sum(record["member_size"] for record in manifest["files"]),
                         "calibration_blocks": 19, "confirmation_test_banks": 10,
                         "new_script_sha256": digest(Path(__file__))})
    except Exception as error:
        manifest["failures"].append({"type": type(error).__name__, "message": str(error)})
        raise
    finally:
        after = protected_hashes()
        manifest["old_evidence_sha256_after"] = after
        manifest["old_evidence_changed"] = after != protected
        if manifest["old_evidence_changed"]:
            manifest["completed"] = False
            manifest["failures"].append({"type": "EvidenceChanged", "message": "Existing evidence differed from the pre-acquisition snapshot"})
        manifest["transfer_this_invocation"] = budget
        write_json(previous, manifest)
        session.close()


if __name__ == "__main__": main()
