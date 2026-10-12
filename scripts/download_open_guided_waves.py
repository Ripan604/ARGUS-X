"""Download bounded numeric HDF5 members from official OGW Figshare ZIPs.

ZIP ranges avoid fetching >150 GB of archives. Partial members have verified
ZIP CRC and local SHA256; the publisher's whole-archive MD5 is retained but is
NOT claimed verified. Downloaded source code is never executed or extracted.
"""
from __future__ import annotations
import argparse
import hashlib
import io
import json
import math
import re
import stat
import sys
import time
import zipfile
import zlib
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

import requests

ROOT = Path(__file__).resolve().parents[1]
DESTINATION = ROOT / "datasets/external/open_guided_waves"
ARTICLES = {"healthy": 8108297, "D04": 8107889, "D12": 8107886, "D16": 8107883, "D24": 8107880}
MAX_MEMBER = 64 * 1024 * 1024
MAX_INDEX = 16 * 1024 * 1024
MAX_NODES = 4096
MAX_NUMERIC_ARRAY = 64 * 1024 * 1024
MAX_DOWNLOAD = 1024 * 1024 * 1024
ARTICLE_XML = "https://www.ebi.ac.uk/europepmc/webservices/rest/PMC6778066/fullTextXML"


def json_write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def bounded_metadata(session: requests.Session, url: str) -> bytes:
    with session.get(url, stream=True, timeout=(20, 40)) as response:
        response.raise_for_status()
        payload = bytearray()
        for block in response.iter_content(65536):
            if len(payload) + len(block) > 1024 * 1024: raise ValueError("Primary metadata exceeds cap")
            payload.extend(block)
        return bytes(payload)


def primary_geometry(session: requests.Session, frequency_khz: int) -> None:
    raw = bounded_metadata(session, ARTICLE_XML)
    if b"<!ENTITY" in raw: raise ValueError("XML entity definitions refused")
    article = ET.fromstring(raw)
    doi = article.find(".//article-id[@pub-id-type='doi']")
    if doi is None or doi.text != "10.1038/s41597-019-0208-1": raise ValueError("Primary article identity mismatch")
    tables = {}
    for identity in ("Tab1", "Tab2"):
        table = article.find(f".//table-wrap[@id='{identity}']/table/tbody")
        if table is None: raise ValueError("Primary geometry table missing")
        tables[identity] = [["".join(cell.itertext()) for cell in row.findall("td")] for row in table.findall("tr")]
    sensors = [[float(row[1]) / 1000, float(row[2]) / 1000] for row in tables["Tab1"]]
    damage = {re.sub(r"\s+", "", row[0]): [float(row[1]) / 1000, float(row[2]) / 1000] for row in tables["Tab2"]}
    if len(sensors) != 12 or set(damage) != {"D04", "D12", "D16", "D24"}: raise ValueError("Geometry label set changed")
    (DESTINATION / "metadata").mkdir(parents=True, exist_ok=True)
    (DESTINATION / "metadata/primary_article.xml").write_bytes(raw)
    json_write(DESTINATION / "metadata/geometry.json", {
        "panel": {"width_m": .5, "height_m": .5, "thickness_m": .002,
                  "material": "Hexply M21/34%/UD134/T700/300 CFRP", "layup": "[45/0/-45/90/-45/0/45/90]S"},
        "sensor_order": "T1..T12; HDF channels zero-based; 66 unordered pairs only",
        "sensor_coordinates_m": sensors, "reference_damage_coordinates_m": damage,
        "damage_model": "surface-mounted reversible aluminium disc with tacky tape; not literal delamination or cavity",
        "geometry_source": ARTICLE_XML, "paper_doi": doi.text, "primary_article_sha256": hashlib.sha256(raw).hexdigest(),
        "data_collection_doi": "10.6084/m9.figshare.c.4488089.v1", "data_license": "CC0", "article_license": "CC BY 4.0",
        "geometry_origin": "primary paper Tables 1 and 2, no data-derived location fitting",
        "selected_frequency_hz": frequency_khz * 1000,
        "native_sampling_frequency_hz": 10000000, "source_excitation": "five-cycle Hann-filtered sine; published drive +/-100 V",
        "selection_basis": "publisher-defined ascending thermal ramps; actual chamber/surface values preserved",
        "independent_healthy_partition": "first ascending cycle baseline; second ascending cycle test"})
    (DESTINATION / "LICENSE_AND_CITATION.txt").write_text(
        "Data license: CC0 https://creativecommons.org/publicdomain/zero/1.0/\n"
        "Article license: CC BY 4.0 https://creativecommons.org/licenses/by/4.0/\n"
        "Moll, J.; Kexel, C.; Poetzsch, S.; Rennoch, M.; Herrmann, A.S. (2019).\n"
        "Temperature affected guided wave propagation in a composite plate complementing the Open Guided Waves Platform.\n"
        "Scientific Data 6:191. https://doi.org/10.1038/s41597-019-0208-1\n"
        "Dataset: https://doi.org/10.6084/m9.figshare.c.4488089.v1\n"
        "The local numeric subset is unchanged. Selection/provenance is described in argus_manifest.json.\n",
        encoding="utf-8")


