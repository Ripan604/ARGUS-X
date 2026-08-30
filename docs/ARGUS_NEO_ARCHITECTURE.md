# ARGUS NEO architecture

ARGUS NEO extends the existing closed-loop locator into a resource-bounded
research platform that distinguishes uncertainty about the structure from
uncertainty about the inspection system. It remains CPU-first, local and
backward compatible.

## Joint state

```text
structural Z
  location grid + radius/severity/type hypotheses

metrology η
  velocity, attenuation, timing, source/receiver coupling, gain,
  noise, pose and temperature proxy distributions

model discrepancy δ
  online residual model indexed by frequency, path and geometry

joint approximation
  p(Z, η, δ | D) ≈ p_grid(Z | D, η, δ) q(η | D) q(δ | residuals)
```

The practical engine uses a normalized spatial grid plus factorized Gaussian
nuisance variables and an online residual ensemble. A particle interface
provides an interchangeable joint representation without requiring MCMC for
the live demonstration.

## Closed-loop control

```text
observation
   -> integrity and quality proxies
   -> discrepancy/OOD assessment
   -> nuisance update and structural likelihood update
   -> separate U_structural and U_metrology
   -> dual-control mode selection
        diagnostic | calibration | verification | exploration
   -> candidate constraints
   -> counterfactual predictive distributions over top hypotheses and η
   -> objective: information | Bayes risk | worst case | compression | multiobjective
   -> optional horizon rollout and waveform/geometry refinement
   -> model-fidelity selection
   -> structured explanation + tamper-evident ledger entry
   -> execute/replay/acquire or abstain
```

### Inference layer

- `StructuralPosterior`: normalized grid, credible region, modal hypotheses and
  conservative quality-weighted updates.
- `NuisancePosterior`: factorized bounded Gaussian estimates with uncertainty
  contributions and calibration-specific Bayesian updates.
- `JointInferenceState`: one versioned serialization boundary for structural,
  metrology, discrepancy, OOD and quality state.
- `ParticleInferenceEngine`: seeded samples for posterior-predictive planning.
- `CalibrationEngine`: direct-path/repeat/reference evidence updates nuisance
  variables without pretending it is defect evidence.

### Dual control

`AdaptiveDualControlManager` compares normalized structural ambiguity,
metrology predictive-variance contribution, OOD/model trust and action value.
Both threshold and decision-value modes return a typed action and a structured
reason. Calibration actions preferentially reduce nuisance uncertainty; their
measurements are not recursively multiplied into the defect grid unless they
also satisfy diagnostic validity rules.

### Counterfactual planner

For top hypotheses and nuisance particles, each feasible action produces a
predictive response distribution. Pairwise Jensen–Shannon and Bhattacharyya
separation, approximate expected entropy reduction, Bayes-risk reduction,
coverage and calibration value are balanced against movement, remount, time,
energy, redundancy, unsupported-model and safety costs. Every number used in
ranking is returned in the explanation object.

### Waveform and geometry co-design

The experiment schema supports tone bursts, chirps, Ricker impulses,
multisines, phase-coded, complementary-coded and spectrally notched signals.
Fast mode uses a reproducible coarse bank; research mode performs bounded
successive refinement. `ExperimentConstraintEngine` enforces signal, geometry,
sensor and virtual no-go restrictions before scoring.

### Multi-fidelity twin and trust

All forward models implement one prediction contract and advertise cost,
domain and uncertainty metadata:

- level 0 analytical signatures;
- level 1 existing waveform simulator;
- level 2 optional CPU surrogate/ensemble;
- level 3 imported offline response bank.

The fidelity controller uses posterior concentration, candidate rivalry,
domain support, cache state and discrepancy. An online ridge/ensemble residual
model produces corrected prediction, residual uncertainty and model trust.

### OOD and abstention

A robust residual-z baseline and a conformal/ensemble score are reported
separately and combined conservatively. The status is `NOMINAL`, `CAUTION`,
`OUT_OF_DISTRIBUTION` or `ABSTAIN`. High OOD blocks confident structural output
and routes control to calibration, verification or escalation.

### Planning horizon and stopping

Horizon 1–3 uses bounded beam rollout rather than a full POMDP. Stop decisions
consider posterior mass, credible area, entropy, expected value of another
measurement, budget, Bayes risk and OOD. A typed reason is always recorded.

## Research infrastructure

- `CounterfactualDataset` seals truth while serving only selected actions.
- Synthetic banks are deterministic, chunked and resumable.
- A SQLite-backed local job runner supports benchmark, calibration, ablation,
  bank generation and surrogate training with progress/cancellation.
- Benchmarks use the same sealed scenarios and criteria for every policy.
- Simulation-based calibration reports rank histograms, coverage and ECE.
- Fault injection and failure classification preserve adverse results.
- A model registry records artifact identity, data hashes, domain and metrics.
- A deterministic memory/disk prediction cache reports hit rate.

## Evidence and reproducibility

Every accepted observation produces an append-only SHA-256 ledger entry linked
to its predecessor. The record includes action, data hashes, configurations,
posterior hashes, nuisance/OOD/model state, score components, model fidelity,
software version and seed. Verification returns the first broken record.
Research bundles contain session state, histories, configuration, ledger,
summaries and a manifest and can be imported into a new replayable session.

## Application surfaces

- Mission Control: current belief, uncertainty split, trust, action and result.
- ARGUS Brain: hypotheses, metrology, OOD, utility decomposition, alternatives
  and predicted outcomes.
- Digital Twin, Signals, Experiments and belief timeline.
- Benchmark, Calibration, Ablation and Failure labs.
- Innovation Evidence and Evidence Ledger.
- `/probe`: responsive browser smart probe with capability detection,
  microphone/camera/motion/orientation, manual fallback and heartbeat.
- `run_edge_node.py`: reconnecting local acquisition node for Laptop B.

All conclusions and exports identify their evidence source as simulated,
replayed measured data, live commodity sensor or future NDE hardware. ARGUS NEO
is a research decision-support prototype and does not make certified structural
safety decisions.

