# Prospective extended reference-design protocol

This protocol is written before the frozen extended study. It tests synthetic
direct-reference calibration and propagation prediction. It does not establish
defect localization accuracy, measured apparatus performance, novelty, or
patentability. The earlier 83000-series study remains a separate artifact.

## Fixed design

- Forty-eight new independent seed clusters: `970001 + 31*i`, `i=0..47`.
- Four fixed diagnostic geometries on a 0.60 by 0.40 m panel: short corner,
  opposite corners, crossed interior probes, and same-side probes. Every target
  uses a nonuniform 20 by 20 probability grid comprising three Gaussian lobes
  plus a nonzero background. All posterior cells contribute to each outcome.
- Two prespecified acquisition regimes: sealed nominal-prior noise and twice
  that acquisition standard deviation. Neither regime changes the estimator's
  assumed-noise contract. Nominal acquisition uses sealed true velocity; it
  therefore is not an exactly matched Gaussian oracle.
- Five policies: existing cyclic order, seeded random references, scaled A-optimal,
  scaled D-optimal, and the implemented task-conditioned selector. All use three
  identical reference opportunities and the same bank of 0.18, 0.36, 0.54 m paths.
- Total final scope: 48 x 4 x 2 x 5 = 1,920 runs and 5,760 opportunities.
- Current sample rate 16 kHz, assumed quality 0.75, cost conversion
  0.0001 m² per existing ARGUS acquisition-cost unit, and three-shot budgets are
  fixed before results. No oracle, seed filtering, tuning, or result-based
  extensions are included.

## Sealing and observation contract

Before running any policy, generate every case's true velocity and timing,
initial means and correlated covariance, nonuniform posterior, target geometry,
reference bank, starting pose, three Gaussian innovations, and random policy's
indices. Retain their canonical SHA-256 seal and the full realization.

The truth draws use the declared joint Gaussian prior, with velocity clipped to
100–330 m/s and timing to 0.05–2.5 ms. Initial means, covariance magnitudes, and
correlations vary prospectively. Clipping is a declared departure from an exact
Gaussian prior, not a reason to exclude a run.

An acquisition is the nonlinear scalar delay `t_true + d/v_true + sigma_true*z`.
True acquisition sigma is computed once from the sealed true speed and declared
initial pose/timing noise, divided by sqrt(0.75), then multiplied by the regime's
fixed noise multiplier. It remains independent of every changing policy state.
The same step's innovation and true sigma are used for all five paired policies.

The implementation's current estimator-based direct-reference noise estimate
and quality 0.75 are used for both candidate design and accepted calibration
updates. They never receive true velocity or true acquisition sigma. Every trace
retains the actual-to-assumed noise ratio so nominal approximation and deliberate
noise mismatch are visible. Sealed truth is used only to create measurements and
score held-out target predictions.

Each executed reference is charged the existing additional-experiment, movement,
energy, and duration cost from `DecisionLossModel`, with the same conversion.
Movement is measured from each policy's preceding acquired pose. Failed
calibration consumes its opportunity and full actuation cost. A failed selection
consumes an opportunity and the declared additional-experiment cost; the state
remains unchanged. Failures are retained in all primary summaries.
The cyclic and random policies choose without optimizing cost, but they are
charged the same actual cost formula and are included in the same objective.

## Strong baseline mathematics

Raw covariance trace or determinant of velocity and timing mixes units. A and D
baselines therefore transform covariance using scales `(v_ref, D/v_ref)`, where
`v_ref` is the sealed initial speed mean and `D` is the panel diagonal. The scales
are fixed across the paired policies and never depend on a diagnostic posterior.

Every baseline candidate uses the same correlated first-order reference update
and assumed noise/quality as the task selector. A-optimal minimizes
`D² trace(C_scaled_after) + acquisition_cost_m²`. D-optimal minimizes
`D² sqrt(det(C_scaled_after)) + acquisition_cost_m²`. At zero cost the criteria
are standard A and D design rankings. Their cost-bearing proxies have declared
m² design units and are not claimed to be squared localization error. They are
strong posterior-independent comparator objectives, not hyperparameters tuned
to favor any policy.

## Outcomes and inference

The first primary outcome is posterior-weighted held-out diagnostic arrival
RMSE in microseconds across all 400 target cells. A second primary outcome is
`v_ref² * target_arrival_MSE + actual_total_cost_m²`, using the same sealed speed
scale across policies. It is a path-equivalent propagation objective; it is not
defect-position error or physical risk.

Retain velocity error, timing error, modeled target variance, posterior-weighted
95% latent-arrival interval coverage, actual costs, rejected opportunities,
selection and update latency, failure latency, and per-step alternatives. The
coverage measure compares true latent arrival to first-order parameter intervals,
not future noisy waveform coverage or empirical defect-confidence calibration.

Report task-minus-comparator performance as comparator minus task, so positive
advantages favor the task method. Form a seed-level average across geometries
and regimes; bootstrap independent seed clusters 4,000 times with fixed bootstrap
seed 118701. Retain each seed's actual contrast and separate geometry-by-regime
tables, together with regime and pooled contrasts. The intervals are exploratory
and unadjusted for multiple comparisons. Negative, null, heterogeneous, and
failed-case outcomes remain in the report; no claims require favorable results.

## Reproduction and source boundary

```powershell
.venv\Scripts\python.exe -m pytest backend\tests\test_extended_reference_validation.py -q -o addopts=""
.venv\Scripts\python.exe scripts\validate_reference_design_extended.py
```

The default output is
`research_results/extended_reference_design_2026_10_07.json`. The test suite runs
small fixtures without writing final evidence. Hash this protocol, the owned
study script and tests, and every `backend/app` Python source before and after
the final run. A changed source fingerprint invalidates attribution to a frozen
version; preserve that output and rerun only after edits stop. A seal or source
hash establishes reproducibility, not hardware provenance or institutional
review. Expected runtime is well below ten minutes on the current CPU.
