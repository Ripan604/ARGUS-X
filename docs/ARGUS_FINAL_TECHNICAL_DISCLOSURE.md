# ARGUS final technical disclosure for patent review

**Historical source boundary:** this document records the pre-v2 method revision.
Its firmware limitation and 192-run results belong to that revision. The current
apparatus, gate and stronger comparison are documented in PROBE_V2_RELEASE_REVIEW.md,
PROBE_V2_DESIGN.md and PATENT_STRENGTHENING_ASSESSMENT.md. Do not treat the older
numbers or apparatus description as validation of the changed v2 source.

**Revision:** final technical-review version, 7 October 2026.
**Status:** implemented software and synthetic evidence; no patent filing,
novelty opinion, physical apparatus validation, or human inventorship finding.

## Title and supported technical contribution

**Task-conditioned reference geometry selection for sequential acoustic
interrogation with correlated propagation uncertainty and gated verification.**

The narrower candidate contribution is an acoustic control sequence that uses
the current location probability map to choose which propagation reference to
measure before the next diagnostic experiment. It reduces uncertainty relevant
to that diagnostic geometry, rather than selecting a reference merely because
it is first feasible or reducing every instrument parameter indiscriminately.

The new full-grid reference selector is implemented and exercised in the live
engine. It is an optional fast-controller extension. Established Bayesian
conditioning and experimental-design principles are not claimed as inventions.
The separate two-observation physical-loss planner already compares calibration
and diagnosis under a coarsened arrival model; the new method is a cheaper,
full-grid, task-conditioned reference subproblem, not a claim to supersede it.

## Technical problem and mechanism

An observed arrival combines propagation speed and electronics timing. A single
reference path gives one constraint on two correlated unknowns. Repeating the
same path can reduce variance along one observed direction while leaving other
diagnostic paths uncertain. Generic uncertainty reduction may improve timing
offset while offering little benefit for the intended diagnostic path.

ARGUS keeps the correlated speed/timing covariance, evaluates a finite feasible
reference bank against all spatial posterior mass under a nominated diagnostic
geometry, predicts the covariance after each reference, and selects the
minimum expected propagation-variance-plus-cost objective. The actual recording
is then validated and incorporated as metrology evidence. It is not counted as
defect-location evidence. Later diagnosis and fresh diverse verification use the
updated propagation model.

## Executed method and implementation boundaries

1. Maintain a normalized 2D location grid and correlated speed/timing means and
   covariance. Other nuisance variables remain approximate separate marginals.
2. The existing fast action controller decides whether reference calibration is
   warranted. The new selector does not independently replace that decision.
3. Form three direct-reference geometries with distinct physical path lengths.
   Filter no-go regions, unavailable actions, waveform/drive, spacing and
   frequency restrictions before selection.
4. Nominate a feasible diagnostic geometry from the current baseline candidates.
   Convert every grid cell to physical coordinates and its bistatic path length.
5. Calculate the weighted second moment of arrival derivatives over the complete
   grid. Retain speed/timing covariance cross terms; do not discard low-mass cells.
6. For each feasible reference, condition the propagation covariance using the
   same first-order reference model and declared noise/quality assumptions.
7. Rank by predicted path-equivalent propagation variance plus declared acquisition
   cost. Report before/after variance, paths, assumptions, design rank, costs and
   every reference alternative. Rank is diagnostic, not a forced diversity rule.
8. Acquire one supported reference. Validate original bandwidth/window/units and
   channel quality before updating metrology; block incompatible data.
9. Replan diagnosis from the updated model, gate structural evidence before fusion,
   and require a fresh qualifying verification before a confident stop.
10. Preserve the action, prediction, observation, actual source identity and state
    transition in content-bound evidence records.

Activation is `enable_task_conditioned_calibration=true` in the session API or
`--task-calibration` in scripts/demo_simulation.py. It stays off by default.
The optional two-step risk policy takes precedence if that policy is enabled.
No robot motion, high-fidelity FEM switching, depth/type/severity inference or
measured safety decision is included in this supported implementation.

## Mathematical specification

Let z be a grid-cell center with mass p_z, diagnostic source S and receiver R,
effective speed v and timing offset t0. All distances are physical metres.

```text
ell_z = distance(S,z) + distance(z,R)
mu_z = t0 + ell_z/v
g_z = [-ell_z/v^2, 1]
W = sum_z p_z * g_z^T g_z
V_before = trace(W C)                         [s^2]
```

