# ARGUS technical invention disclosure for professional review

Prepared 7 October 2026. Technical input, not a filed application, novelty
finding, legal claim set, or patent-pending representation. Human conception,
ownership, prior disclosures and jurisdiction are unresolved administrative facts.

## Working title and technical field

**Sequential acoustic interrogation with correlated propagation calibration,
measurement-validity gating, and verification-supported termination.**

The implemented field is operator-guided acoustic/vibration interrogation of a
rectangular panel with one dominant localized scatterer. The objective is to
choose physical measurements under uncertain propagation and finite action cost.

## Problem addressed

Speed and instrument timing uncertainty can confound defect localization.
Low-quality, aliased, incomplete or unsupported recordings can create misleading
spatial concentration. A diagnosis-only controller can spend scarce measurements
on structural ambiguity that cannot be resolved until propagation is calibrated.
The program compares supported diagnostic and reference actions, gates the
actual acquisition before updating structure, and requires a fresh qualifying
verification observation before a confident termination.

## Enabled software embodiment

1. Define a 0.60 x 0.40 m panel and 20 x 20 location grid. The synthetic effective
   speed prior is 180 m/s and timing prior is 0.8 ms. These are illustrative,
   not measured material properties.
2. Represent propagation speed and timing with means and a correlated 2 x 2
   covariance. Other nuisance quantities remain separate approximate marginals.
3. Enumerate bounded source/receiver/waveform candidates within drive, duration,
   frequency, spacing and no-go restrictions. Live forward levels are analytical
   and physics-signature only. The default policy uses explicit ranking proxies.
4. Optionally compare diagnostic and direct-reference actions using expected
   squared position loss plus acquisition cost. Partition all spatial mass into
   regions; retain within-region spread. Gaussian quadrature branches over at most
   two observations and conditions later arrivals using shared propagation
   covariance. A finite beam restricts optimization.
5. Execute one selected action via the simulator or an acquisition adapter.
   Validate original bandwidth, mono shape, finite samples, declared window,
   normalization and channel reliability before evidence fusion. Server-owned
   acquisition provenance selects the physical acoustic-reference guard.
6. For a direct reference, update propagation covariance from one scalar delay;
   do not count that delay as two independent observations or as defect evidence.
   Use varied reference distances to improve speed/timing identifiability.
7. For diagnostic evidence, subtract the nominal direct response, correlate with
   the excitation, sample support at each candidate bistatic lag, construct the
   generalized likelihood, then assess OOD against pre-observation belief. Block
   unsupported data and temper caution. Fuse accepted evidence in log space.
8. A confident stop requires the latest accepted, nominal, consistent verification
   measurement with changed geometry or excitation content. Amplitude-only,
   duration-only and reciprocal-probe changes do not count as fresh verification.
9. Preserve state and record the action, waveform, configuration, planner,
   diagnostics and transition hashes with the actual source fingerprint. An
   independently retained checkpoint may anchor history-consistency verification.

The firmware reference enables an ESP32 exciter driver/conditioned ADC contract,
and adapters support WAV, local/browser microphones and phone/edge nodes. The
repository does not establish an assembled, synchronized, characterized NDE
apparatus; its hardware embodiment requires measured construction evidence.

## Mathematical support

For candidate location z, source S, receiver R, speed v and timing t0:

```text
arrival(z,e) = t0 + (distance(S,z)+distance(z,R))/v
H = [-path/v^2, 1]
arrival_variance = H C H^T + R
K = C H^T / (H C H^T + R/quality_weight)
new_mean = mean + K (observed_reference_delay - predicted_delay)
new_C = (I-KH) C (I-KH)^T + K(R/quality_weight)K^T
```

With region centroid c_h, mass p_h and within-region second moment w_h:

```text
position_risk = sum_h p_h (||c_h||^2 + w_h) - ||sum_h p_h c_h||^2
candidate_value = prior_risk - expected_terminal_risk - acquisition_cost
structural_posterior_next = normalize(prior * likelihood^evidence_weight)
```

