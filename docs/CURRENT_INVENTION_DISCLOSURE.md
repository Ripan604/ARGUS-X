# Current technical disclosure and claim-support boundary

Date: 7 October 2026. Engineering input for a human inventor and patent
professional. Not a filed application, novelty opinion or confidentiality claim.

## Implemented subject

The final technical-review extension adds an optional full-grid task-conditioned
direct-reference selector. It ranks feasible reference paths by covariance-
conditioned downstream propagation-arrival variance plus declared cost for a
nominated diagnostic geometry. This is a fast reference subproblem; it is not
the separate two-step physical-loss policy. The complete final support/claims
worksheet and bounded 192-run scalar-arrival evidence are in
ARGUS_FINAL_TECHNICAL_DISCLOSURE.md and FINAL_PATENT_EVIDENCE.md. Legacy ESP32
post-excitation capture is refused by arrival localization pending an aligned
adapter; no synchronized apparatus is represented as physically demonstrated.

A controller for human-guided acoustic interrogation of a rectangular panel
with one dominant scatterer. A two-dimensional grid represents structural
location. A nuisance state includes a correlated propagation-velocity/timing
pair. Other nuisance quantities remain separate approximate marginals. The
current program is **not** a full hierarchical structural/material/sensor
posterior and does not establish defect existence, type, depth or severity.

The optional policy compares reference calibration and diagnostic actions using
expected squared location error and a declared acquisition cost. At most two
future observations are considered within a finite candidate beam. One action is
executed, the actual waveform updates the state, and planning repeats. The exact
implementation is `backend/app/active_learning/bayes_design.py`.

## Measurement and calibration equations

Let velocity be v, instrument delay t0 and path length L. The arrival mean is
`mu = t0 + L/v`. Around the current nuisance mean, the derivative is
`H = [-L/v^2, 1]` and the nuisance covariance is a 2-by-2 matrix C. Observation
variance is `H C H^T + R`, including the velocity/timing cross term. R includes
assumed timing resolution and pose effects; it is not a measured field bound.

A direct-path reference supplies **one** scalar observation:

```text
K = C H^T / (H C H^T + R/quality_weight)
m_new = m + K (observed_delay - predicted_delay)
C_new = (I - K H) C (I - K H)^T + K (R/quality_weight) K^T
```

One reference cannot identify both velocity and timing independently. Different
path lengths supply different derivative directions. The implemented reference
bank spans normalized source/receiver distances 0.30, 0.60 and 0.90. The covariance
and path-length history are persisted. No independent pose/coupling shrinkage is
derived solely from waveform quality.

## Physical loss and actual observation branching

All grid probability mass is assigned to spatial regions. Each region retains
its probability, probability-weighted physical centroid and within-region second
moment. For estimated position a and true position x, the loss is `||x-a||^2`
in square metres. The Bayes action is the posterior mean. Within-region error
remains in the risk rather than disappearing when modal points are selected.

The terminal risk is:

```text
R(p) = sum_h p_h (||c_h||^2 + within_h) - ||sum_h p_h c_h||^2
```

Gauss–Hermite quadrature integrates this risk over future Gaussian-mixture
arrival observations. The first observation changes region probabilities and
the conditional predictions of a second action. Shared nuisance uncertainty is
carried across observations using:

```text
cross_h = H_first,h C H_second,h^T
mu_second|y,h = mu_second,h + cross_h / var_first,h * (y - mu_first,h)
var_second|y,h = var_second,h - cross_h^2 / var_first,h
```

Under calibration the first response distribution is the same for every
structural hypothesis. Its value can arise through improved subsequent
diagnostic prediction. Under a diagnostic action the first response also changes
the structural weights. The second action is selected separately within each
observation branch. Stopping after the first action is allowed.

Candidate value is prior risk minus expected terminal risk and expected
acquisition cost. The default cost conversion is 0.0001 m² per configured
research cost unit; this is an explicit preference, not a measured maintenance
loss. A finite candidate bank and beam restrict optimization. Orders 16 and 32
are compared and numerical ranking ambiguity is reported. This difference is
not a rigorous quadrature-error bound.

This mathematics uses established Bayesian conditioning and experimental-design
principles. The implementation does not claim those principles were invented
here. Any inventive-step argument must identify a narrower physical interaction
and support it against the closest art.

## Execution and evidence sequence

1. Measure a waveform under a recorded geometry/excitation.
2. Validate original source bandwidth, mono finite samples, complete declared
   acquisition windows and units; reject missing evidence instead of padding.
   Gate channel reliability before any calibration or structural update.
3. For reference actions, update the correlated propagation block only from
   reference diagnostics; absolute pose requires an external measured reference.
4. For diagnostic actions, compute a matched-filter generalized likelihood,
   assess discrepancy/OOD against the pre-observation belief, then block or
   temper fusion as indicated. The inference likelihood is not identical to the
   regional planning likelihood; this remains a validation gap.
5. Require the latest verification measurement to pass quality, OOD, meaningful
   geometry/excitation diversity (not amplitude-only or reciprocal-path change)
   and prior-location consistency checks before permitting a confident stop.
6. Record the action, waveform, state transition, configuration and software
   identity. Verify content and the hash chain against an independent checkpoint
   if one is available.
7. Select the next physically feasible action under the updated state.

## Counsel discussion outline — not final claims

The candidate subject is an apparatus-limited acoustic control sequence that
uses a correlated timing/velocity model to compare a direct-path calibration
action with a diagnostic bistatic action under a common physical localization
loss, includes the effect on a subsequent diagnostic action, executes the chosen
action, gates actual measured evidence before structural fusion, and requires
fresh consistent verification before stopping.

Potential dependent limitations include varied reference path lengths, explicit
observation-noise/covariance treatment, finite hardware action constraints, and
independently retained evidence checkpoints. Do not make the UI, hash chain,
generic AI, general sensor placement or Gaussian update the independent
inventive concept without specific supporting prior-art analysis.

## Excluded from the current supported claim scope

- Arbitrary electromagnetic, thermal or visual interrogation modalities.
- Robot control, simultaneous synchronized ultrasonic acquisition or a new
  transducer/analog-front-end structure.
- Arbitrary multi-defect, type, depth or severity reconstruction.
- Globally optimal waveform design, a general POMDP, or guaranteed convergence.
- Validated high-fidelity FE/surrogate/bank switching in the live planner.
- Calibrated field confidence, certified safety, industrial accuracy or superiority.
- Authenticated/timestamped evidence without separate signing/anchoring infrastructure.

## Administrative facts that must come from real records

Human inventors and claim-specific conception contributions: unresolved.
Assignee/university/competition obligations: unresolved.
Earliest filing and public disclosure dates: unresolved.
Public repository visibility history and copies of demonstrations: preserve and review.

No human conception date or inventorship is inferred from an AI-generated code
change. A professional must assess existing disclosure and possible jurisdiction
restrictions before relying on a filing strategy.
