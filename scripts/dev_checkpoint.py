"""Inspect ARGUS development state without changing the project by default.

This tool does not access account usage limits, schedule jobs, or resume an agent.
Only --write-checkpoint writes a fixed, local status snapshot.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
from http.client import HTTPConnection, HTTPException
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CHECKPOINT = "output/development/checkpoint.json"
CONTINUITY = "docs/DEVELOPMENT_CONTINUITY.md"
SOURCE_FOLDERS = ("app", "components", "hooks", "services", "utils", "tests", "scripts")
SOURCE_CONFIGS = ("package.json", "package-lock.json", "vite.config.ts", "tsconfig.json")
MAX_JSON_BYTES = 2 * 1024 * 1024
MAX_SOURCE_BYTES = 16 * 1024 * 1024
EVIDENCE_FILES = (
    "docs/CURRENT_INVENTION_DISCLOSURE.md",
    "docs/PATENT_STRENGTHENING_ASSESSMENT.md",
    "docs/FUNDAMENTAL_UPGRADE_RESULTS_2026_10_08.md",
    "docs/PROBE_V2_RELEASE_REVIEW.md",
    "docs/VISUALIZATION_UPGRADE_2026_10_11.md",
    "docs/WAVE_PACKET_DEVELOPMENT_RESULTS_2026_10_12.md",
    "research_results/wave_packet_imaging_development_2026_10_12.json",
    "research_results/qualified_wave_packet_imaging_development_2026_10_12.json",
    "research_results/reference_conditioned_confirmation_2026_10_08.json",
    "output/release/fundamental-backend-tests.xml",
)


def bounded_path(root: Path, relative: str) -> Path:
    """Reject traversal and links resolving outside the intended workspace."""
    name = PurePosixPath(relative)
    if "\\" in relative or name.is_absolute() or ".." in name.parts or not name.parts:
        raise ValueError("unsafe relative path")
    # A colon also excludes Windows drive-relative paths on non-Windows hosts.
    if any(":" in part for part in name.parts):
        raise ValueError("unsafe relative path")
    base = root.resolve()
    path = base.joinpath(*name.parts)
    if not path.resolve().is_relative_to(base):
        raise ValueError("path resolves outside workspace")
    return path


def file_status(root: Path, relative: str) -> dict[str, Any]:
    result: dict[str, Any] = {"path": relative, "present": False}
    try:
        path = bounded_path(root, relative)
        if path.is_file():
            stat = path.stat()
            result.update(present=True, bytes=stat.st_size,
                          modified_utc=datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat())
    except (OSError, ValueError):
        result["unavailable"] = True
    return result


def read_json(root: Path, relative: str) -> Any:
    path = bounded_path(root, relative)
    with path.open("rb") as handle:
        data = handle.read(MAX_JSON_BYTES + 1)
    if len(data) > MAX_JSON_BYTES:
        raise ValueError("JSON exceeds inspection size limit")
    return json.loads(data)


def source_hashes(root: Path) -> dict[str, str]:
    sources: dict[str, str] = {}
    for folder in SOURCE_FOLDERS:
        directory = bounded_path(root, f"frontend/{folder}")
        for path in sorted(directory.rglob("*")):
            if path.is_file() and path.suffix in {".ts", ".tsx", ".css", ".js", ".mjs"}:
                relative = path.relative_to(root).as_posix()
                safe = bounded_path(root, relative)
                if safe.stat().st_size > MAX_SOURCE_BYTES:
                    raise ValueError("frontend source exceeds inspection size limit")
                sources[relative] = sha256(safe.read_bytes()).hexdigest()
    for name in SOURCE_CONFIGS:
        relative = f"frontend/{name}"
        path = bounded_path(root, relative)
        if path.is_file():
            if path.stat().st_size > MAX_SOURCE_BYTES:
                raise ValueError("frontend configuration exceeds inspection size limit")
            sources[relative] = sha256(path.read_bytes()).hexdigest()
    return sources


def frontend_checks(root: Path) -> dict[str, Any]:
    result = file_status(root, "output/release/frontend-checks.json")
    if not result["present"]:
        return {**result, "status": "missing"}
    try:
        record = read_json(root, result["path"])
        expected = record.get("source_sha256")
        if not isinstance(expected, dict) or not expected:
            raise ValueError("missing source hashes")
        # Never read a path supplied by the report. Compare to our fixed scopes.
        if any(not isinstance(key, str) or not isinstance(value, str)
               for key, value in expected.items()):
            raise ValueError("invalid source hashes")
        current = source_hashes(root)
        added = set(current) - set(expected)
        removed = set(expected) - set(current)
        changed = {key for key in set(current) & set(expected) if current[key] != expected[key]}
        checks = record.get("checks")
        if not isinstance(checks, list) or any(not isinstance(item, dict) for item in checks):
            raise ValueError("invalid checks")
        task_codes = {item.get("task"): item.get("exit_code") for item in checks}
        passed = (len(checks) == 4 and
                  set(task_codes) == {"test", "typecheck", "lint", "build"} and
                  all(type(code) is int and code == 0 for code in task_codes.values()) and
                  record.get("all_passed") is True and
                  record.get("source_changed_during_run") is False)
        stale = bool(added or removed or changed)
        tests = next((item.get("tests") for item in checks if item.get("task") == "test"), None)
        result.update(status="stale" if stale else ("current_pass" if passed else "current_failed"),
                      recorded_all_passed=passed, source_matches=not stale,
                      added_sources=len(added), removed_sources=len(removed),
                      changed_sources=len(changed),
                      recorded_test_count=tests if type(tests) is int else None)
    except (OSError, ValueError, TypeError, AttributeError):
        result["status"] = "unreadable_or_invalid"
    return result


def parse_git_status(raw: str) -> dict[str, int]:
    counts = {"entries": 0, "staged": 0, "unstaged": 0, "untracked": 0,
              "conflicts": 0, "renamed_or_copied": 0}
    entries = raw.split("\0")
    index = 0
    while index < len(entries):
        entry = entries[index]
        index += 1
        if len(entry) < 3:
            continue
        status = entry[:2]
        counts["entries"] += 1
        if status == "??":
            counts["untracked"] += 1
            continue
        counts["staged"] += int(status[0] != " ")
        counts["unstaged"] += int(status[1] != " ")
        counts["conflicts"] += int(status in {"DD", "AU", "UD", "UA", "DU", "AA", "UU"})
        if "R" in status or "C" in status:
            counts["renamed_or_copied"] += 1
            index += 1  # -z includes the original path as another NUL token.
    return counts


def git_status(root: Path) -> dict[str, Any]:
    try:
        result = subprocess.run(
            ["git", "-c", "core.fsmonitor=false", "status", "--porcelain=v1", "-z", "--untracked-files=all"],
            cwd=root, capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=15, env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"}, check=False,
        )
        if result.returncode:
            return {"available": False}
        return {"available": True, **parse_git_status(result.stdout)}
    except (OSError, subprocess.TimeoutExpired):
        return {"available": False}


def localhost_status(port: int, path: str) -> dict[str, Any]:
    # HTTPConnection follows no redirects and no environment proxy settings.
    result: dict[str, Any] = {"url": f"http://127.0.0.1:{port}{path}"}
    connection = HTTPConnection("127.0.0.1", port, timeout=2)
    try:
        connection.request("GET", path)
        response = connection.getresponse()
        result.update(responding=True, http_status=response.status,
                      successful_response=200 <= response.status < 300)
    except (OSError, ValueError, HTTPException):
        result.update(responding=False, successful_response=False)
    finally:
        connection.close()
    return result


def inspect(root: Path = ROOT, api_port: int = 8001, network: bool = True) -> dict[str, Any]:
    board: dict[str, Any] = file_status(root, "output/release/probe-v2-board-build.json")
    if board["present"]:
        try:
            record = read_json(root, board["path"])
            board.update(recorded_core_installed=record.get("core_installed") is True,
                         recorded_compile_executed=record.get("board_compile_command_executed") is True)
        except (OSError, ValueError, TypeError, AttributeError):
            board["unreadable_or_invalid"] = True
    services = ({"frontend": localhost_status(5173, "/"),
                 "api": localhost_status(api_port, "/health")} if network else {"checked": False})
    return {
        "schema_version": 1,
        "captured_utc": datetime.now(timezone.utc).isoformat(),
        "mode": "read_only_inspection",
        "account_usage": {"observable": False, "automatic_reset_resume": False},
        "git": git_status(root),
        "services": services,
        "frontend_checks": frontend_checks(root),
        "board_build_record": board,
        "evidence_files": [file_status(root, name) for name in EVIDENCE_FILES],
        "evidence_scope": "File presence is not verification of scientific results or physical apparatus performance.",
        "manual_continuation_document": CONTINUITY,
        "checkpoint": {"path": CHECKPOINT, "present": file_status(root, CHECKPOINT)["present"],
                       "written": False},
    }


def write_checkpoint(root: Path, report: dict[str, Any]) -> None:
    target = bounded_path(root, CHECKPOINT)
    target.parent.mkdir(parents=True, exist_ok=True)
    # Recheck after creation; never accept an output directory escaping the root.
    target = bounded_path(root, CHECKPOINT)
    report["checkpoint"].update(present=True, written=True)
    report["mode"] = "explicit_checkpoint_snapshot"
    target.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


def valid_port(value: str) -> int:
    try:
        port = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("port must be an integer") from exc
    if not 1 <= port <= 65535:
        raise argparse.ArgumentTypeError("port must be between 1 and 65535")
    return port


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Print only the machine-readable status report")
    parser.add_argument("--no-network", action="store_true", help="Skip localhost service reachability checks")
    parser.add_argument("--api-port", type=valid_port, default=8001, help="Local API port (default: 8001)")
    parser.add_argument("--write-checkpoint", action="store_true",
                        help=f"Explicitly replace {CHECKPOINT} with this snapshot")
    args = parser.parse_args()
    report = inspect(api_port=args.api_port, network=not args.no_network)
    if args.write_checkpoint:
        write_checkpoint(ROOT, report)
    if args.json:
        print(json.dumps(report, indent=2))
        return
    changes = report["git"]
    print("ARGUS developer checkpoint")
    if changes["available"]:
        print(f"Git: {changes['staged']} staged, {changes['unstaged']} unstaged, "
              f"{changes['untracked']} untracked; {changes['conflicts']} conflicts.")
    else:
        print("Git status unavailable.")
    print(f"Frontend checks: {report['frontend_checks']['status']}.")
    for name in ("frontend", "api"):
        if name in report["services"]:
            service = report["services"][name]
            print(f"{name}: {service['url']} - "
                  f"{service.get('http_status', 'not responding')}")
    print(f"Evidence pointers: {sum(item['present'] for item in report['evidence_files'])} "
          f"of {len(EVIDENCE_FILES)} present; presence does not validate results.")
    print(f"Continuation notes: {CONTINUITY}")
    print(f"Snapshot: {CHECKPOINT} ({'written' if report['checkpoint']['written'] else 'not written'})")
    print("Account quotas/reset times are unavailable; resume development manually when access returns.")


if __name__ == "__main__":
    main()