class BoundedRemoteZip(io.RawIOBase):
    def __init__(self, session: requests.Session, url: str, size: int, budget: dict):
        self.session, self.url, self.size, self.budget = session, url, size, budget
        self.position = 0
        self.cache = {}

    def seekable(self): return True
    def readable(self): return True
    def tell(self): return self.position
    def seek(self, offset, whence=0):
        target = offset if whence == 0 else self.position + offset if whence == 1 else self.size + offset
        if not 0 <= target <= self.size: raise ValueError("ZIP seek outside declared file")
        self.position = target
        return target

    def read(self, size=-1):
        size = self.size - self.position if size < 0 else min(size, self.size - self.position)
        if size == 0: return b""
        if size > MAX_MEMBER: raise ValueError("Unbounded ZIP read refused")
        start, end = self.position, self.position + size - 1
        key = (start, end)
        if key not in self.cache:
            if self.budget["received_bytes"] + size > self.budget["maximum_bytes"]:
                raise ValueError("Total download budget exhausted")
            with self.session.get(self.url, headers={"Range": f"bytes={start}-{end}", "Accept-Encoding": "identity"},
                                  stream=True, timeout=(20, 90)) as response:
                if response.status_code != 206: raise ValueError("Server ignored range; whole archive refused")
                if response.headers.get("Content-Range") != f"bytes {start}-{end}/{self.size}":
                    raise ValueError("Range origin/length mismatch")
                payload = bytearray()
                for block in response.iter_content(1024 * 1024):
                    if len(payload) + len(block) > size: raise ValueError("Oversized range body")
                    payload.extend(block)
                if len(payload) != size: raise ValueError("Incomplete range body")
                self.budget["received_bytes"] += size
                # Cache only ZIP metadata-sized reads; never retain all measurement payloads.
                if size <= 65536: self.cache[key] = bytes(payload)
                else:
                    self.position += size
                    return bytes(payload)
        self.position += size
        return self.cache[key]


def safe_member(info: zipfile.ZipInfo) -> None:
    name = info.filename
    path = PurePosixPath(name)
    if ("\\" in name or "\\" in info.orig_filename or "\x00" in name or path.is_absolute() or ".." in path.parts
            or re.match(r"^[A-Za-z]:", name)):
        raise ValueError("Unsafe archive member path")
    kind = (info.external_attr >> 16) & 0o170000
    if kind == stat.S_IFLNK: raise ValueError("Archive symlink refused")
    if info.flag_bits & 1: raise ValueError("Encrypted archive member refused")
    if info.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED):
        raise ValueError("Unsupported archive compression")
    if info.file_size > MAX_MEMBER or info.compress_size > MAX_MEMBER:
        raise ValueError("Archive member exceeds allocation cap")
    if info.file_size > max(1024 * 1024, info.compress_size * 200):
        raise ValueError("Excessive archive expansion")


