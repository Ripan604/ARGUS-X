from __future__ import annotations

import io
import json
from pathlib import Path
import shutil
import subprocess
import zipfile

import pytest

from scripts.build_release_bundle import (
    MANIFEST_NAME, allowed_path, build_release_bundle, select_files, verify_release_bundle,
)


def write(root: Path, name: str, content: str = "fixture\n") -> Path:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


@pytest.fixture
def source(tmp_path):
    write(tmp_path, "README.md", "ARGUS review fixture\n")
    write(tmp_path, "LICENSE", "MIT fixture\n")
    write(tmp_path, "backend/app/engine.py", "value = 1\n")
    write(tmp_path, "backend/tests/test_engine.py", "def test_fixture():\n    assert True\n")
    write(tmp_path, "backend/requirements.txt", "numpy>=1.24\n")
    write(tmp_path, "backend/requirements.lock.txt", "numpy==2.0.0\n")
    write(tmp_path, "frontend/package.json", '{"name":"argus"}')
    write(tmp_path, "frontend/package-lock.json", '{"lockfileVersion":3}')
    write(tmp_path, "frontend/.env.example", "NEXT_PUBLIC_ARGUS_API_URL=http://localhost:8000\n")
    write(tmp_path, "frontend/app/page.tsx", "export default function Page() { return null; }\n")
    write(tmp_path, "scripts/demo.py", "print('fixture')\n")
    write(tmp_path, "firmware/esp32/argus_probe.ino", "void setup() {}\n")
    write(tmp_path, "docs/CURRENT_INVENTION_DISCLOSURE.md", "Current technical disclosure\n")
    write(tmp_path, "docs/RELEASE_READINESS_REPORT.md", "Local readiness; no publication\n")
    write(tmp_path, "paper/main.tex", "\\documentclass{article}\n")
    write(tmp_path, "models/metrics.json", '{"r2":0.5}')
    write(tmp_path, "research_results/release_validation_2026_10_07.json", '{"evidence_source":"simulated","cases":2}')
    return tmp_path


def rewrite_archive(path: Path, change):
    with zipfile.ZipFile(path) as archive:
        files = {name: archive.read(name) for name in archive.namelist()}
    change(files)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in files.items():
            # Keep deliberately hostile raw names even on Windows, where the
            # ordinary ZipInfo constructor normalizes backslashes.
            member = zipfile.ZipInfo("safe")
            member.filename = name
            member.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(member, content)


def test_build_verify_and_selection_are_deterministic(source):
    before = [path.relative_to(source).as_posix() for path in select_files(source)]
    first = build_release_bundle(source, created_at="2026-10-07T00:00:00+00:00")
    first_bytes = Path(first["archive"]).read_bytes()
    second = build_release_bundle(source, created_at="2026-10-07T00:00:00+00:00")
    assert Path(second["archive"]).read_bytes() == first_bytes
    assert first["valid"] and first["private_paths_excluded"]
    assert before == sorted(before)
    assert before == [path.relative_to(source).as_posix() for path in select_files(source)]
    manifest = json.loads(Path(first["manifest"]).read_text())
    assert manifest["created_at_utc"].endswith("+00:00")
    assert "backend/requirements.lock.txt" in manifest["files"]
    assert manifest["publication_performed"] is False
    assert manifest["patent_filing_performed"] is False
    assert manifest["authenticity_verified"] is False
    assert any(record["declared_evidence_source"] == "simulated" for record in manifest["evidence_sources"])
    assert verify_release_bundle(first["archive"], first["manifest"])["valid"]


@pytest.mark.parametrize("name", [
    ".env", "frontend/.env.local", "backend/app/.env.production", ".aws/credentials",
    "frontend/node_modules/vendor/index.js", "backend/app/vendor/module.py", "backend/app/__pycache__/test.py",
    "models/model.pt", "models/model.npz", "models/model.joblib", "models/credentials.json",
    "backend/app/secrets/private.py", "backend/data/argus.db", "paper/main.pdf", "paper/archive.zip",
    "datasets/generated/bank.json", "output/release/previous.zip", "docs/PATENT_DRAFT.md",
])
def test_release_excludes_private_generated_and_binary_inputs(source, name):
    write(source, name, "private or generated fixture")
    selected = [path.relative_to(source).as_posix() for path in select_files(source)]
    assert name not in selected
    assert allowed_path(name) is False


