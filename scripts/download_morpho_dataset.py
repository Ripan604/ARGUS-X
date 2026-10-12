"""Download a pinned public numeric MORPHO subset after license verification.

Only the five publisher-listed files are downloaded. Author software and pickle
files are never executed or loaded. Raw data and checksums remain separate from
any derived experiment or defect-localization claim.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
RECORD_URL = "https://zenodo.org/api/records/20120070"
MAX_TOTAL_BYTES = 150_000_000
PINNED_FILES = {
    "LICENSE": (1753, "cf86807b65874fb042515656d49cb15e"),
    "README.md": (8272, "44318ce8b8ce896c8eea4b76ce33f76a"),
    "CITATION.cff": (2510, "669559c68a431a3ff340bd50735eac55"),
    "paper_labels.json": (227494, "06893020177e0be78a72abadce9a9951"),
    "morpho_50khz_full.h5": (97647899, "98ef387d8ed7ef583347ed020674129a"),
}


def _official_url(url: str) -> str:
    parts = urllib.parse.urlsplit(url)
    if parts.scheme != "https" or parts.netloc != "zenodo.org" or not parts.path.startswith("/api/records/20120070"):
        raise ValueError("Download metadata does not bind the pinned official record")
    return url


def _request(url: str):
    return urllib.request.urlopen(urllib.request.Request(_official_url(url),
        headers={"User-Agent": "ARGUS-public-measured-data-catalog/1.0"}), timeout=60)


def _digest(path: Path, algorithm: str) -> str:
    digest = hashlib.new(algorithm)
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024*1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_dataset(output: Path) -> dict:
    output = output.resolve()
    # Keep retained data inside the shared workspace by default and even when
    # a command-line destination is provided. No external trees are modified.
    if not output.is_relative_to(ROOT.resolve()):
        raise ValueError("Dataset destination must stay inside the ARGUS workspace")
    output.mkdir(parents=True, exist_ok=True)
    with _request(RECORD_URL) as response:
        record_bytes = response.read(1_000_001)
    if len(record_bytes) > 1_000_000:
        raise ValueError("Publisher metadata exceeded the declared bound")
    record = json.loads(record_bytes)
    metadata = record.get("metadata", {})
    if metadata.get("access_right") != "open" or metadata.get("license", {}).get("id") != "cc-by-4.0":
        raise ValueError("Open CC-BY-4.0 dataset license was not verified")
    if metadata.get("doi") != "10.5281/zenodo.20120070":
        raise ValueError("Dataset DOI changed from the pinned release")
    entries = {row["key"]: row for row in record["files"]}
    if set(entries) != set(PINNED_FILES):
        raise ValueError("Publisher file inventory changed; review the new release before downloading")
    for filename, (expected_size, expected_md5) in PINNED_FILES.items():
        entry = entries[filename]
        if entry["size"] != expected_size or entry["checksum"] != "md5:"+expected_md5:
            raise ValueError("Publisher file size/checksum differs from the pinned inventory")
        _official_url(entry["links"]["self"])
    if sum(value[0] for value in PINNED_FILES.values()) > MAX_TOTAL_BYTES:
        raise ValueError("Pinned data exceeds the approved download bound")
    retained = []
    # License is checked and retained before any raw numeric payload is fetched.
    for filename, (expected_size, expected_md5) in PINNED_FILES.items():
        destination = output / filename
        if destination.exists():
            if destination.stat().st_size != expected_size or _digest(destination, "md5") != expected_md5:
                raise ValueError("Existing dataset file does not match the pinned release; refusing overwrite")
            reused = True
        else:
            temporary = destination.with_name(destination.name+".part")
            count = 0
            digest = hashlib.md5()
            with _request(entries[filename]["links"]["self"]) as response, temporary.open("wb") as target:
                if int(response.headers.get("Content-Length", expected_size)) > expected_size:
                    raise ValueError("Publisher response exceeds the pinned file bound")
                while True:
                    chunk = response.read(min(1024*1024, expected_size-count+1))
                    if not chunk:
                        break
                    count += len(chunk)
                    if count > expected_size:
                        raise ValueError("Downloaded file exceeds the pinned byte count")
                    digest.update(chunk)
                    target.write(chunk)
            if count != expected_size or digest.hexdigest() != expected_md5:
                raise ValueError("Downloaded file failed official size/MD5 verification; no data is accepted")
            temporary.replace(destination)
            reused = False
        if filename == "LICENSE":
            license_text = destination.read_text(encoding="utf-8")
            if "Creative Commons Attribution 4.0 International" not in license_text or "CC BY 4.0" not in license_text:
                raise ValueError("Publisher license text does not match the API license declaration")
        retained.append({"filename": filename, "source_url": entries[filename]["links"]["self"],
                         "bytes": expected_size, "official_md5": expected_md5,
                         "sha256": _digest(destination, "sha256"), "reused_verified_file": reused})
        print(json.dumps({"retained": filename, "bytes": expected_size, "reused": reused}), flush=True)
    metadata_path = output / "zenodo_record_20120070.json"
    metadata_path.write_bytes(record_bytes)
    manifest = {"dataset_doi": metadata["doi"], "source_record_url": RECORD_URL,
                "retrieved_at_utc": datetime.now(timezone.utc).isoformat(), "license_id": "cc-by-4.0",
                "attribution_required": True, "also_cite_original_doi": "10.5281/zenodo.14627730",
                "publisher_metadata_sha256": hashlib.sha256(record_bytes).hexdigest(), "files": retained,
                "source_script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "label_scope": "operator_good_bad_signal_quality_not_defect_position_truth",
                "downloaded_software_executed": False, "pickle_loaded": False,
                "numeric_hdf5_inspection_pending": True}
    (output / "download_manifest.json").write_text(json.dumps(manifest, indent=2, allow_nan=False)+"\n", encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "datasets/external/morpho_50khz")
    args = parser.parse_args()
    result = download_dataset(args.output)
    print(json.dumps({"dataset_doi": result["dataset_doi"], "files": len(result["files"]),
                      "total_bytes": sum(f["bytes"] for f in result["files"]), "license": result["license_id"]}))


if __name__ == "__main__":
    main()
