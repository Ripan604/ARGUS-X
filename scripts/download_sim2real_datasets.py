from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from urllib.request import Request, urlopen
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
USER_AGENT = "ARGUS-sim2real-downloader/1.0"

TUD_ITEM_ID = "33756af4-eb6d-4156-8708-a41cbed33e7b"
TUD_API = f"https://tudatalib.ulb.tu-darmstadt.de/server/api/core/items/{TUD_ITEM_ID}"
TUD_DESTINATION = ROOT / "datasets" / "external" / "tud_gfrp_2026"
TUD_REQUIRED = {
    "README.md",
    "README_unaugmented_data.md",
    "README_raw_measurement_data.md",
    "unaugmented_data.zip",
}

AE_RECORD_ID = "10875042"
AE_API = f"https://zenodo.org/api/records/{AE_RECORD_ID}"
AE_DESTINATION = ROOT / "datasets" / "external" / "ae_impact_2024"


def request_json(url: str) -> dict:
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urlopen(request, timeout=60) as response:
        return json.load(response)


def file_md5(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.md5()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download(url: str, destination: Path, expected_size: int, expected_md5: str) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and destination.stat().st_size == expected_size:
        if file_md5(destination) == expected_md5:
            print(f"verified  {destination.name} ({expected_size / 1_048_576:.1f} MiB)", flush=True)
            return
    partial = destination.with_suffix(destination.suffix + ".part")
    print(f"download  {destination.name} ({expected_size / 1_048_576:.1f} MiB)", flush=True)
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
    with urlopen(request, timeout=180) as response, partial.open("wb") as handle:
        downloaded = 0
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            handle.write(chunk)
            downloaded += len(chunk)
            if expected_size >= 20 * 1_048_576 and downloaded % (25 * 1_048_576) < len(chunk):
                print(f"          {100 * downloaded / expected_size:5.1f}%", flush=True)
    if partial.stat().st_size != expected_size:
        raise RuntimeError(f"Size mismatch for {destination.name}: {partial.stat().st_size} != {expected_size}")
    actual_md5 = file_md5(partial)
    if actual_md5 != expected_md5:
        raise RuntimeError(f"Checksum mismatch for {destination.name}: {actual_md5} != {expected_md5}")
    partial.replace(destination)


def safe_extract(archive: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    root = destination.resolve()
    with ZipFile(archive) as zipped:
        for item in zipped.infolist():
            target = (destination / item.filename).resolve()
            if root != target and root not in target.parents:
                raise RuntimeError(f"Unsafe archive path: {item.filename!r}")
        zipped.extractall(destination)
    marker = destination / ".argus_extracted.json"
    marker.write_text(
        json.dumps({"archive": archive.name, "md5": file_md5(archive)}, indent=2), encoding="utf-8"
    )


def tud_bitstreams() -> tuple[dict, dict[str, dict]]:
    item = request_json(TUD_API)
    bundles = request_json(item["_links"]["bundles"]["href"])["_embedded"]["bundles"]
    files: dict[str, dict] = {}
    for bundle in bundles:
        response = request_json(bundle["_links"]["bitstreams"]["href"])
        for bitstream in response.get("_embedded", {}).get("bitstreams", []):
            files[bitstream["name"]] = bitstream
    return item, files


def download_tud(destination: Path, include_raw: bool, extract: bool) -> dict:
    item, files = tud_bitstreams()
    selected = set(TUD_REQUIRED)
    if include_raw:
        selected.add("raw_measurement_data.zip")
    missing = selected - files.keys()
    if missing:
        raise RuntimeError(f"TU Darmstadt record is missing required files: {sorted(missing)}")
    manifest_files = []
    for name in sorted(selected):
        bitstream = files[name]
        checksum = bitstream["checkSum"]
        if checksum["checkSumAlgorithm"].lower() != "md5":
            raise RuntimeError(f"Unsupported checksum algorithm for {name}")
        url = bitstream["_links"]["content"]["href"]
        download(url, destination / name, int(bitstream["sizeBytes"]), checksum["value"].lower())
        manifest_files.append({"name": name, "size": int(bitstream["sizeBytes"]), "md5": checksum["value"].lower()})
    if extract:
        safe_extract(destination / "unaugmented_data.zip", destination / "unaugmented_data")
    manifest = {
        "dataset": "TU Darmstadt GFRP acoustic defect dataset",
        "record_id": TUD_ITEM_ID,
        "url": f"https://tudatalib.ulb.tu-darmstadt.de/items/{TUD_ITEM_ID}",
        "license": "CC-BY-4.0",
        "profile": "raw+unaugmented" if include_raw else "unaugmented",
        "files": manifest_files,
    }
    (destination / "argus_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def download_ae(destination: Path, include_simulation: bool, extract: bool) -> dict:
    record = request_json(AE_API)
    files = {item["key"]: item for item in record["files"]}
    selected = {name for name in files if name.lower().endswith(".csv")}
    if include_simulation:
        selected.add("Simulation.zip")
    manifest_files = []
    for name in sorted(selected):
        item = files[name]
        checksum_type, checksum = item["checksum"].split(":", 1)
        if checksum_type.lower() != "md5":
            raise RuntimeError(f"Unsupported checksum algorithm for {name}")
        url = item["links"].get("content", item["links"].get("self"))
        download(url, destination / name, int(item["size"]), checksum.lower())
        manifest_files.append({"name": name, "size": int(item["size"]), "md5": checksum.lower()})
    if include_simulation and extract:
        safe_extract(destination / "Simulation.zip", destination / "simulation")
    metadata = record["metadata"]
    manifest = {
        "dataset": metadata["title"],
        "record_id": AE_RECORD_ID,
        "doi": metadata["doi"],
        "url": f"https://zenodo.org/records/{AE_RECORD_ID}",
        "license": metadata["license"]["id"],
        "profile": "paired-simulation-experiment" if include_simulation else "experimental",
        "files": manifest_files,
    }
    (destination / "argus_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Download and verify the measured datasets used by ARGUS sim-to-real")
    parser.add_argument("--dataset", choices=("tud-gfrp", "ae-impact", "all"), default="all")
    parser.add_argument("--include-tud-raw", action="store_true", help="Also download the 560 MiB unsplit Soundbook export")
    parser.add_argument("--experimental-only", action="store_true", help="Skip the AE ray-tracing simulation archive")
    parser.add_argument("--no-extract", action="store_true")
    args = parser.parse_args()
    manifests = []
    if args.dataset in {"tud-gfrp", "all"}:
        manifests.append(download_tud(TUD_DESTINATION, args.include_tud_raw, not args.no_extract))
    if args.dataset in {"ae-impact", "all"}:
        manifests.append(download_ae(AE_DESTINATION, not args.experimental_only, not args.no_extract))
    for manifest in manifests:
        print(f"ready     {manifest['dataset']} [{manifest['license']}]", flush=True)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        raise SystemExit("Download interrupted; rerun the command to verify completed files.")
    except Exception as exc:
        print(f"Sim-to-real dataset download failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