def test_verify_rejects_hash_tampering(source):
    result = build_release_bundle(source)
    rewrite_archive(Path(result["archive"]), lambda files: files.__setitem__("backend/app/engine.py", b"value = 999\n"))
    with pytest.raises(ValueError, match="hash or size mismatch"):
        verify_release_bundle(result["archive"])


@pytest.mark.parametrize("name", ["../README.md", "/README.md", "C:/README.md", "backend\\app\\evil.py", "frontend/.env.local", "models/credentials.json"])
def test_verify_rejects_traversal_and_private_members(source, name):
    result = build_release_bundle(source)
    rewrite_archive(Path(result["archive"]), lambda files: files.__setitem__(name, b"must not be extracted"))
    with pytest.raises(ValueError, match="unsafe|private|disallowed"):
        verify_release_bundle(result["archive"])
    assert not (source.parent / "README.md").exists()


def test_verify_rejects_duplicate_members(source):
    result = build_release_bundle(source)
    with pytest.warns(UserWarning, match="Duplicate"):
        with zipfile.ZipFile(result["archive"], "a") as archive:
            archive.writestr("README.md", b"duplicate")
    with pytest.raises(ValueError, match="duplicate"):
        verify_release_bundle(result["archive"])


def test_verify_rejects_manifest_rewrite_against_retained_copy(source):
    result = build_release_bundle(source)
    def alter(files):
        manifest = json.loads(files[MANIFEST_NAME])
        manifest["created_at_utc"] = "2020-01-01T00:00:00+00:00"
        files[MANIFEST_NAME] = json.dumps(manifest).encode()
    rewrite_archive(Path(result["archive"]), alter)
    with pytest.raises(ValueError, match="independently retained"):
        verify_release_bundle(result["archive"], result["manifest"])


def test_verify_rejects_forged_evidence_source_labels(source):
    result = build_release_bundle(source)
    def alter(files):
        manifest = json.loads(files[MANIFEST_NAME])
        record = next(item for item in manifest["evidence_sources"] if item["declared_evidence_source"] == "simulated")
        record["declared_evidence_source"] = "physical_measurement"
        files[MANIFEST_NAME] = json.dumps(manifest).encode()
    rewrite_archive(Path(result["archive"]), alter)
    with pytest.raises(ValueError, match="evidence source declarations"):
        verify_release_bundle(result["archive"])


def test_verify_rejects_expansion_bomb_before_loading_manifest(tmp_path, monkeypatch):
    import scripts.build_release_bundle as builder
    monkeypatch.setattr(builder, "MAX_BUNDLE_BYTES", 4_096)
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("README.md", b"0" * 40_000)
    path = tmp_path / "bomb.zip"
    path.write_bytes(payload.getvalue())
    with pytest.raises(ValueError, match="Expanded"):
        verify_release_bundle(path)


def test_release_refuses_embedded_private_keys(source):
    write(source, "models/metrics.json", '"-----BEGIN ' + 'PRIVATE KEY-----\\nprivate"')
    # A private key in any text asset is blocked even when its suffix is safe.
    write(source, "docs/SECURITY.md", "-----BEGIN " + "PRIVATE KEY-----\nprivate\n")
    with pytest.raises(ValueError, match="private key"):
        build_release_bundle(source)


def test_release_output_cannot_escape_output_release(source):
    with pytest.raises(ValueError, match="inside output/release"):
        build_release_bundle(source, source.parent / "external-release")


def test_source_identity_changes_with_dirty_untracked_and_deleted_source(source):
    if not shutil.which("git"):
        pytest.skip("git not installed")
    def git(*arguments):
        subprocess.run(["git", *arguments], cwd=source, capture_output=True, check=True)
    git("init")
    git("add", ".")
    git("-c", "user.name=Release Test", "-c", "user.email=release@example.invalid", "commit", "-m", "fixture")
    initial = build_release_bundle(source)["source_identity"]
    assert initial["dirty_source"] is False
    write(source, "backend/app/engine.py", "value = 2\n")
    dirty = build_release_bundle(source)["source_identity"]
    assert dirty["dirty_source"] is True
    assert initial["working_tree_sha256"] != dirty["working_tree_sha256"]
    write(source, "backend/app/new.py", "value = 3\n")
    untracked = build_release_bundle(source)["source_identity"]
    assert "backend/app/new.py" in untracked["untracked_source_files"]
    assert dirty["working_tree_sha256"] != untracked["working_tree_sha256"]
    (source / "backend/app/engine.py").unlink()
    deleted = build_release_bundle(source)["source_identity"]
    assert deleted["dirty_source"] is True
    assert deleted["working_tree_sha256"] != untracked["working_tree_sha256"]
