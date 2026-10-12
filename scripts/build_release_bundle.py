"""Build or verify a local, allowlisted source/evidence review bundle.

This operation does not publish, upload, file a patent, or execute packaged code.
ZIP integrity is content consistency; it is not a signature or proof of novelty.
Only Python's standard library is required to inspect the resulting artifact.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import io
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys
import zipfile


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_NAME = "release_manifest.json"
MAX_BUNDLE_BYTES = 100 * 1024 * 1024
# The frozen 1,920-run study is 29 MB with complete candidate/failed-case
# traces. Keep it intact, within both a per-file cap and the 100 MB total cap.
MAX_FILE_BYTES = 32 * 1024 * 1024
MAX_FILES = 5_000
BLOCKED_PARTS = {
    ".git", ".aws", ".ssh", ".azure", ".gcloud", ".codex", ".agents", ".config",
    "secrets", "credentials", "node_modules", "vendor", ".venv", "venv", "__pycache__",
    ".pytest_cache", ".next", ".vite", "dist", "build", "generated", "uploads", "data", "logs", "release",
}
ROOT_FILES = {
    "README.md", "LICENSE", "pytest.ini", ".gitignore", "IMPLEMENTATION_REPORT.md",
    "run_argus.py", "run_argus.ps1", "run_edge_node.py", "start_argus.bat", "start_argus.sh",
    "start_backend.bat", "start_backend.sh", "start_frontend.bat", "start_frontend.sh",
}
BACKEND_FILES = {"backend/__init__.py", "backend/run_backend.py", "backend/requirements.txt", "backend/requirements.lock.txt"}
FRONTEND_FILES = {
    "frontend/package.json", "frontend/package-lock.json", "frontend/tsconfig.json",
    "frontend/next-env.d.ts", "frontend/next.config.ts", "frontend/vite.config.ts",
    "frontend/eslint.config.mjs", "frontend/postcss.config.mjs", "frontend/.gitignore", "frontend/.env.example",
}
VERIFICATION_FILES = {
    "output/release/probe-v2-board-build.json", "output/release/probe-v2-backend-tests.xml",
    "output/release/frontend-checks.json", "output/release/probe-v2-host-fixture.txt",
    "output/release/measured-data-backend-tests.xml", "output/release/fundamental-backend-tests.xml",
}
PUBLIC_REPORT_FILES = {
    "frontend/public/research/measured-data-summary.json", "frontend/public/research/nuisance-design-summary.json",
    "frontend/public/research/fundamental-summary.json",
}
REDUNDANT_PREFLIGHT_FILES = {
    "research_results/measured_guided_wave_validation_2026_10_08_preflight_pilot.json",
    "research_results/reference_conditioned_development_2026_10_08_v1_control_pilot.json",
}
DOC_FILES = {
    "API.md", "ARCHITECTURE.md", "ARGUS_CURRENT_ARCHITECTURE.md", "ARGUS_NEO_ARCHITECTURE.md",
    "SCIENTIFIC_MODEL.md", "HARDWARE.md", "EVIDENCE_LEDGER.md", "BENCHMARK_PROTOCOL.md",
    "LIMITATIONS.md", "RESEARCH_EVALUATION.md", "REPRODUCIBILITY.md", "REAL_DATA_GUIDE.md",
    "CURRENT_INVENTION_DISCLOSURE.md", "PATENT_TECHNICAL_DISCLOSURE_NOTES.md", "PRIOR_ART_NOTES.md",
    "AUDIT_REMEDIATION.md", "VERIFICATION_REPORT.md", "RELEASE_VERIFICATION.md",
    "RELEASE_READINESS_REPORT.md", "PATENT_REVIEW_PACKAGE.md", "SECURITY.md", "PUBLICATION_READINESS.md",
    "VALIDATION_PROTOCOL_2026_10_07.md",
    "ARGUS_FINAL_TECHNICAL_DISCLOSURE.md", "FINAL_CALIBRATION_PROTOCOL.md",
    "FINAL_PATENT_EVIDENCE.md",
    "EXTENDED_REFERENCE_VALIDATION_PROTOCOL.md", "PROBE_V2_DESIGN.md",
    "PATENT_STRENGTHENING_ASSESSMENT.md", "PROBE_V2_RELEASE_REVIEW.md",
    "MEASURED_DATASET_CATALOG_2026_10_08.md", "MEASURED_RESULTS_2026_10_08.md",
    "MEASURED_GFRP_VALIDATION_PROTOCOL.md", "MEASURED_IMPACT_VALIDATION_PROTOCOL.md",
    "MEASURED_MORPHO_QUALITY_PROTOCOL.md", "OPEN_GUIDED_WAVES_SOURCE_AUDIT.md",
    "MEASURED_GUIDED_WAVE_PROTOCOL.md", "HEALTHY_WAVE_TRANSPORT_PROTOCOL.md",
    "TRAJECTORY_REFERENCE_GATE_PROTOCOL.md", "REFERENCE_CONDITIONED_CONFIRMATION_PROTOCOL.md",
    "OGW_CONFIRMATION_ACQUISITION.md", "FUNDAMENTAL_UPGRADE_RESULTS_2026_10_08.md",
    "WORKSPACE_UPGRADE_2026_10_09.md",
}
SOURCE_TREES = {
    "backend/app": {".py"}, "backend/tests": {".py"},
    "frontend/app": {".ts", ".tsx", ".js", ".jsx", ".css"},
    "frontend/components": {".ts", ".tsx", ".js", ".jsx", ".css"},
    "frontend/hooks": {".ts", ".tsx"}, "frontend/services": {".ts", ".tsx"},
    "frontend/types": {".ts", ".tsx"}, "frontend/utils": {".ts", ".tsx"},
    "frontend/tests": {".ts", ".tsx", ".js"}, "frontend/public": {".svg"},
    "firmware": {".ino", ".c", ".cpp", ".h", ".md", ".ps1"}, "scripts": {".py"},
    "paper": {".tex", ".bib", ".md"}, "research_results": {".json"},
    "models": {".json", ".md"}, "benchmark_results": {".json", ".csv"},
}


def _relative_name(name: str) -> PurePosixPath:
    path = PurePosixPath(name)
    if (not name or path.is_absolute() or ".." in path.parts or "\\" in name or ":" in name
            or str(path) != name or any(ord(character) < 32 for character in name)):
        raise ValueError("Release bundle contains an unsafe or noncanonical path")
    return path


def allowed_path(name: str) -> bool:
    path = _relative_name(name)
    if name in REDUNDANT_PREFLIGHT_FILES:
        # These source-validation reruns have identical final metrics; preserve
        # full pilots in the workspace while packaging all current case traces.
        return False
    # Exact bounded receipts only; the rest of release/ (including nested
    # archives) stays excluded. The mock fixture is labelled synthetic.
    if name in VERIFICATION_FILES or name in PUBLIC_REPORT_FILES:
        return True
    parts = [part.lower() for part in path.parts]
    if any(part in BLOCKED_PARTS for part in parts):
        return False
    if any(part.startswith(".env") and part != ".env.example" for part in parts):
        return False
    if any(PurePosixPath(part).stem in {"credentials", "credential", "secrets", "secret", "private_key", "id_rsa", "id_ed25519"} for part in parts):
        return False
    if name in ROOT_FILES or name in BACKEND_FILES or name in FRONTEND_FILES:
        return True
    if len(path.parts) == 2 and path.parts[0] == "docs":
        return path.name in DOC_FILES
    # Plans and saved audit summaries are included; prior releases and all
    # rendered PDFs remain separate artifacts.
    if len(path.parts) == 2 and path.parts[0] == "output":
        return path.suffix.lower() == ".json"
    for tree, suffixes in SOURCE_TREES.items():
        if name.startswith(tree + "/") and path.suffix.lower() in suffixes:
            return True
    return False


def _inspect_content(name: str, content: bytes) -> None:
    try:
        content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"Release input is not UTF-8 text: {name}") from exc
    if b"\0" in content or re.search(rb"-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----", content):
        raise ValueError(f"Release input contains binary data or a private key: {name}")
    if PurePosixPath(name).suffix.lower() == ".json":
        _json(content)


def _read_file(path: Path, maximum: int = MAX_FILE_BYTES) -> bytes:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > maximum:
        raise ValueError("Release input is a symlink, missing, or exceeds its byte limit")
    with path.open("rb") as handle:
        content = handle.read(maximum + 1)
    if len(content) > maximum:
        raise ValueError("Release input exceeds its byte limit")
    return content


def _json(content: bytes):
    def pairs(items):
        value = {}
        for key, item in items:
            if key in value:
                raise ValueError("Release JSON contains duplicate keys")
            value[key] = item
        return value
    def number(value):
        result = float(value)
        if not math.isfinite(result):
            raise ValueError("Release JSON contains non-finite numbers")
        return result
    try:
        value = json.loads(content.decode("utf-8"), object_pairs_hook=pairs, parse_float=number,
                           parse_constant=lambda _: (_ for _ in ()).throw(ValueError("Non-finite JSON number")))
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ValueError("Release contains invalid JSON") from exc
    def check(item, depth=0):
        if depth > 64:
            raise ValueError("Release JSON nesting exceeds supported bounds")
        if isinstance(item, dict):
            for key, child in item.items():
                check(key, depth + 1)
                check(child, depth + 1)
        elif isinstance(item, list):
            for child in item:
                check(child, depth + 1)
        elif isinstance(item, str):
            try:
                item.encode("utf-8")
            except UnicodeEncodeError as exc:
                raise ValueError("Release JSON contains invalid Unicode") from exc
    check(value)
    return value


def select_files(root: str | Path = ROOT) -> list[Path]:
    """Return a stable, sorted file selection without following symlinks."""
    root = Path(root).resolve()
    found: dict[str, Path] = {}
    candidates = [root / name for name in ROOT_FILES | BACKEND_FILES | FRONTEND_FILES | VERIFICATION_FILES | PUBLIC_REPORT_FILES]
    candidates.extend(root / "docs" / name for name in DOC_FILES)
    if (root / "output").is_dir() and not (root / "output").is_symlink():
        candidates.extend((root / "output").glob("*.json"))
    for tree in SOURCE_TREES:
        base = root / tree
        if not base.is_dir() or base.is_symlink():
            continue
        for directory, children, files in os.walk(base, topdown=True, followlinks=False):
            children[:] = sorted(child for child in children if child.lower() not in BLOCKED_PARTS
                                  and not child.lower().startswith(".env") and not (Path(directory) / child).is_symlink())
            candidates.extend(Path(directory) / name for name in files)
    for path in candidates:
        if path.is_symlink() or not path.is_file():
            continue
        if any(parent.is_symlink() for parent in path.parents if parent != root and root in parent.parents):
            continue
        if not path.resolve().is_relative_to(root):
            raise ValueError("Release input escapes the repository root")
        name = path.relative_to(root).as_posix()
        if allowed_path(name):
            found[name] = path
    names = sorted(found)
    if len(names) > MAX_FILES or len({name.casefold() for name in names}) != len(names):
        raise ValueError("Release contains too many files or case-colliding paths")
    return [found[name] for name in names]


def _role(name: str) -> str:
    if name.startswith(("research_results/", "benchmark_results/", "models/", "output/")):
        return "saved_evidence_or_model_metadata"
    if name.startswith(("docs/", "paper/")) or name in {"README.md", "LICENSE", "IMPLEMENTATION_REPORT.md"}:
        return "documentation"
    return "source_or_configuration"


def _evidence_source(name: str, content: bytes) -> dict | None:
    if _role(name) != "saved_evidence_or_model_metadata" or PurePosixPath(name).suffix.lower() != ".json":
        return None
    value = _json(content)
    declaration = value.get("evidence_source", "unspecified_in_file") if isinstance(value, dict) else "unspecified_in_file"
    return {"file": name, "declared_evidence_source": declaration if isinstance(declaration, str) else "unspecified_in_file",
            "interpretation": "saved report or metadata; packaging does not establish acquisition provenance or validate its claims"}


def _source_identity(root: Path, files: dict[str, dict]) -> dict:
    source_names = [name for name in sorted(files) if files[name]["role"] == "source_or_configuration"]
    commit, dirty, untracked = None, None, []
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True,
                                timeout=3, check=True).stdout.strip()
        changed = subprocess.run(["git", "diff", "--name-only", "-z", "HEAD"], cwd=root,
                                 capture_output=True, timeout=3, check=True).stdout
        others = subprocess.run(["git", "ls-files", "--others", "--exclude-standard", "-z"], cwd=root,
                                capture_output=True, timeout=3, check=True).stdout
        changed_names = {name.decode("utf-8") for name in changed.split(b"\0") if name}
        untracked = sorted(name.decode("utf-8") for name in others.split(b"\0") if name and name.decode("utf-8") in source_names)
        dirty = bool(untracked or any(allowed_path(name) and _role(name) == "source_or_configuration" for name in changed_names))
    except (OSError, subprocess.SubprocessError, UnicodeDecodeError):
        pass
    working_hash = _source_identity_from_files(files)
    return {"git_commit": commit, "dirty_source": dirty, "untracked_source_files": untracked,
            "working_tree_sha256": working_hash,
            "revision": f"{commit or 'git-unavailable'}+packaged-source-sha256:{working_hash}",
            "fingerprint_scope": "actual packaged source and configuration bytes, including dirty/untracked source; documentation and saved evidence excluded"}


def build_release_bundle(root: str | Path = ROOT, output_dir: str | Path | None = None, *, created_at: str | None = None) -> dict:
    root = Path(root).resolve()
    destination = Path(output_dir).resolve() if output_dir is not None else root / "output" / "release"
    allowed_destination = (root / "output" / "release").resolve()
    if not allowed_destination.is_relative_to(root) or not destination.is_relative_to(allowed_destination):
        raise ValueError("Release output must remain inside output/release")
    files, contents, evidence_sources = {}, {}, []
    total_bytes = 0
    for path in select_files(root):
        name = path.relative_to(root).as_posix()
        content = _read_file(path)
        # Allowlisted inputs are text. Reject disguised binary data and embedded
        # private keys instead of copying them into a review artifact.
        _inspect_content(name, content)
        total_bytes += len(content)
        if total_bytes > MAX_BUNDLE_BYTES:
            raise ValueError("Expanded release exceeds the 100 MB limit")
        role = _role(name)
        files[name] = {"sha256": sha256(content).hexdigest(), "size": len(content), "role": role}
        declaration = _evidence_source(name, content)
        if declaration is not None:
            evidence_sources.append(declaration)
        contents[name] = content
    if not files or not {"README.md", "LICENSE"} <= set(files):
        raise ValueError("A release requires README.md, LICENSE, and allowlisted project files")
    manifest = {
        "schema_version": 1, "artifact_type": "argus_local_review_release",
        "created_at_utc": created_at or datetime.now(timezone.utc).isoformat(),
        "source_identity": _source_identity(root, files), "files": files,
        "file_count": len(files), "expanded_bytes": total_bytes,
        "evidence_sources": evidence_sources,
        "scope": "Local source, dependency specifications, firmware, current review documents, manuscript source, and saved JSON/CSV evidence metadata.",
        "exclusions": "Private env files, secrets/credential directories, Git metadata, vendors, generated runtime data, logs/databases, binary models/raw measurements, prior release archives, and PDFs.",
        "publication_performed": False, "patent_filing_performed": False, "authenticity_verified": False,
        "limitations": "Hashes establish content consistency, not signatures, trusted timestamps, acquisition authenticity, patentability, novelty, or scientific validation. Retain the manifest independently for later comparison.",
    }
    manifest_bytes = json.dumps(manifest, sort_keys=True, indent=2, allow_nan=False).encode("utf-8")
    if len(manifest_bytes) > MAX_FILE_BYTES or total_bytes + len(manifest_bytes) > MAX_BUNDLE_BYTES:
        raise ValueError("Release manifest exceeds the size budget")
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, content in [*contents.items(), (MANIFEST_NAME, manifest_bytes)]:
            member = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            member.compress_type = zipfile.ZIP_DEFLATED
            member.external_attr = (stat.S_IFREG | 0o644) << 16
            archive.writestr(member, content)
    archive_bytes = output.getvalue()
    if len(archive_bytes) > MAX_BUNDLE_BYTES:
        raise ValueError("Compressed release exceeds the byte limit")
    destination.mkdir(parents=True, exist_ok=True)
    archive_path, manifest_path = destination / "argus-review-release.zip", destination / "argus-review-release.manifest.json"
    archive_path.write_bytes(archive_bytes)
    manifest_path.write_bytes(manifest_bytes)
    verified = verify_release_bundle(archive_path, manifest_path)
    return {"archive": str(archive_path), "manifest": str(manifest_path), "archive_sha256": sha256(archive_bytes).hexdigest(),
            "manifest_sha256": sha256(manifest_bytes).hexdigest(), **verified}


def verify_release_bundle(path: str | Path, manifest_path: str | Path | None = None) -> dict:
    """Verify without extraction, importing code, running files, or uploading."""
    payload = _read_file(Path(path), MAX_BUNDLE_BYTES)
    try:
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            members = archive.infolist()
            names = [member.filename for member in members]
            if len(members) > MAX_FILES + 1 or len({name.casefold() for name in names}) != len(names):
                raise ValueError("Release ZIP has too many members or duplicate paths")
            if sum(member.file_size for member in members) > MAX_BUNDLE_BYTES:
                raise ValueError("Expanded release exceeds the byte limit")
            for member in members:
                _relative_name(member.filename)
                if (member.orig_filename != member.filename or member.is_dir() or stat.S_ISLNK(member.external_attr >> 16)
                        or member.flag_bits & 1 or member.compress_type not in {zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED}
                        or member.file_size > MAX_FILE_BYTES):
                    raise ValueError("Release ZIP contains an unsafe or unsupported member")
                if member.filename != MANIFEST_NAME and not allowed_path(member.filename):
                    raise ValueError("Release ZIP contains a private or disallowed path")
            if MANIFEST_NAME not in names:
                raise ValueError("Release ZIP is missing its manifest")
            manifest_bytes = archive.read(MANIFEST_NAME)
            manifest = _json(manifest_bytes)
            if (not isinstance(manifest, dict) or manifest.get("schema_version") != 1
                    or manifest.get("artifact_type") != "argus_local_review_release"
                    or not isinstance(manifest.get("files"), dict)
                    or any(manifest.get(field) is not False for field in ("publication_performed", "patent_filing_performed", "authenticity_verified"))):
                raise ValueError("Release manifest schema is invalid")
            if manifest_path is not None and _read_file(Path(manifest_path)) != manifest_bytes:
                raise ValueError("Release manifest does not match the independently retained manifest")
            files = manifest["files"]
            if (set(files) != set(names) - {MANIFEST_NAME} or not {"README.md", "LICENSE"} <= set(files)
                    or isinstance(manifest.get("file_count"), bool) or not isinstance(manifest.get("file_count"), int)
                    or manifest["file_count"] != len(files)):
                raise ValueError("Release ZIP members do not match the manifest")
            total_bytes = 0
            evidence_sources = []
            for name in sorted(files):
                expected = files[name]
                if (not isinstance(expected, dict) or isinstance(expected.get("size"), bool) or not isinstance(expected.get("size"), int)
                        or not 0 <= expected["size"] <= MAX_FILE_BYTES or not isinstance(expected.get("sha256"), str)
                        or not re.fullmatch(r"[0-9a-f]{64}", expected["sha256"])):
                    raise ValueError("Release manifest contains an invalid file record")
                content = archive.read(name)
                total_bytes += len(content)
                if len(content) != expected["size"] or sha256(content).hexdigest() != expected.get("sha256"):
                    raise ValueError(f"Release content hash or size mismatch: {name}")
                _inspect_content(name, content)
                declaration = _evidence_source(name, content)
                if declaration is not None:
                    evidence_sources.append(declaration)
            if total_bytes != manifest.get("expanded_bytes"):
                raise ValueError("Release expanded size does not match manifest")
            if evidence_sources != manifest.get("evidence_sources"):
                raise ValueError("Release evidence source declarations do not match included reports")
            identity = _source_identity_from_files(files)
            if not isinstance(manifest.get("source_identity"), dict) or manifest["source_identity"].get("working_tree_sha256") != identity:
                raise ValueError("Release source identity does not match packaged source")
    except (zipfile.BadZipFile, KeyError, RuntimeError, NotImplementedError, OSError) as exc:
        raise ValueError("Release is not a valid readable ZIP archive") from exc
    return {"valid": True, "file_count": len(files), "expanded_bytes": total_bytes,
            "source_identity": manifest["source_identity"], "private_paths_excluded": True,
            "verification_scope": "allowlisted paths, exact member set, sizes, SHA-256 hashes, and packaged source fingerprint",
            "authenticity_verified": False, "publication_performed": False}


def _source_identity_from_files(files: dict) -> str:
    digest = sha256()
    for name in sorted(files):
        item = files[name]
        if item.get("role") != _role(name):
            raise ValueError("Release manifest file role does not match its path policy")
        if item["role"] == "source_or_configuration":
            digest.update(name.encode("utf-8") + b"\0" + str(item["size"]).encode("ascii") + b"\0" + item["sha256"].encode("ascii") + b"\0")
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--verify", type=Path, metavar="ZIP", help="Verify an existing bundle without extracting or running it")
    parser.add_argument("--manifest", type=Path, help="Compare against a separately retained manifest when verifying")
    args = parser.parse_args()
    try:
        if args.verify is not None:
            result = verify_release_bundle(args.verify, args.manifest)
        else:
            if args.manifest is not None:
                parser.error("--manifest requires --verify")
            result = build_release_bundle(args.root, args.output_dir)
        print(json.dumps(result, sort_keys=True, indent=2))
        return 0
    except (ValueError, OSError) as exc:
        print(f"Release bundle refused: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
