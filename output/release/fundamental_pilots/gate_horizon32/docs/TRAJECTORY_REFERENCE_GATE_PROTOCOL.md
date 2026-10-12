# Whole-trajectory reference gate for native guided-wave replay

Date: 8 October 2026. Status: prespecified experimental method, implemented in
`backend/app/evaluation/trajectory_reference_gate.py`. This document fixes the
score and calibration procedure before confirmation damage-bank results are
used. It does not report an executed physical experiment or a measured benefit.
The production audio-range inference engine is not automatically changed.

## The problem being addressed

A controller chooses later transducer paths from earlier responses. Those
responses are therefore neither a random sample of all paths nor independent
observations. Repeating a per-path anomaly test at each acquisition can also
raise an alarm eventually just because the algorithm had many opportunities.
Temperature can change a healthy waveform enough to resemble damage.

The experiment separates three operations: estimate a healthy response from
fitting references; execute a frozen controller that reveals one recorded path
at a time; compare its accumulated discrepancy with complete healthy executions
of that same controller. The latter comparison calibrates the unit that will
actually be monitored: an entire adaptive trajectory, rather than one channel.

## Frozen inputs and calibration unit

The measured-data experiment uses the Open Guided Waves temperature extension:
native 40 kHz, five-cycle excitation, 10 MHz sampling, 66 recorded pairs among
twelve transducers on the same 500 x 500 x 2 mm CFRP plate. See the
[source audit](OPEN_GUIDED_WAVES_SOURCE_AUDIT.md) and the authors'
[Scientific Data article](https://doi.org/10.1038/s41597-019-0208-1).

The planned new calibration set is 19 first-cycle healthy **cooling** banks at
nominal 22, 24, ..., 58 C. The condition used for reference transport is the
recorded surface temperature, not a silently substituted chamber setpoint.
Each native bank has 66 paths; each controller replay reaches 32 distinct
acquisition opportunities. The prespecified checkpoints are
`(1, 2, 4, 8, 12, 16, 32)`. A separate complete healthy trajectory is replayed
for every model/controller binding. A bank contributes exactly **one** scalar
maximum for each such calibration, not 66 independent samples or seven
independent checkpoint samples.

These are 19 temperature-condition blocks from **one physical specimen**. They
are not 19 independent plates, trials after independent remounting, or examples
drawn randomly from a field operating population. Reusing the banks for another
controller or fold does not create additional independent physical specimens.

The healthy reference transport and each path's scale are fitted using only
the declared development healthy references. In the accompanying experiment,
those are first-cycle warming banks at nominal 20, 40 and 60 C. The 40 C
development reference may be left out temporarily to estimate residual scale
against interpolation from 20/60 C, after which the declared final reference
model can use all three. The 19 cooling calibration banks do **not** fit the
reference transport, path scales, response model, policy, score or alpha.
Confirmation warming conditions at 30/50 C are likewise excluded from fitting.

Download/access failures and unsupported acquisitions remain in the study
accounting. Only actually acquired, complete and qualified healthy replays may
be passed to the calibrator. The module refuses an invalid calibration batch;
it does not discard malformed blocks to make an alarm threshold easier to meet.
If fewer than 19 valid blocks are available, the smaller N and resulting
resolution are reported, and the 5% gate returns `unsupported`.

## Fixed causal score

At path acquisition j, the reference transport returns corrected damage index
`d_j`, retaining the existing `1 - abs(Pearson correlation)` definition, and a
finite positive scale `sigma_j` fitted from healthy development data. The gate
also permits a declared signed centered DI in [-1, 1]. It does not change the
score formula according to confirmation labels or outcomes.

At a permitted budget b, the prespecified score is:

`S_b = (1 / b) * sum_{j=1..b} (d_j / sigma_j)^2`.

Only already acquired observations enter this sum. The gate receives a bounded
tuple/list copied at that checkpoint; it has no bank, waveform, truth label,
damage-location parameter or future-query function. It refuses generators that
could fetch unseen observations while being consumed. A finite positive scale
is a numerical/reference requirement, not evidence that the residual is
Gaussian; the subsequent rank comparison does not assume Gaussian residuals.

For complete healthy trajectory i, the calibration value is:

`M_i = max_{b in {1,2,4,8,12,16,32}} S_{i,b}`.

At test prefix b, the conservative empirical reference rank is:

`p_b = (1 + count_i(M_i >= S_b)) / (N + 1)`.

Ties use `>=`. Alpha is fixed at 0.05. With exactly 19 blocks, the minimum
attainable p is 0.05: an alert requires the prefix score to exceed **every**
calibration maximum. A tie with the largest calibration value gives at least
0.10 and cannot alert. This coarse resolution must be shown with every result.
There is no interpolation of p-values to manufacture stronger evidence.

## What the maximum protects, and what it does not

For a hypothetical complete test trajectory, its maximum `M_test` dominates
each of its permitted prefix scores. Because the reference-rank p-value falls
as the score increases, an alarm at any checkpoint implies an alarm for the
complete test maximum. Thus calibrating complete maxima addresses repeated
looks at these fixed checkpoints without treating the individual path scores
as independent. Runtime scoring still needs only the acquired prefix.

The familiar finite-sample conformal rank argument would require the complete
healthy calibration trajectories and a new healthy trajectory to be
exchangeable, with the same frozen fitting procedure, controller, horizon,
score and condition distribution. Model fitting must be separate from rank
calibration. Adaptiveness within a trajectory is compatible with treating the
complete trajectory as the calibration unit when the same closed-loop
procedure generates each exchangeable unit.

The proposed cooling calibration versus warming confirmation split has
**unverified exchangeability**. Thermal hysteresis, ordering, sensor coupling,
and dependence among temperatures on one plate can violate it. Accordingly,
the experiment reports an **empirical reference rank** and observed outcomes,
not guaranteed 95% field coverage, a certified 5% false-alarm rate, or a damage
posterior. The result cannot certify temperatures outside the qualified
reference range. It also does not protect a search across different controllers,
folds or tuned score variants, nor an indefinitely extended acquisition
horizon, unless a separate suitable calibration protocol is declared.

## Three states and safeguards

The gate returns the following explicit states:

| State | Required interpretation |
|---|---|
| `supported_anomaly` | Valid selected observations exceed the empirical healthy trajectory reference at the frozen alpha; further verification is required. |
| `background_consistent` | The acquired prefix is not exceptional by this reference rank; it does not prove the plate is healthy or authorize a healthy release. |
| `unsupported` | The reference, model quality, numeric data, provenance, checkpoint or sample resolution cannot support this comparison. |

The caller must qualify the transported reference and model quality. A failed
acquisition remains an opportunity in the trace and makes the comparison
unsupported; it cannot be removed from the prefix to strengthen an alert.
Empty prefixes, unexpected checkpoints, NaN/Inf, nonpositive scales, repeated
paths, unsupported accepted flags and numeric overflow all return unsupported.

Calibration binds lowercase SHA256 identities for the model, controller,
protocol and fitting-reference library. A change requires a matching new
calibration. Complete blocks have unique bounded IDs and unique raw-member
SHA256 values. Testing a block ID or raw artifact already used for calibration
is unsupported. These checks detect accidental reuse; hashes do not establish
authenticity or specimen independence. The calibration snapshots caller lists
and stores immutable tuples, so later edits to a trace or exported JSON cannot
change its rank distribution.

An anomaly decision never supplies localization support. A qualified spatial
response model, query accounting, a fresh geometrically distinct verification
measurement, and the apparatus acquisition contract remain separate conditions
for a supported location. The gate does not replace the direct-path
calibration/latch checks on the ESP32 device or claim that 40 kHz ultrasonic
data validate a 16 kHz audio-range probe.

## Minimal experimental API

```python
binding = GateBinding(model_hash, controller_hash, protocol_hash, reference_hash)
rows = tuple(SelectedObservation(path, corrected_di, healthy_sigma, accepted)
             for path, corrected_di, healthy_sigma, accepted in acquired_trace)
healthy = HealthyTrajectory(block_id, raw_member_sha256, rows, binding)
calibration = calibrate_reference_gate(healthy_trajectories, binding, alpha=.05)
decision = evaluate_reference_prefix(
    calibration, rows[:budget], binding,
    block_id=test_block_id, source_sha256=test_raw_sha256,
    reference_qualified=reference_ok, model_quality_accepted=model_ok,
)
```

`healthy_trajectories` must contain complete 32-opportunity healthy replays.
The caller records all failures and the actual number of valid blocks. It
derives hashes from the frozen implementation/configuration and exact source
members. A hand-written hash string is not a validation of the fitted model.

## Required reporting and tests

Report all 19 planned temperatures, acquired/source hashes, unsupported banks,
actual calibration N, minimum p, selected paths, rejected opportunities, every
checkpoint score/rank/state, earliest anomaly budget and separate localization
outcomes. Retain negative or inconclusive comparisons and all source/code
identities. Cooling/warming direction and one-specimen dependence are explicit
limitations. No confirmation-dependent score or threshold substitution is
allowed in the confirmatory table; any later variant is exploratory.

Focused tests in `backend/tests/test_trajectory_reference_gate.py` cover block
order invariance, exact rank resolution, conservative ties, early-versus-final
maxima, maximum domination of every checkpoint, causal prefix behavior,
generator refusal, signed score equivalence, invalid data, rejected/repeated
paths, identity reuse, changed bindings, insufficient N, complete-calibration
requirements and immutable snapshots. They validate implementation behavior,
not the physical exchangeability assumption or detection sensitivity.

## Existing mathematics and limited invention discussion

Conformal ranking is established mathematics. Shafer and Vovk's
[2007 tutorial](https://arxiv.org/abs/0706.3188) explains its assumptions and
construction. Agia et al., *Unpacking Failure Modes of Generative Policies:
Runtime Monitoring of Consistency and Progress* (CoRL 2024), explicitly
calibrate whole closed-loop trajectories to handle correlated sequential
states/actions; see its [primary paper](https://openreview.net/pdf?id=yqLFb0RnDW)
and [authors' repository](https://github.com/agiachris/sentinel). The earlier
[2011 trajectory anomaly paper](https://ieeexplore.ieee.org/abstract/document/5977571)
also applies sequential conformal detection to incomplete trajectories.
The gate cannot plausibly claim invention of conformal p-values, maxima or
generic sequential anomaly detection.

A technical interaction to investigate in a narrow apparatus claim is the
ordered combination of: (1) provenance-bound reference capture with source
timing qualification; (2) healthy-only path/condition transport and uncertainty
that can redirect an acquisition toward reference repair; (3) one-at-a-time
feasible actuator/receiver selection under a fixed opportunity budget;
(4) calibration of the actual resulting healthy controller trajectories;
(5) a three-state gate that prevents an unsupported capture from advancing a
structural claim; and (6) a fresh diverse verification capture bound to the
same record. These are **candidate technical relationships**, not a novelty
opinion, a proposed patent claim known to be allowable, or evidence of an
inventive step. The interaction needs closer prior-art searching, actual
hardware execution and comparative results before it can strengthen a grant
assessment.
