"""Developer checkpoint safety and evidence freshness regressions."""
from hashlib import sha256
import json
from pathlib import Path

import pytest

from scripts import dev_checkpoint as checkpoint


def _frontend_record(root: Path) -> Path:
    source = root / "frontend/app/page.tsx"
    source.parent.mkdir(parents=True)
    source.write_text("export default function Page() { return null; }", encoding="utf-8")
    report = root / "output/release/frontend-checks.json"
    report.parent.mkdir(parents=True)
    report.write_text(json.dumps({
        "source_sha256": {"frontend/app/page.tsx": sha256(source.read_bytes()).hexdigest()},
        "checks": [{"task": task, "exit_code": 0, "tests": 81}
                   for task in ("test", "typecheck", "lint", "build")],
        "all_passed": True, "source_changed_during_run": False,
    }), encoding="utf-8")
    return report


def test_current_frontend_record_detects_changed_removed_and_added_sources(tmp_path):
    _frontend_record(tmp_path)
    assert checkpoint.frontend_checks(tmp_path)["status"] == "current_pass"
    source = tmp_path / "frontend/app/page.tsx"
    source.write_text("changed", encoding="utf-8")
    assert checkpoint.frontend_checks(tmp_path)["changed_sources"] == 1
    source.unlink()
    (source.parent / "other.tsx").write_text("new", encoding="utf-8")
    status = checkpoint.frontend_checks(tmp_path)
    assert status["status"] == "stale"
    assert status["added_sources"] == status["removed_sources"] == 1


def test_freshness_never_reads_paths_from_artifact(tmp_path):
    report = _frontend_record(tmp_path)
    data = json.loads(report.read_text(encoding="utf-8"))
    data["source_sha256"]["../../credentials"] = "not-a-hash"
    report.write_text(json.dumps(data), encoding="utf-8")
    result = checkpoint.frontend_checks(tmp_path)
    assert result["status"] == "stale"
    assert result["removed_sources"] == 1


def test_new_frontend_diagnostic_script_invalidates_retained_checks(tmp_path):
    _frontend_record(tmp_path)
    assert checkpoint.frontend_checks(tmp_path)["status"] == "current_pass"
    script = tmp_path / "frontend/scripts/check-hydration-live.mjs"
    script.parent.mkdir(parents=True)
    script.write_text("export {};", encoding="utf-8")
    result = checkpoint.frontend_checks(tmp_path)
    assert result["status"] == "stale"
    assert result["added_sources"] == 1


def test_git_counts_handle_rename_path_and_overlapping_changes():
    raw = "R  renamed.txt\0old.txt\0 M changed.txt\0MM both.txt\0?? new.txt\0UU conflict.txt\0"
    result = checkpoint.parse_git_status(raw)
    assert result == {"entries": 5, "staged": 3, "unstaged": 3, "untracked": 1,
                      "conflicts": 1, "renamed_or_copied": 1}


def test_read_only_inspection_does_not_create_output_or_expose_environment(tmp_path, monkeypatch):
    monkeypatch.setenv("ARGUS_API_TOKEN", "secret-sentinel")
    monkeypatch.setattr(checkpoint, "git_status", lambda root: {"available": False})
    report = checkpoint.inspect(tmp_path, network=False)
    assert not (tmp_path / "output").exists()
    assert "secret-sentinel" not in json.dumps(report)
    assert report["account_usage"] == {"observable": False, "automatic_reset_resume": False}
    assert report["checkpoint"]["written"] is False


def test_explicit_checkpoint_writes_only_fixed_workspace_target(tmp_path, monkeypatch):
    monkeypatch.setattr(checkpoint, "git_status", lambda root: {"available": False})
    report = checkpoint.inspect(tmp_path, network=False)
    checkpoint.write_checkpoint(tmp_path, report)
    target = tmp_path / checkpoint.CHECKPOINT
    assert json.loads(target.read_text(encoding="utf-8"))["checkpoint"]["written"] is True
    assert len(list(tmp_path.rglob("*.json"))) == 1


@pytest.mark.parametrize("relative", ["../secret", "/secret", "C:/secret", "frontend\\..\\secret"])
def test_bounded_paths_reject_escape(tmp_path, relative):
    with pytest.raises(ValueError):
        checkpoint.bounded_path(tmp_path, relative)


def test_localhost_check_does_not_follow_redirect_or_read_body(monkeypatch):
    calls = []

    class Connection:
        def __init__(self, host, port, timeout):
            calls.append((host, port, timeout))

        def request(self, method, path):
            calls.append((method, path))

        def getresponse(self):
            return type("Redirect", (), {"status": 302})()

        def close(self):
            calls.append("closed")

    monkeypatch.setattr(checkpoint, "HTTPConnection", Connection)
    report = checkpoint.localhost_status(8001, "/health")
    assert report["responding"] is True
    assert report["successful_response"] is False
    assert calls == [("127.0.0.1", 8001, 2), ("GET", "/health"), "closed"]


def test_malformed_local_http_response_is_reported_without_crashing(monkeypatch):
    class Connection:
        def __init__(self, *args, **kwargs):
            self.closed = False

        def request(self, method, path):
            raise checkpoint.HTTPException("invalid status line")

        def close(self):
            self.closed = True

    monkeypatch.setattr(checkpoint, "HTTPConnection", Connection)
    result = checkpoint.localhost_status(8001, "/health")
    assert result["responding"] is False
    assert result["successful_response"] is False