For direct-reference length d, h=[-d/v^2,1]. R_ref is the declared timing and
placement variance; q=0.75 is the selector's explicitly assumed quality.

```text
K = C h^T / (h C h^T + R_ref/q)
C_after = (I-Kh) C (I-Kh)^T + K(R_ref/q)K^T
V_after = trace(W C_after)
reference_objective = v^2 * V_after + c * acquisition_cost
```

Here v^2 V is path-equivalent propagation variance in m^2, not expected location
error. The default c=0.0001 m^2 per research cost unit is a preference, not a
measured monetary, energy or maintenance loss. The comparison study disables
cost to isolate the geometry criterion. Actual acquisition quality may differ
from the assumed value and is checked before the measured update.

For a valid Gaussian block, C-C_after is positive semidefinite and the modeled
variance cannot increase. The reduction equals

```text
sum_z p_z * (g_z C h^T)^2 / (h C h^T + R_ref/q)
```

This is an analytic property of the declared local model, not a physical coverage
guarantee. The implementation verifies variance bounds and does not mutate the
belief, hidden truth, random generator or covariance during selection.

## Concrete software embodiment

The worked configuration uses a 600 x 400 mm panel, a 20 x 20 grid, 16 kHz acquisition,
an illustrative 180 m/s speed and 0.8 ms timing prior. Reference paths are 0.18,
0.36 and 0.54 m; the measured noise contract includes a 0.2 ms timing floor and
declared pose uncertainty. These are simulation/design values, not certified
material or transducer constants.

In the checked easy seed 17 eight-action demonstration, the calibration at action 7
selects a 0.54 m reference. Its modeled downstream arrival variance falls from
1.767e-7 to 5.463e-8 s^2 under the assumed reference model. The actual simulation
continues to approximately 10 mm MAP error and STOP_BUDGET; this one run is not an
accuracy superiority result.

## Physical acquisition embodiment and enabling requirements

The control software can consume an externally acquired, trigger-aligned WAV with
known source/receiver geometry, source sampling rate, excitation definition,
recording window and normalization. A proposed physical embodiment uses a shared
trigger driving a characterized exciter and acquisition system on a repeatable
fixture, records before/through early arrival, and retains the actual timing and
transfer calibration. Its wiring and apparatus timing must be measured.

The current ESP32 firmware calls excitation before ADC recording and does not
carry a verified sample-clock/trigger contract. It also derives a chirp endpoint
internally rather than transporting the complete declared experiment. It is a
decay-recording example. Its serial adapter is now refused by arrival localization
before any actuation. No synchronized ESP32 apparatus, flash, compilation or
physical verification is claimed by this disclosure.

For enabling drawings, Figure 1 specifies the controller/data blocks; Figure 2
shows the direct and bistatic paths; Figure 3 shows the reference-design/update
sequence. The physical clock requirement is an implementation boundary, not an
omitted claim of an already-built transducer or DAQ.

## Technical effects and evidence

The fresh scalar-arrival study contains 64 paired seeds, 3 references per policy,
and 192 completed policy runs. Mean downstream arrival RMSE is 279.65 microseconds
for the cyclic first-feasible policy and 200.57 for task-conditioned selection,
a 28.3% reduction. The paired mean advantage is 79.07 microseconds with bootstrap
95% interval [50.27,110.35]. Source hashes were stable and match the reviewed code.

The mean timing-offset error increases from 136.20 to 144.89 microseconds, while
speed error decreases from 14.10 to 11.80 m/s. This adverse tradeoff is retained:
the objective targets the subsequent arrival prediction, not all parameter errors.
The repeated-short policy is an additional failure control, not the existing
cyclic baseline. An earlier repeated-path pilot is preserved and labelled pilot.

The result supports a bounded computational calibration effect in the declared
synthetic model. It does not establish real waveform performance, hidden-defect
localization, fewer physical measurements, or patent novelty. The earlier 48-run
defect-localization study belongs to the pre-extension source and still contains
large mismatch errors; it must not be reassigned to this source revision.

## Draft claim concepts for practitioner revision

These are technical drafting aids. They have not been assessed for novelty,
inventive step, eligibility, unity, clarity, ownership or enforceability.

1. A processor-controlled acoustic interrogation method maintaining a probability
   distribution over candidate positions and a correlated propagation-speed/timing
   state; determining a feasible diagnostic geometry; evaluating feasible direct
   references using the position-weighted covariance-conditioned arrival variance
   for that geometry; selecting and executing a reference under declared cost;
   validating its recording and updating propagation state; and subsequently
   acquiring and fusing diagnostic evidence under the updated state.
