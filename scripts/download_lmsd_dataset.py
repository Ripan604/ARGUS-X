from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
RECORD_ID = "11033677"
API_URL = f"https://zenodo.org/api/records/{RECORD_ID}"
DEFAULT_DESTINATION = ROOT / "datasets" / "external" / "lmsd2021"
METADATA_FILES = {"README.txt", "LICENSE-DATA.txt", "plate_positions.png"}


def md5(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.md5()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fetch_record() -> dict:
    request = Request(API_URL, headers={"User-Agent": "ARGUS-dataset-downloader/1.0"})
    with urlopen(request, timeout=30) as response:
        return json.load(response)


def download(url: str, destination: Path, expected_size: int, expected_md5: str) -> None:
    if destination.exists() and destination.stat().st_size == expected_size and md5(destination) == expected_md5:
        print(f"verified  {destination.name} ({expected_size / 1_048_576:.1f} MiB)", flush=True)
        return
    part = destination.with_suffix(destination.suffix + ".part")
    print(f"download  {destination.name} ({expected_size / 1_048_576:.1f} MiB)", flush=True)
    request = Request(url, headers={"User-Agent": "ARGUS-dataset-downloader/1.0", "Accept": "application/octet-stream"})
    with urlopen(request, timeout=120) as response, part.open("wb") as handle:
        downloaded = 0
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            handle.write(chunk)
            downloaded += len(chunk)
            if expected_size > 20 * 1_048_576 and downloaded % (25 * 1_048_576) < len(chunk):
                print(f"          {100 * downloaded / expected_size:5.1f}%", flush=True)
    if part.stat().st_size != expected_size:
        raise RuntimeError(f"Size mismatch for {destination.name}: {part.stat().st_size} != {expected_size}")
    actual_md5 = md5(part)
    if actual_md5 != expected_md5:
        raise RuntimeError(f"Checksum mismatch for {destination.name}: {actual_md5} != {expected_md5}")
    part.replace(destination)


def main() -> None:
    parser = argparse.ArgumentParser(description="Download and verify the public KU Leuven LMSD plate dataset")
    parser.add_argument("--profile", choices=("metadata", "minimal", "all"), default="minimal")
    parser.add_argument("--destination", type=Path, default=DEFAULT_DESTINATION)
    args = parser.parse_args()
    record = fetch_record()
    files = {item["key"]: item for item in record["files"]}
    selected = set(METADATA_FILES)
    if args.profile in {"minimal", "all"}:
        selected.update({"baseline.npz", "1 mass.npz"})
    if args.profile == "all":
        selected.update(name for name in files if name.endswith(".npz"))
    args.destination.mkdir(parents=True, exist_ok=True)
    for name in sorted(selected):
        item = files.get(name)
        if item is None:
            raise RuntimeError(f"Zenodo record no longer contains required file {name!r}")
        checksum_type, checksum = item["checksum"].split(":", 1)
        if checksum_type != "md5":
            raise RuntimeError(f"Unsupported checksum type {checksum_type!r}")
        download(item["links"]["self"], args.destination / name, int(item["size"]), checksum)
    manifest = {
        "record_id": RECORD_ID,
        "doi": record["metadata"]["doi"],
        "title": record["metadata"]["title"],
        "license": record["metadata"]["license"]["id"],
        "profile": args.profile,
        "files": sorted(selected),
    }
    (args.destination / "argus_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Ready: {args.destination.resolve()}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        raise SystemExit("Download interrupted; rerun the command to resume verification.")
    except Exception as exc:
        print(f"LMSD download failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
