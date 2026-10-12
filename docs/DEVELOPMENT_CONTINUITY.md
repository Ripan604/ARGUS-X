# ARGUS development continuity

ARGUS can retain a local development checkpoint so another session can resume with
the actual source and evidence state. The assistant cannot inspect ChatGPT account
usage, know a reset time, hibernate across a stopped session, or automatically
resume when a quota resets. This workflow installs no recurring background job.
Check account usage in the application and send `continue` when access is available.

## Inspect the current workspace

From the project root, run:

```powershell
.venv\Scripts\python.exe scripts\dev_checkpoint.py
.venv\Scripts\python.exe scripts\dev_checkpoint.py --json --no-network
```

The default command is read-only. It reports aggregate Git change counts, checks
the frontend on `127.0.0.1:5173` and the API health route on `127.0.0.1:8001`, and
compares the frontend's retained check hashes to the current source scopes. Use
`--api-port 8000` when the launcher uses that port. It does not start or stop either
service, contact external hosts, follow HTTP redirects, inspect environment-file
contents, print changed filenames, or copy credentials into the report.

`current_pass` means that all four retained frontend checks passed, source was
stable during that check run, and the current file contents and file set match the
record. `stale` means that at least one recorded source was changed or removed,
or a source was added. The script does not rerun checks. Other status values mean
that evidence is missing, invalid, or records failed checks. Git counts can overlap:
a file can have both staged and unstaged changes.

The board-build fields describe the retained build record, not a new compilation.
Evidence pointers report presence and timestamps, not review, reproducibility,
sensor authenticity, patentability, or measured performance. Older test records
must not be treated as proof that newer source passed.

## Save an explicit checkpoint

```powershell
.venv\Scripts\python.exe scripts\dev_checkpoint.py --write-checkpoint
```

This explicitly replaces `output/development/checkpoint.json` with a small status
snapshot. The fixed target must resolve inside this workspace. It contains no
environment variables, file contents, service response bodies, or Git filenames.
The snapshot is historical as soon as files change; inspect again on resumption.
The manual checkpoint below carries the reasoning that a status snapshot cannot.

## Manual checkpoint

Update this section before stopping a development session. Keep measured results
and synthetic results separate, retain negative findings, and preserve unrelated
changes in the shared dirty working tree.

- Current checkpoint: 12 October 2026. Continue scientific development from the
  qualified wave-packet results and preserve source-bound checks and limitations.
- Completed UI baseline: restored 3D representation, synchronized 2D/3D selection,
  probability profiles and CSV export, preserved camera, touch gesture hardening.
  Direct 3D inspection now picks the visible relief and links the same 2D/profile
  cell, with keyboard navigation. Latest retained frontend checks passed 88 tests,
  type checking, lint and build; the status script determines current freshness.
  The subsequent visual refinement shares a graphite/teal palette across the
  landing, workspace and spatial panels; read `docs/VISUAL_AESTHETICS_2026_10_12.md`.
  Its final source-bound frontend run also passed all 88 tests and other checks.
- Scientific boundary: reference-conditioned measured replay remains experimental.
  Read `docs/FUNDAMENTAL_UPGRADE_RESULTS_2026_10_08.md` before changing performance
  claims. Improved visual presentation is not evidence of patent novelty.
- Latest measured development: read
  `docs/WAVE_PACKET_DEVELOPMENT_RESULTS_2026_10_12.md`. The original packet branch
  failed to improve localization. Restricting images to healthy-qualified paths
  improved directional 40 C mean error to 63.31 mm versus paired RAPID 302.97 mm,
  on four previously seen cases. Isotropic 60 C remained worse than RAPID.
  Only two of six calibrations qualify, each branch covers four of twelve damage
  conditions, and D16 remains a 143.96 mm directional error. There is one plate.
  No damage detector or field-calibrated probabilities are established.
- Source preservation: two measured results remain unchanged, with six and nine
  exact code/protocol snapshots under `output/research_sources/` and verified
  SHA-256 manifests. Current code additionally rejects signed-integer amplitude
  overflow and invalid calibration path indices. Those input-contract fixes do
  not alter valid recorded calibration numerics. Do not rerun into existing
  scientific artifacts or treat a previously inspected dataset as untouched.
- Hardware boundary: inspect `output/release/probe-v2-board-build.json` and
  `docs/PROBE_V2_RELEASE_REVIEW.md`; host mocks are not physical board validation.
- Browser visual verification: the previous session had no connected browser
  surface. Check current browser availability before claiming visual QA.
- Latest continuity changes: `scripts/dev_checkpoint.py` adds read-only status
  inspection and an explicit snapshot option; `backend/tests/test_dev_checkpoint.py`
  covers freshness, path bounds, secret omission, redirect handling and safe writes.
  Record other changes from the active development session here before stopping.
- Continuity verification: `.venv\Scripts\python.exe -m pytest
  backend/tests/test_dev_checkpoint.py -q -o addopts=""` passed 11 tests.
  A default status inspection returned HTTP 200 from the frontend and API and
  created no checkpoint snapshot. These are continuity-tool checks, not full
  project validation. Record source changes after checks before reusing evidence.
- Current focused backend verification: wave-packet imaging, qualification,
  existing measured-wave replay and continuity regressions passed 48 tests;
  retained XML is
  `output/release/development-tests-2026-10-12.xml`. Read its actual count instead
  of assuming older full-suite counts apply to the new source.
- Final source review verified all 15 archived source hashes, all 12 recorded
  calibration objects against the hardened index contract, and all six healthy
  qualification outputs unchanged after that input-contract fix. No damaged
  receiver was used to fit or recheck those qualification outputs.
- Next bounded task: measured electrical-source timing/gain correction that never
  fits the damaged receiver, then healthy-only packet/mode identification and
  model identifiability. Freeze the revised policy before uninspected data or
  blind independent-panel trials. The reference norm gate has no independent
  performance ablation here: its flagged path was already outside model inliers.
  Browser visual verification and a real apparatus campaign remain outstanding.

## Resume

1. Read this checkpoint, inspect Git status, and run `dev_checkpoint.py`.
2. Reassess stale checks and preserve work from other contributors.
3. Continue the recorded task. Run checks appropriate to the actual changes.
4. Record the result and optionally refresh the explicit checkpoint snapshot.

Start local services, if needed, with `.venv\Scripts\python.exe run_argus.py`.
Refresh frontend checks, when appropriate, with
`.venv\Scripts\python.exe scripts\run_frontend_release_checks.py`.
