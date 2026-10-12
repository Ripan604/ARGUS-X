# ARGUS 7 October 2026 release validation protocol

This is a fixed, synthetic engineering validation of the hardened working tree.
It is not a physical trial, a powered efficacy study, or a patent-novelty test.
The protocol was recorded before executing this release's numerical run.

- Seeds: 64000-64007, not the September development or validation seeds.
- Conditions: nominal; separately generated acquisition with velocity x1.02,
  attenuation x1.04, and noise x2.0 relative to the inference model.
- Policies: legacy_proxy, nuisance_aware, risk_calibration. Each uses the same
  pre-generated feasible diagnostic opportunities for a paired scenario.
- Budget: six observations per policy, twelve diagnostic opportunities per step.
  Fixed budget deliberately does not establish measurement compression.
- Outcomes: attempted/completed runs, execution failures, physical MAP error,
  posterior entropy, empirical R90 coverage, rejection and abstention, and the
  complete per-run trajectories retained by the evaluator.
- Uncertainty: paired case bootstrap, 10,000 resamples with the evaluator's fixed
  seed, percentile 95% intervals. Report intervals crossing zero as inconclusive.
- Timing: shared Windows workstation, not dedicated real-time hardware. Report
  computation as descriptive engineering data, not a deployment guarantee.
- Truth: used by acquisition and final scoring, not by candidate selection.
- Source boundary: hash scripts/research_validation.py and every backend/app
  Python file before execution; refuse publication use if source changes during
  the run. Preserve configuration and command in the artifact.
- No tuning after looking at these outcomes, no seed removal, no substitution of
  simulated missing physical responses, and no relabeling of evidence source.

Command:

```powershell
.venv\Scripts\python.exe scripts\research_validation.py --seed 64000 --cases 8 --steps 6 --candidates 12 --variants legacy_proxy nuisance_aware risk_calibration --output research_results/release_validation_2026_10_07.json
```

The September artifacts remain historical. Their numerical results must not be
attributed to this hardened source tree. A successful software regression or a
low-error single-seed demo cannot establish field defect-localization accuracy.

## Physical closure study

Use the actual exciter, receiver, trigger, fixture and panel. Retain independently
measured specimen/defect geometry, healthy reference recordings, source sampling
rate, excitation window, normalization/transfer calibration and environmental
metadata. Acquire all candidate outcomes required for offline policy replay, not
only outcomes chosen by ARGUS. Hold out entire specimens or defect locations,
keeping all related repeats/channels together. Compare adaptive and fixed/random
policies under equal action opportunities and costs, retaining failures.

Primary physical outcomes must be declared before acquisition: position error vs
budget, success at a justified tolerance, empirical containment coverage,
false-confidence and rejection/abstention, plus comparison with an appropriate
independent inspection/reference method. A representative study of damage
existence and minimum detectable size requires additional healthy/defective
labels; the present one-scatterer locator cannot substitute for it.
