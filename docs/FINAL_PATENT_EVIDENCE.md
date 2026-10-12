# Final patent-review evidence and reproducibility

**Historical source boundary:** the 306-test and 192-run figures below describe
the pre-v2 revision. The later apparatus and expanded comparison are reported
separately in PROBE_V2_RELEASE_REVIEW.md. Original source hashes remain authoritative.

The final technical contribution is documented in ARGUS_FINAL_TECHNICAL_DISCLOSURE.
It is an optional task-conditioned reference selector, not a new general Bayesian
principle or a validated physical defect-localization upgrade.

## Implementation mapping

| Element | Source | Actual support |
|---|---|---|
| Full-grid target matrix and reference ranking | backend/app/active_learning/reference_design.py | Covariance conditioning, costs, all 400 default cells, alternatives and rank/span |
| Engine invocation | backend/app/services/engine.py | Direct calibration only, feasible nominated diagnostic, explicit optional flag |
| Propagation measurement update | backend/app/inference/nuisance_posterior.py | Correlated first-order update; one delay is one observation |
| API/CLI activation | schemas/api.py; session_manager.py; scripts/demo_simulation.py | Persisted enable_task_conditioned_calibration flag and CLI demonstration |
| Legacy acquisition boundary | hardware/devices.py; firmware/esp32/README.md | Post-excitation example blocked before localization actuation |
| Functional regressions | backend/tests/test_reference_design.py | Monotonic/PSD variance, full mass, ordering, costs, immutability, observability and engine use |
| New comparative study | scripts/validate_task_calibration.py | Three equal-budget policies and source-bound per-case outputs |

## Evidence levels

1. Mathematical invariants apply to the declared local Gaussian model.
2. Twelve new regression cases passed; the full final suite records 306 passes,
   one refused-legacy-checkpoint skip, and a nonfatal framework warning.
3. The 64-seed calibration comparison is synthetic scalar-arrival evidence.
4. The existing 48-run hidden-defect evaluation is pre-extension historical evidence.
5. Neither experiment is measured apparatus or field performance.

| Calibration policy | Mean target arrival RMSE | Mean velocity absolute error | Mean timing absolute error |
|---|---|---|---|
| Repeated short reference (failure control) | 454.43 microseconds | 20.06 m/s | 121.45 microseconds |
| Cyclic first-feasible (primary baseline) | 279.65 microseconds | 14.10 m/s | 136.20 microseconds |
| Task-conditioned reference | 200.57 microseconds | 11.80 m/s | 144.89 microseconds |

Primary paired advantage: 79.07 microseconds, 95% bootstrap interval [50.27,110.35].
All 192 runs completed. The worsened timing-parameter error is retained; task
prediction improves without claiming every parameter improves. The first
repeated-reference pilot is not substituted for the cyclic baseline.

## Reproduction and source boundary

```powershell
.venv\Scripts\python.exe -m pytest backend\tests -q -o addopts="" --junitxml=output/release/final-backend-tests.xml
.venv\Scripts\python.exe scripts\validate_task_calibration.py
.venv\Scripts\python.exe scripts\demo_simulation.py --task-calibration --preset easy --seed 17 --experiments 8
```

The model-study report is research_results/final_task_calibration_2026_10_07.json.
Check source_changed_during_run=false and compare every retained backend source
hash before reusing its results. Protocol and acquisition assumptions are in
FINAL_CALIBRATION_PROTOCOL.md. Preserve failures and complete per-case traces.

The final source/evidence ZIP and its independent manifest retain exact source
versions and exclude private environment files, credentials and model binaries.
Integrity is not an institutional signature or proof of sensor authenticity.
External publication and patent filing remain unperformed.
