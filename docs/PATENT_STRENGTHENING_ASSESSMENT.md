# ARGUS patent-strengthening assessment and evidence boundary

**Prepared:** 7 October 2026. **Purpose:** engineering input for a registered
patent agent and technical reviewer. No application, external publication,
novelty opinion, freedom-to-operate opinion or grant is represented here.
Human inventorship, ownership and previous public disclosures remain unknown.

## 1. What became more defensible

The supported subject is an acoustic inspection controller linked to a
specific source/receiver acquisition contract. It maintains a spatial location
distribution and a correlated effective-speed/instrument-delay model; selects
a direct reference relevant to the pending diagnostic geometry; records a
supported excitation and concurrent receiver response; rejects inconsistent
frames before interpretation; updates metrology without adding structural
evidence; and replans diagnosis with fresh verification controlling termination.

The v2 reference removes a concrete physical inconsistency in the earlier
sketch: excitation finished before recording started, so early arrivals were
missing while inference assumed an excitation-aligned observation. The new
source DAC and receiver ADC operate within one timed loop, with pretrigger
samples, recorded trigger/call timestamps, actual DAC codes and complete
action-bound frames. The host requires a device-specific external bench
declaration independently of protocol support. These changes support an
implementable technical sequence and clearer failure behavior. They do not
establish that this sequence is new or non-obvious.

The contribution should be presented as the ordered interaction between
reference selection, acquisition validity, propagation feedback and later
diagnostic control. Broad ownership over acoustic localization, movable
transducers, Bayesian calibration, prediction-variance design, hash chaining
or common microcontroller acquisition is unsupported. Adding more components
or a longer claim is not evidence of inventive step.

Implementation pointers: `backend/app/active_learning/reference_design.py`,
`backend/app/inference/nuisance_posterior.py`, `backend/app/services/engine.py`,
`backend/app/hardware/protocol_v2.py`, `backend/app/hardware/devices.py`,
and `firmware/esp32/argus_probe.ino`. The complete apparatus and protocol are
described in [PROBE_V2_DESIGN.md](PROBE_V2_DESIGN.md).

## 2. Closest checked sources and limitations of this search

The following are document-specific observations, not a completed worldwide
claim chart. The EPO's EP4592907A1 publication and the NASA-hosted original
US10126274B2 patent were read directly. For EP2214009A2, the original publication
text reproduced by Google Patents was inspected; direct EPO retrieval failed.
Its French wording must be checked against the official document before legal
claim analysis. No legal-status conclusion is inferred from mirror labels.

| Source and inspected scope | Existing technical subject | Consequence for ARGUS |
|---|---|---|
| EP4592907A1, claims 1-3 and 5 | Bayesian synchronization of a scientific instrument's digital twin; claim 3 includes measured observations, state weighting/pruning, a variance test and active instrument-setting adjustment for following iterations. The microscope limitation is in dependent claim 5. | A distinction based only on a different instrument or active calibration is weak. Compare the precise reference geometry, separate structural/metrology evidence and later diagnostic control sequence. |
| EP2214009A2, claims 1, 3-5 | Reference/current wave responses, decorrelation, source/receiver exploration probabilities, multiplication into a defect-location probability map, normalization and temporal response correction. | Reference subtraction, probability maps, normalized evidence fusion and timing correction are already adjacent art. Compare the actual ordered reference selection and acquisition-gated feedback. |
| US10126274B2, claims 1, 4, 6-10 | Known-state acquisition using a movable transducer, estimated scattered responses, unknown-state comparison, correlation/deconvolution and adaptive combination weights. | Neither movable sensing nor reference/scattered-wave comparison establishes a new concept. ARGUS currently uses a simpler effective bistatic model, not this patent's validated multi-path response bank. |