The default cost conversion is 0.0001 m^2 per declared research cost unit.
It is a configured preference, not a measured maintenance loss. The waveform
inference likelihood differs from the regional Gaussian planning model. This
is an acknowledged model-consistency and physical-validation gap.

## Claim-support worksheet

| Candidate element | Implemented support | Excluded or unresolved |
|---|---|---|
| Sequential feasible acoustic action selection | Engine, candidate planner, hardware API and recorded histories | Global optimality, robotics, arbitrary modalities |
| Correlated reference calibration | Nuisance covariance, Joseph update, distinct reference path options and tests | Full hierarchical posterior, exact physics |
| Common physical-loss diagnosis/calibration comparison | Optional finite-horizon risk planner and synthetic evaluation | Guaranteed fewer measurements, superior field error |
| Pre-fusion validity and provenance controls | Source bandwidth/window/unit checks, channel/quality/OOD gates | Calibrated physical confidence or spoof-proof sensors |
| Fresh verification-supported stop | Latest-observation consistency and meaningful diversity tests | Field coverage/safety certification |
| Bound recorded state/evidence identity | Content-bound ledger and independent checkpoint option | Signatures, trusted timestamps, human authorship proof |

Any draft claim should be tied to a reproducible technical sequence supported by
these implementation files, not the general idea of AI or Bayesian mathematics.
This worksheet is material for a practitioner to assess, not an asserted claim
of novelty or non-obviousness.

## Preliminary adjacent-art comparison

| Reference | Relevant existing subject matter | Specific comparison still needed |
|---|---|---|
| [EP2214009A2](https://patents.google.com/patent/EP2214009A2/en) | Reference wave responses and probabilistic defect-location mapping | Whether the ordered diagnosis/reference competition and qualifying verification are disclosed or obvious |
| [US9964468B1](https://patents.google.com/patent/US9964468B1/en) | Model/scenario-based structural-health sensor placement | Fixed arrangement versus live belief-conditioned sequential action selection and calibration |
| [US20230401694A1](https://patents.google.com/patent/US20230401694A1/en) | Confidence-driven inspection-location selection and model retraining | Wave-response discrimination and propagation-reference comparison rather than inspection-label acquisition |
| Flynn and Todd guided-wave placement literature (paper bibliography) | Bayesian sensor placement and value of information | Closest sequential calibration/dual-control methods, not merely fixed networks |

The three patent documents were consulted again during this audit. This is a
limited comparison, not an exhaustive family/claim search or freedom-to-operate
analysis. Existing Gaussian conditioning, experimental design, wave localization,
dual control and hash chains are not presented as newly invented principles.

## Evidence that exists and evidence still required

Existing: executable code, security/scientific regression tests, seeded synthetic
studies, separate public measured-data bridge artifacts, and source/evidence
packaging. The fresh release study is documented separately and keeps all failures.

Required for efficacy claims: blind, specimen-held-out measurements on the actual
apparatus with independent geometry/timing truth, appropriate comparison methods,
coverage/false-confidence checks and matched-cost policy comparisons. The existing
public GFRP classifier and one-plate impact experiments cannot establish adaptive
persistent-defect localization on this apparatus.

## Administrative and disclosure record to complete

- Actual human inventor(s), each claim-specific contribution and dated conception
  evidence; code authored with an AI tool is not itself a human conception record.
- University/credit-project ownership, collaborator agreements and any sponsor or
  competition obligations.
- Repository visibility history, presentations, uploads, demonstrations, offers,
  prior filings and exact disclosure dates.
- Target jurisdiction, suitable filing form, enabling drawings/measurements, and
  a professional independent-claim/family/literature comparison.

Public disclosure can affect filing options; the applicable rules must be checked
for the chosen jurisdiction before external publication. The
[USPTO provisional guidance](https://www.uspto.gov/patents/basics/apply/provisional-application)
explains disclosure requirements and timing for that US filing route. The
[EPO simulation guidance](https://www.epo.org/en/legal/guidelines-epc/2026/g_ii_3_3_2.html)
distinguishes computer implementation from technical effects. Neither establishes
ARGUS eligibility or novelty in India or elsewhere. No filing or external release
is performed by this preparation package.