def verify_saved(manifest: dict) -> dict:
    import h5py
    import numpy as np
    counts, conditions, total = {}, [], 0
    for record in manifest["files"]:
        path = ROOT / record["local_path"]
        if not path.resolve().is_relative_to(DESTINATION.resolve()) or path.stat().st_size > MAX_MEMBER:
            raise ValueError("Saved numeric file escaped source/allocation bounds")
        raw = path.read_bytes()
        if (len(raw) != record["member_size"] or hashlib.sha256(raw).hexdigest() != record["sha256"]
                or f"{zlib.crc32(raw) & 0xffffffff:08x}" != record["member_crc32"]):
            raise ValueError("Saved source hash/CRC mismatch")
        schema = inspect_hdf5(path)
        json_write(path.with_suffix(".schema.json"), schema)
        with h5py.File(path, "r") as source:
            for name in ("pitchcatch/catch", "pitchcatch/pitch"):
                if source[name].shape != (66, 13108) or not np.isfinite(source[name][()]).all():
                    raise ValueError("Source bank shape/finite contract failed")
        counts[record["state"]] = counts.get(record["state"], 0) + 1
        total += len(raw)
        conditions.append({key: record[key] for key in ("state", "timestamp", "thermal_cycle", "chamber_temperature_c", "surface_temperature_c")})
    summary = {"accepted_full_banks": len(conditions), "raw_numeric_bytes": total, "files_per_state": counts,
               "every_signal_finite": True, "shape66x13108": True, "crc_sha_checked_after_download": True}
    manifest["verification"] = summary
    manifest["metadata_provenance"] = [{"path": path.relative_to(ROOT).as_posix(),
                                        "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
                                       for path in (DESTINATION / "metadata").iterdir() if path.is_file()]
    manifest["downloader_source_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    json_write(DESTINATION / "download_verification.json", {"summary": summary, "conditions": conditions})
    return manifest


def inspect_hdf5(path: Path) -> dict:
    import h5py
    import numpy as np
    result = {"datasets": {}, "attributes": {}}
    nodes = 0
    with h5py.File(path, "r") as source:
        checked = set()
        def links(group, depth=0):
            if depth > 32: raise ValueError("HDF5 hierarchy depth exceeds cap")
            identity = h5py.h5o.get_info(group.id).addr
            if identity in checked: return
            checked.add(identity)
            if len(checked) > MAX_NODES: raise ValueError("HDF5 link count exceeds cap")
            for key in group.keys():
                if not isinstance(group.get(key, getlink=True), h5py.HardLink):
                    raise ValueError("External or soft HDF5 links refused")
                obj = group[key]
                if isinstance(obj, h5py.Group): links(obj, depth + 1)
        links(source)
        def visit(name, obj):
            nonlocal nodes
            nodes += 1
            if nodes > MAX_NODES: raise ValueError("HDF5 object count exceeds cap")
            if isinstance(obj, h5py.Dataset):
                if obj.dtype.kind not in "biufcSU": raise ValueError("Object/reference HDF5 datatype refused")
                if obj.ndim > 4 or obj.dtype.hasobject: raise ValueError("HDF5 dimension/type outside numeric contract")
                if obj.size * obj.dtype.itemsize > MAX_NUMERIC_ARRAY: raise ValueError("HDF5 array exceeds cap")
                if obj.is_virtual or obj.external: raise ValueError("External/virtual HDF5 storage refused")
                if obj.chunks and math.prod(obj.chunks) * obj.dtype.itemsize > MAX_NUMERIC_ARRAY:
                    raise ValueError("HDF5 chunk exceeds allocation cap")
                creation = obj.id.get_create_plist()
                for index in range(creation.get_nfilters()):
                    filter_id = creation.get_filter(index)[0]
                    if filter_id not in (1, 2, 3) or not h5py.h5z.filter_avail(filter_id):
                        raise ValueError("External or unavailable HDF5 filter refused")
                result["datasets"][name] = {"shape": list(obj.shape), "dtype": str(obj.dtype)}
                if obj.size <= 1024:
                    values = obj[()]
                    if isinstance(values, bytes): values = values.decode("utf-8", errors="replace")
                    elif isinstance(values, np.ndarray): values = values.tolist()
                    elif isinstance(values, np.generic): values = values.item()
                    result["datasets"][name]["small_value"] = values
            for key in obj.attrs.keys():
                attribute = obj.attrs.get_id(key)
                if attribute.shape is None:
                    result["attributes"][f"{name or '/'}/{key}"] = None
                    continue
                if (attribute.dtype.kind not in "biufcSU" or attribute.dtype.hasobject
                        or math.prod(attribute.shape or (1,)) * attribute.dtype.itemsize > 65536):
                    result["attributes"][f"{name or '/'}/{key}"] = {"not_read": "unsupported_or_unbounded_attribute"}
                    continue
                value = obj.attrs[key]
                values = np.asarray(value)
                if values.dtype.kind not in "biufcSUO" or values.size > 2048: continue
                if values.dtype.kind == "O":
                    if not all(isinstance(v, (str, bytes)) for v in values.ravel()):
                        raise ValueError("HDF5 object/reference attribute refused")
                converted = values.tolist()
                def decode(v):
                    if isinstance(v, bytes): return v.decode("utf-8", errors="replace")
                    if isinstance(v, list): return [decode(x) for x in v]
                    return v
                result["attributes"][f"{name or '/'}/{key}"] = decode(converted)
        visit("", source)
        source.visititems(visit)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frequency-khz", type=int, default=100)
    parser.add_argument("--snapshots", type=int, default=3)
    parser.add_argument("--selection", choices=("protocol-temperature", "chronological"), default="protocol-temperature")
    parser.add_argument("--states", nargs="+", choices=ARTICLES, default=list(ARTICLES))
    parser.add_argument("--max-download-mib", type=int, default=900)
    parser.add_argument("--inspect-only", action="store_true")
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    if not 1 <= args.snapshots <= 16 or not 1 <= args.max_download_mib <= 1024:
        parser.error("Bounded snapshot/download range required")
    DESTINATION.mkdir(parents=True, exist_ok=True)
    if args.verify_only:
        path = DESTINATION / "argus_manifest.json"
        manifest = verify_saved(json.loads(path.read_text(encoding="utf-8")))
        json_write(path, manifest)
        print(json.dumps(manifest["verification"]), flush=True)
        return
    session = requests.Session()
    budget = {"received_bytes": 0, "maximum_bytes": args.max_download_mib * 1024 * 1024}
    manifest = {"schema_version": 1, "dataset": "Open Guided Waves #2 temperature extension",
                "collection_doi": "10.6084/m9.figshare.c.4488089.v1",
                "collection_url": "https://api.figshare.com/v2/collections/4488089",
                "paper_doi": "10.1038/s41597-019-0208-1", "data_license": "CC0",
                "license_url": "https://creativecommons.org/publicdomain/zero/1.0/",
                "acquired_at_utc": datetime.now(timezone.utc).isoformat(),
                "evidence_type": "measured_ultrasonic_reversible_surface_reference_damage_not_ARGUS_hardware",
                "whole_archive_md5_verified": False, "selection": vars(args), "sources": [], "files": [], "failures": []}
    previous = DESTINATION / "argus_manifest.json"
    if previous.exists():
        old = json.loads(previous.read_text(encoding="utf-8"))
        manifest["files"] = old.get("files", [])
    try:
        primary_geometry(session, args.frequency_khz)
        for state in args.states:
            api = f"https://api.figshare.com/v2/articles/{ARTICLES[state]}"
            item = json.loads(bounded_metadata(session, api))
            json_write(DESTINATION / "metadata" / f"figshare_{ARTICLES[state]}.json", item)
            if item.get("license", {}).get("name") != "CC0": raise ValueError("Dataset license changed; reassess")
            archive = item["files"][0]
            manifest["sources"].append({"state": state, "article_url": api, "doi": item["doi"], "file": archive})
            print(f"Index {state}: {archive['name']} ({archive['size']} bytes)", flush=True)
            remote = BoundedRemoteZip(session, archive["download_url"], archive["size"], budget)
            with zipfile.ZipFile(remote) as zipped:
                infos = zipped.infolist()
                if len(infos) > 100000: raise ValueError("Archive member count exceeds cap")
                hdf = [info for info in infos if re.search(rf"(?:_|\s)f{args.frequency_khz}kHz\.h5$", info.filename, re.I)]
                json_write(DESTINATION / "metadata" / f"archive_index_{state}.json", [
                    {"name": info.filename, "compressed_bytes": info.compress_size, "bytes": info.file_size,
                     "crc32": f"{info.CRC:08x}"} for info in infos])
                print(f"  {len(infos)} members; {len(hdf)} matching frequency files", flush=True)
                if not hdf: raise ValueError("Requested frequency absent")
                hdf.sort(key=lambda info: info.filename)
                if args.selection == "protocol-temperature":
                    # Publisher protocol: 20..60 C in 0.5 C increments, then cooling;
                    # 161 timestamps/cycle. Selection is frozen before waveform analysis.
                    expected = 322 if state == "healthy" else 161
                    if len(hdf) != expected: raise ValueError("Published thermal-cycle count changed")
                    indices = [0, 40, 80] + ([161, 201, 241] if state == "healthy" else [])
                else:
                    indices = sorted({round(i * (len(hdf) - 1) / max(args.snapshots - 1, 1)) for i in range(args.snapshots)})
                selected = [hdf[i] for i in indices]
                if args.inspect_only: continue
                for info in selected:
                    safe_member(info)
                    timestamp = next((part for part in PurePosixPath(info.filename).parts if re.fullmatch(r"\d{8}T\d{6}", part)), "unknown")
                    target = DESTINATION / "numeric" / state / timestamp / PurePosixPath(info.filename).name
                    if not target.resolve().is_relative_to(DESTINATION.resolve()): raise ValueError("Output escaped dataset directory")
                    target.parent.mkdir(parents=True, exist_ok=True)
                    if not target.exists():
                        with zipped.open(info) as contents:
                            payload = contents.read(MAX_MEMBER + 1)
                        if len(payload) != info.file_size: raise ValueError("Expanded member length mismatch")
                        target.write_bytes(payload)
                    raw = target.read_bytes()
                    if len(raw) != info.file_size or zlib.crc32(raw) & 0xffffffff != info.CRC:
                        raise ValueError("Existing/downloaded member size or CRC mismatch")
                    actual_sha = hashlib.sha256(raw).hexdigest()
                    schema = inspect_hdf5(target)
                    temperature = schema["datasets"]["CTC/Temperature"]["small_value"][0]
                    if args.selection == "protocol-temperature":
                        expected_temperature = {0: 20., 40: 40., 80: 60., 161: 20., 201: 40., 241: 60.}[hdf.index(info)]
                        if abs(temperature - expected_temperature) > .25:
                            raise ValueError("Selected member chamber temperature conflicts with published ramp")
                    json_write(target.with_suffix(".schema.json"), schema)
                    record = {"state": state, "timestamp": timestamp, "local_path": target.relative_to(ROOT).as_posix(),
                              "member_path": info.filename, "member_size": info.file_size,
                              "member_crc32": f"{info.CRC:08x}", "member_crc_verified": True,
                              "sha256": actual_sha, "archive_url": archive["download_url"],
                              "chamber_temperature_c": temperature,
                              "surface_temperature_c": schema["datasets"]["Temperature/values"]["small_value"],
                              "thermal_cycle": 2 if state == "healthy" and hdf.index(info) >= 161 else 1,
                              "native_sampling_frequency_hz": schema["datasets"]["command/pitchcatch/sampling_frequency"]["small_value"][0],
                              "channels_count": schema["datasets"]["command/pitchcatch/channels"]["shape"][0],
                              "publisher_archive_md5": archive["computed_md5"], "whole_archive_md5_verified": False}
                    manifest["files"] = [r for r in manifest["files"] if r["local_path"] != record["local_path"]] + [record]
                    print(f"  Saved {record['local_path']} ({info.file_size} bytes)", flush=True)
                    json_write(previous, manifest)
        if not args.inspect_only:
            verify_saved(manifest)
    except Exception as error:
        manifest["failures"].append({"type": type(error).__name__, "message": str(error)})
        raise
    finally:
        manifest["transfer"] = budget
        json_write(previous, manifest)
        session.close()


if __name__ == "__main__": main()