The first summary is supported by the [official EPO EP4592907A1 publication](https://data.epo.org/publication-server/rest/v1.2/publication-dates/2025-07-30/patents/EP4592907NWA1/document.pdf),
claims on printed pages 38-39. The second is supported by the
[EP2214009A2 publication text](https://patents.google.com/patent/EP2214009A2/en),
with the translation/retrieval qualification above. The third is supported by
the [original US10126274B2 patent hosted by NASA](https://ntrs.nasa.gov/api/citations/20190000745/downloads/20190000745.pdf),
claims on printed pages 16-18. These references are relevant even without an
opinion on enforceable current claims in any particular country.

The engineering inference is that the broad ingredients face substantial prior
art. No checked passage was used to establish the novelty of their combination.
A professional must review descriptions as well as claims, cited literature,
family documents, examination records and other sequential calibration/control
work. Absence of the entire ARGUS sequence from this short table is not proof
that nobody disclosed it or that combining the teachings would be non-obvious.

## 3. The reference-selection mathematics is established design

For structural cell z under pending diagnostic e, ARGUS predicts
t(z,e)=t0+L(z,e)/v. Its local derivative with respect to propagation parameters
(v,t0) is h_z=[-L(z,e)/v^2,1]. Let C be their covariance and let p_z be all
normalized spatial cell masses. The software forms:

```text
Q(e,p) = sum_z p_z h_z h_z^T
predicted propagation variance = trace(Q C)
```

A reference path r provides a single scalar arrival observation with derivative
h_r and declared noise R. Its local Gaussian conditioning gives a covariance
C_r. The selector ranks finite feasible references by:

```text
J(r | e,p) = v^2 trace(Q(e,p) C_r) + declared acquisition cost
```

This is a locally linear, posterior-weighted prediction-variance criterion:
an application of established V-optimal/Bayesian design, with an added configured
cost. Prediction-variance minimization over a finite regressor set, including
sequential adaptive variants, predates ARGUS. See Wiens and Li,
[V-optimal designs for heteroscedastic regression (2014)](https://www.sciencedirect.com/science/article/abs/pii/S0378375813002310).
Bayesian prediction-oriented design has still earlier literature, including
O'Hagan's [Curve Fitting and Optimal Design for Prediction (1978)](https://rss.onlinelibrary.wiley.com/doi/abs/10.1111/j.2517-6161.1978.tb01643.x).

Multiplying timing variance by v^2 produces path-equivalent square metres; it
does not convert it into proven defect-location loss. The full-grid weights,
current diagnostic geometry and speed/delay covariance give this application
a definite physical target, but those features do not make the mathematical
criterion newly invented. Local linearization, assumed independent reference
noise, stationary effective speed and finite candidate geometry remain model
assumptions. A single path gives a rank-one precision increment; different path
lengths improve observability, an established identification principle.

The synthetic comparison supports propagation-prediction behavior under its
declared model. It does not prove patentability, field localization, minimum
detectable defect size, measurement compression or that every instrument
parameter improves. Preserve the worse timing-parameter result and all runs.
The extended study includes stronger standard A- and D-optimal controls. Its
pooled arrival-RMSE advantage over D-optimal is inconclusive (0.46 us, exploratory
95% seed-cluster bootstrap interval [-5.70,6.90] us), and modeled interval
coverage falls under doubled acquisition noise. A cyclic-reference improvement
cannot support a claim of general design superiority. These are synthetic
scalar-reference findings, not physical localization.
See [the retained extended study](../research_results/extended_reference_design_2026_10_07.json)
and [its protocol](EXTENDED_REFERENCE_VALIDATION_PROTOCOL.md).

## 4. Narrow technical concepts for a patent agent to test

The following are discussion concepts, not a final independent claim set.
Each would still require a search for the full combination and obviousness.
The inventive-step analysis must explain why the interaction solves a physical
problem beyond predictable use of known components.

**Concept A: task-conditioned reference-to-diagnosis control.** A panel
interrogation apparatus has a controllable acoustic source, receiver,
excitation-referenced acquisition clock and processor. The processor maintains
a spatial location distribution and correlated speed/delay covariance; nominates
a feasible diagnostic source/receiver geometry; evaluates direct-reference
geometries through the propagation-variance effect over that diagnostic's
weighted spatial support; acquires the selected reference; updates propagation
only from accepted reference evidence; and recomputes a later diagnostic
physical action. Restrict the model and physical modality to what is disclosed.

**Concept B: acquisition-contract gate inside that control sequence.** Before
the reference or diagnostic waveform can change its respective state, the host
checks that the capture overlaps source excitation, includes pretrigger and
the declared observation window, reports the accepted waveform/endpoints and
actual DAC sequence, and has bounded clock deviations, ordered complete samples
and valid integrity. The bench declaration is tied to a specific chip and
sampling rate. A failed acquisition cannot be relabelled as valid evidence.
The technical interaction is protection of the arrival model's physical input,
not a general claim to framing, checksum algorithms or software authentication.

**Concept C: verified subsequent termination.** Following the updated
propagation model and accepted diagnostic fusion, a confident stop requires the
latest qualifying observation to pass quality/model support and meaningful
geometry/excitation diversity and agree with the preceding location region.
Reciprocal paths or amplitude-only changes cannot satisfy that condition in
the current reciprocal model. This is an implemented control guard; there is
no claim that its heuristic confidence is a field-calibrated probability.

Candidate dependent limitations include varied reference lengths, explicitly
retained covariance cross terms, all grid mass in the target, known waveform
families, pretrigger/quiet-tail windows, hard drive bounds, feasibility/no-go
checks and the separation of reference from structural evidence. Exact pins,
8-bit resolution and 16 pretrigger samples are reference implementation details;
claim necessity should be assessed rather than asserted. Evidence hashes may
support reproducibility but should not carry the independent inventive concept.

A mere list of known devices operating independently would be insufficient
as a technical case. Show, in code traces and then physical records, how the
reference changes the propagation prediction and the next executed diagnostic
geometry, and how the acquisition gate prevents an invalid observation from
creating that state change. This is the precise technical interaction to chart
against the closest art.

## 5. Enablement and physical evidence levels

| Evidence level | Actual status and permitted statement |
|---|---|
| Executable controller/host parser | Implemented source and regressions; model-state transitions and protocol rejection can be reproduced. |
| Portable waveform/protocol logic | g++ property tests pass: strict tokens/bounds, rational deadlines, bounded DAC sequence and checksum behavior. |
| Full sketch with Arduino mocks | Compiles and passes host tests for overlapping drive/capture, pretrigger, quiet tail, complete frames, STOP, overrun and clock rollover. The fixture is generated ADC/virtual-clock data. |
| Real ESP32 board-target build | Official CLI 1.5.1 was verified and installed in isolated directories; requested stable core 3.3.12 did not finish installing. No board compile command ran or board binary was generated; receipt in output/release/probe-v2-board-build.json. |
| Assembled apparatus/clock bench | No measured board, amplifier, ADC aperture, DAC settling, trigger-to-drive latency, drift, transfer or acoustic coupling is represented as validated. |
| Blind adaptive physical localization | Not performed on this apparatus. No field error, safety or calibrated coverage claim follows from synthetic results. |

The v2 sketch's trigger time is a scheduling marker before GPIO26/DAC writes;
sample times denote ADC-call start. They are not exact electrical converter
apertures. An operator's calibration declaration is a recorded attestation and
external evidence digest; the host does not independently certify its truth.
Chip identity plus FNV and hashes provide consistency/binding, not sensor
authenticity or trusted timestamping. GPIO27 STOP is polled software; an
independent actuator-supply cutoff remains a proposed circuit.

The reference amplitude limit 0.60 bounds DAC commands around biased idle 128.
It is not a measured force, pressure, current, wattage or energy constraint.
The AC-coupled external amplifier, input protection, antialias filtering,
specimen fixture and transfer characterization must be supplied for the actual
apparatus. The effective nondispersive single-scatterer model cannot silently
support arbitrary ultrasonic structures, multi-defect reconstruction or depth,
type and severity claims. See the [enabling probe design](PROBE_V2_DESIGN.md).

## 6. India: technical readiness, application publication and grant differ

India's definition of an invention requires a new product/process, inventive
step and industrial applicability. Inventive step requires non-obviousness,
alongside the statutory technical-advance/economic-significance language. The
worldwide earlier-publication/use boundary matters for novelty. An implemented
demo and a better numerical result do not themselves establish these criteria.
[IP India, section 2](https://ipindia.gov.in/acts/patent-act-1970/section-2-5).

The statutory exclusions include mathematical methods/algorithms and computer
programmes per se, presentation of information, and mere arrangements of known
devices working independently. Linking a processor to a transducer does not
automatically resolve eligibility or inventive step; a patent agent must assess
the claimed technical operation and current practice.
[IP India, section 3](https://ipindia.gov.in/acts/patent-act-1970/section-3).

A complete specification must describe operation and performance sufficiently,
include the applicant's known best method, and have clear claims fairly based
on the disclosure. Consequently the actual acquisition, geometry, calibration
and failure handling matter more than broad labels such as AI or digital twin.
Physical tests are not asserted here to be a universal legal prerequisite for
filing; the current experiment gaps limit the claims and technical performance
representations this package can responsibly support.
[IP India, section 10](https://ipindia.gov.in/acts/patent-act-1970/section-10).

Application publication is disclosure of a filed application. Ordinary secrecy
before publication is generally eighteen months from filing or priority,
whichever is earlier; an earlier-publication request is provided for. This is
separate from substantive examination and grant. Publication does not itself
establish that the claims were found patentable.
[IP India, section 11A](https://ipindia.gov.in/acts/patent-act-1970/section-11a),
[rule 24](https://ipindia.gov.in/acts/patent-rules-2003/rule-24).

Examination requires a prescribed request. Grant follows the application's
being found in order under the Act; it is a separate legal event. A manuscript
publication is different again. ARGUS has no filing/publication/grant number
created by this work, and should not be called patent pending or patented.
[IP India, section 11B](https://ipindia.gov.in/acts/patent-act-1970/section-11b),
[section 43](https://ipindia.gov.in/acts/patent-act-1970/section-43).

The applicable procedure and disclosure dates must be reviewed before a filing
decision. If relevant parties are resident in India, foreign-filing restrictions
also require assessment; residency is not inferred from this project's folder
or timezone. [IP India, section 39](https://ipindia.gov.in/acts/patent-act-1970/section-39).

## 7. Exact package still needed for professional review and publication

1. **Human and ownership records:** identify real human contributors for each
   claimed mechanism; retain dated conception/design notes and contribution
   statements. Resolve university/project-credit, collaborator, sponsor and
   competition rights. Do not infer inventorship or conception dates from
   AI-generated changes or PDF dates.
2. **Disclosure inventory:** capture repository visibility/history, public
   demos, review slides, reports, uploads, offers and prior filings with exact
   dates and audiences. Ask the agent to assess the effect in each desired
   jurisdiction. Do not assume an available grace period or backdate records.
3. **Closest-art chart:** obtain the official French EP2214009A2 copy; chart
   independent/dependent claims and descriptions from all three references,
   related families and cited non-patent design/control literature against
   every proposed limitation. Separate novelty, obviousness and infringement
   questions; legal status alone cannot substitute for technical comparison.
4. **Best-method apparatus:** retain the final circuit/BOM, board/core/firmware
   revision, external driver gain/current/voltage limits, sensor protection,
   antialias response, fixture, specimen dimensions/material/thickness and
   measured S/R locations with uncertainty. Draw the clock and source/receiver
   interconnections and separate built from proposed elements.
5. **Timing/transfer bench:** acquire external oscilloscope/logic-analyser
   captures of GPIO26, DAC output and ADC/known injected reference. Measure
   call-to-electrical latency, sample jitter, rate drift, clipping, quantization,
   drive endpoints and transfer response at the actual supported rate. Preserve
   original records and independently calculate the declared tolerances.
6. **Reference validity:** demonstrate that the accepted reference peak is the
   intended direct propagation response rather than a stronger echo, electrical
   pickup or defect scattering. Vary measured path lengths, estimate the joint
   speed/delay correlation, and retain an independent held-out path. Determine
   when dispersion, temperature, boundaries or poor coupling require rejection
   or a different model rather than spurious precision.
7. **Blind physical closure:** prerecord outcomes/budgets; hold out whole
   specimens or defect locations; retain healthy/reference labels, independent
   defect truth and every repeat/failure. Compare task references to cyclic and
   appropriate fixed/random baselines under equal opportunities and cost;
   include no-reference, repeated-path and acquisition-gate ablations where
   appropriate. Report arrival prediction, position error, actual observed
   coverage, false confidence, rejection and stopping behavior separately.
8. **Frozen source/evidence:** fingerprint all relevant application, firmware,
   controller/configuration and experiment files; preserve raw captures,
   metadata, command frames, outcomes and source manifests. A later software
   change invalidates attribution of earlier results to the changed source
   unless it is explicitly assessed. Preserve negative results and model
   likelihood/planning differences in the manuscript.

The immediate defensible deliverable is this reproducible technical disclosure
and its implementation evidence. Filing scope, professional claim drafting,
ownership and publication sequencing require the real records above. No
outside patent contact, filing, payment or publication was performed.