2. The method of concept 1, wherein every grid-cell mass contributes to a derivative
   second-moment matrix and covariance cross terms contribute to reference value.
3. The method of concept 1, wherein the direct-reference observation supplies one
   scalar update to the correlated speed/timing block, with a Joseph covariance
   update and without multiplication into the structural location grid.
4. The method of concept 1, wherein reference eligibility is tested against physical
   placement, source bandwidth/window and drive constraints before acquisition.
5. The method of concept 1, wherein reference-path rank/span and before/after target
   variance are retained without claiming separate identification from one delay.
6. The method of concept 1, wherein actual quality/channel/model-domain checks
   suppress or temper unsupported evidence before a structural update.
7. The method of concept 1, wherein confident termination requires the latest
   accepted nominal verification using changed geometry or excitation content;
   reciprocal-path or amplitude-only changes do not alone qualify.
8. The method of concept 1, wherein evidence binds selected geometry, prediction,
   recorded waveform, calibration and structural transition to source identity.
9. A control-system implementation having a processor, memory and acquisition
   adapter configured to perform the supported method concepts; its physical
   trigger/DAQ embodiment is subject to the stated enabling/validation boundary.

The independent concept should be narrowed to the technical interaction actually
supported, after a professional search. Security/UI/hash features alone should
not be used to manufacture an inventive acoustic effect.

## Closest-art comparison and obviousness risks

| Reference reviewed | Relevant claim subject matter | Comparison still required |
|---|---|---|
| EP4592907A1, claims 1-3 | Digital-twin synchronization with a state-wide Bayesian filter; later weighted instantiations and active instrument adjustments | Compare specific full-grid downstream acoustic-reference criterion and ordered measured fusion; generic Bayesian calibration is already crowded |
| EP2214009A2, claim 1 and dependent claims | Reference wave responses, decorrelation/error functions and spatial probability mapping | Compare reference-geometry selection for a nominated diagnostic task; baseline wave inference is not new |
| US10126274B2, claims 1 and 4 | Known-state data, movable transducer and stored scattered impulse responses for multi-path detection/localization | Compare task-conditioned direct-reference calibration; movable multi-path acquisition itself is not new |
| Bayesian experimental design and guided-wave placement literature | Value/information-based measurement and sensor design | Task-conditioned covariance reduction may be viewed as established optimal-design mathematics applied to this apparatus |

Sources: [EP4592907A1](https://patents.google.com/patent/EP4592907A1/en),
[EP2214009A2](https://patents.google.com/patent/EP2214009A2/en),
[US10126274B2](https://patents.google.com/patent/US10126274B2/en).
The correct digital-twin reference is EP4592907A1; a transposed publication number
must not be used. This limited claim reading is not an exhaustive family search
or a finding that the ordered combination is absent or non-obvious.

## Human inventorship, ownership and disclosure record

An actual person must supply claim-specific conception and contribution records.
This computer-assisted engineering work does not establish who conceived each
claim. Preserve the prompts, dated human notes, alternatives, decisions and source
versions without treating automatic code generation as a human invention date.
Complete university/credit-project ownership and collaborator agreements, prior
public demonstrations/repository history, earliest disclosures and intended jurisdiction.

Current official references include India's notified CRI 2025 guidance (review the
actual applicable text), the EPO technical-effect framework, and revised USPTO
AI-assisted inventorship guidance. They do not establish ARGUS eligibility.
The USPTO 2025 revision superseded its 2024 guidance; only natural persons can be
named as inventors under that guidance.

Sources: [Indian government CRI announcement](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2149719&lang=2&reg=48),
[USPTO revised guidance](https://www.uspto.gov/subscription-center/2025/revised-inventorship-guidance-ai-assisted-inventions),
[EPO simulation guidance](https://www.epo.org/en/legal/guidelines-epc/2026/g_ii_3_3_2.html).

## Final review handoff

Provide this disclosure, code mapping, new study, negative tradeoff, drawings,
regression report and independently retained source manifest to your supervisor
and patent practitioner. Before broader claims, obtain blind physical data with
measured timing/geometry and specimen-held-out comparisons. Do not state patent
pending, field validated, world first, certified or grant guaranteed without the
corresponding actual event and evidence. No filing or external publication was
performed by this technical finalization.
