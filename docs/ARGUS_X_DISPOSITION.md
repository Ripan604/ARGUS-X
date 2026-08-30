# ARGUS-X master problem disposition

## Executive decision

The 1,331 identified failure modes are now treated as an engineering risk register, not as a checklist that can be made true by adding model complexity. ARGUS-X closes the risks that are controllable in software, bounds the assumptions that are not, and makes physical, statistical, literature, and certification work explicit.

The current artifact is a research-grade autonomous inspection demonstrator. It is not an airworthiness system, maintenance-release authority, probability-of-detection qualification, medical device, or safety certification. No result from the simulator is represented as physical validation.

The complete item-by-item accounting is in:

- `docs/ARGUS_X_PROBLEM_REGISTER.md` — human-readable register;
- `docs/ARGUS_X_PROBLEM_REGISTER.csv` — filterable machine-readable register;
- `docs/ARGUS_X_PROBLEM_REGISTER.summary.json` — totals by disposition;
- `docs/ARGUS_X_MASTER_INVENTORY.txt` — immutable input snapshot;
- `scripts/build_argus_x_register.py` — deterministic register generator.

## What was added in response to this inventory

### 1. Explicit structural-integrity state

ARGUS now reports three mutually exclusive screening states whose probabilities sum to one:

1. healthy or no detectable damage under the tested conditions;
2. known damage candidate;
3. unknown or unsupported condition.

This closes the conceptual error of forcing every measurement into a known defect location. The healthy state is updated from bounded baseline-residual evidence; the unknown state is driven by OOD score and model trust. Neither is described as a certified probability of correctness.

### 2. Multiple candidate regions without a false multi-defect claim

The spatial posterior now exposes separated modes as candidate regions and a screening distribution over healthy, one candidate region, two-or-more candidate regions, and unsupported/unknown. This makes competing or multiple spatial modes visible.

It is not yet a validated joint multi-scatterer inverse solution. Closely spaced interacting defects, unknown defect count, and multi-defect ground-truth validation remain research obligations. The interface uses “candidate region,” not “confirmed defect instance.”

### 3. Conservative engineering-action layer

Predictions are translated into one of these bounded actions:

- `CONTINUE_INSPECTION`;
- `REACQUIRE_OR_REPAIR_SENSOR`;
- `MARK_REGION_AND_VERIFY_WITH_REFERENCE_METHOD`;
- `HUMAN_INSPECTION_REQUIRED`;
- `NO_DAMAGE_EVIDENCE_UNDER_TESTED_CONDITIONS`;
- `REVIEW_BEFORE_ENDING_RESEARCH_SESSION`.

The negative statement is as important as the positive one: ARGUS does not output “structure safe.” Human authority is required for any disposition other than continuing the research loop.

### 4. Persistent probabilistic sensor health

Every sensing channel receives an auditable beta-binomial reliability state. Accepted evidence is weighted by measurement quality; rejection is accumulated; repeated faults cannot be erased by one adequate sample. The monitor records rejected count, consecutive rejections, failure reasons, last quality, and reliability mean.

An unreliable channel forces abstention and caps decision confidence. A degraded channel forces caution and recommends redundant acquisition or coupling verification. Thus sensor failure cannot silently masquerade as a healthy structure.

### 5. Environmental-envelope monitoring

Temperature, humidity, and battery-voltage metadata establish a session baseline when present. Deviations outside a declared envelope are flagged. The current mechanism detects drift; it does not claim universal environmental compensation. Cross-temperature, cross-weather, and seasonal validation require representative longitudinal data.

### 6. Acquisition integrity controls

External measurements now enforce:

- finite values and minimum/maximum length;
- supported sampling-rate range;
- declared unit vocabulary;
- duplicate measurement-ID rejection;
- exact duplicate sample-payload rejection using SHA-256;
- timestamp validation for distributed probes;
- amplitude, duration, frequency, spacing, no-go, and human-rejected action constraints;
- persistent audit events for duplicate and timestamp failures.

These controls address corruption and accidental replay. Authentication, encrypted transport, secure boot, and adversarial penetration testing remain deployment work.

### 7. Latched emergency stop

Every session has a persisted emergency-stop state. Once latched, simulated, uploaded, probe, device, and calibration acquisition paths are blocked. Release requires explicit human acknowledgement and a reason. Both transitions are audit events. A process restart preserves the latch.

### 8. Failure taxonomy and post-mortem trace

The assurance API exposes the taxonomy requested by the inventory: physics mismatch, sensor failure, insufficient data, ambiguity, model error, planner error, domain shift, data corruption, physical execution error, and timing error. Runtime failures are stored with measurement index, sensor ID, and evidence reasons. Existing deterministic replay and evidence bundles support post-mortem analysis.

## Highest-priority problem disposition

| Priority | Current disposition | What proves it | Remaining work |
|---|---|---|---|
| BO1 Sim-to-real gap | Partially mitigated | online discrepancy model, nuisance calibration, OOD abstention, LMSD ingestion | representative paired hardware campaign |
| BO2 Simplified physics | Bounded | multifidelity forward models and explicit model trust | calibrated anisotropic guided-wave FEM/experiment twin |
| BO3 Calibration | Implemented for research outputs | reliability study, credible region, confidence cap | independent physical calibration and coverage study |
| BO4 OOD/abstention | Implemented and tested | ensemble/discrepancy/quality score with reject path | external OOD benchmark and threshold freeze |
| BO5 Single defect | Partially mitigated | separated candidate modes and count screening | joint multi-defect likelihood and physical mixtures |
| BO6 Location-only output | Partially mitigated | size/type/severity fields and integrity decision | validated characterization training labels |
| BO7 Dataset diversity | Partially mitigated | domain-randomized generator and public LMSD pipeline | more panels, materials, defect types, operators |
| BO8 Physical validation | Open external gate | protocol documented | blind, independently grounded experiment |
| BO9 Statistical power | Partially mitigated | paired seeds, bootstrap intervals, failure retention | prospective power-sized physical campaign |
| BO10 Leakage | Implemented in protocol | sealed truth, grouped splits, duplicate checks | audit every imported dataset license/split |
| BO11 Planner objective | Implemented as configurable | information, disagreement, Bayes-risk, cost, model trust | application-specific utility elicitation |
| BO12 Physical cost | Partially implemented | movement, time, energy, switching proxies | calibrated monetary/lifecycle coefficients |
| BO13 Risk model | Partially implemented | asymmetric false-negative loss and abstention | owner-approved consequence model |
| BO14 Sensor failure | Implemented and tested | channel reliability, abstention, fault injection | redundant physical sensor campaign |
| BO15 Environment | Drift detection implemented | session envelope monitor | compensation and longitudinal validation |
| BO16–18 Cross domain | Open validation gates | explicit OOD/discrepancy safeguards | held-out panels/materials/hardware |
| BO19 Unknown defects | Implemented as reject option | unknown state and human escalation | diverse unknown-defect challenge set |
| BO20 Characterization | Output schema only | screening fields are exposed and labeled unvalidated | calibrated labels and metrics for each quantity |
| BO21 Digital-twin calibration | Implemented online | nuisance posterior and discrepancy updates | physical identifiability/coverage study |
| BO22 Surrogate uncertainty | Implemented | ensemble disagreement and fidelity escalation | extensive decision-equivalence benchmark |
| BO23 Exploration/exploitation | Implemented | uncertainty coverage, separation, risk, redundancy | long-horizon physical comparison |
| BO24 Multi-step planning | Implemented as bounded beam horizon | receding-horizon planner | POMDP/RL only if it beats strong greedy baselines |
| BO25 Hardware loop | Prototype path implemented | phone, microphone, serial, WebSocket, firmware | true closed-loop robot/probe demonstration |
| BO26 Latency | Instrumentable | benchmark timing outputs | target hardware latency/power characterization |
| BO27 Reproducibility | Implemented | fixed seeds, configs, replay, bundles, doctor | container/CI publication if desired |
| BO28 Baselines | Implemented for simulator | random, uniform, greedy and ablation harness | literature-matched external baselines |
| BO29 Ablation | Implemented for major mechanisms | controlled feature removals | larger repeated physical ablation |
| BO30 Novelty verification | Preliminary only | prior-art notes and landscape | professional search and claim chart before filing |

## Final-system requirement disposition

| Requirement | Status | Boundary |
|---|---|---|
| BQ1 healthy vs damaged | Implemented screening state | not a certified POD decision |
| BQ2 localize | Implemented | model-domain dependent |
| BQ3 multiple defects | Partial | candidate modes, not validated joint inversion |
| BQ4 type | Partial | probability fields exist; no validated classifier |
| BQ5 size | Partial | posterior moment exists; no physical calibration |
| BQ6 severity | Partial | screening moment exists; no engineering severity standard |
| BQ7 uncertainty | Implemented | decomposed structural/metrology/model/OOD uncertainty |
| BQ8–9 OOD and abstain | Implemented | thresholds require target-domain calibration |
| BQ10–11 sensor faults/reliability | Implemented | basic channel model, not a full sensor digital twin |
| BQ12 environment adaptation | Partial | drift detection and nuisance calibration |
| BQ13 sim-to-real | Partial | discrepancy learning and multifidelity control |
| BQ14 between structures | Open validation gate | OOD prevents unsupported confidence |
| BQ15–18 next experiment/geometry/frequency/waveform | Implemented | constrained candidate search |
| BQ19 modality choice | Partial | software paths exist; no full multimodal policy benchmark |
| BQ20–22 cost/risk/redundancy | Implemented as configurable research utilities | weights require application owner |
| BQ23–26 stop/explain/abstain | Implemented | stopping is research-only |
| BQ27 sensor-failure operation | Implemented safe degradation | abstain/reacquire rather than force prediction |
| BQ28 realistic environment | Open physical gate | metadata/drift monitor only |
| BQ29 real prototype | Partial | phone/serial/microphone stack exists; blind campaign absent |
| BQ30 audit trail | Implemented | hash chain, events, export bundle |
| BQ31 real-time inference | Demonstrator-level | benchmark on target hardware before claim |
| BQ32 reproducible benchmarks | Implemented | simulation/public-data scope stated |
| BQ33 statistical uncertainty | Implemented in study tools | larger samples still needed |
| BQ34 cross-domain generalization | Open validation gate | no unsupported claim made |
| BQ35 blind physical validation | Open external gate | requires independent ground truth and sealed test |

## Definition of done for the physical program

The software program is ready to support the next experimental phase. The physical claim gate is not passed until all of the following are complete:

1. Freeze the intended use, minimum defect size, false-negative cost, and acceptable POD/confidence bounds.
2. Pre-register grouped splits by panel, material, environment, hardware, and defect family.
3. Determine sample count from prospective power analysis rather than convenience.
4. Use at least one independently characterized, sealed blind panel.
5. Include healthy panels, multiple real defect families, multi-defect cases, subtle/severe cases, sensor faults, sensor repositioning, and environmental shifts.
6. Compare against classical signal processing, uniform-grid sensing, random sensing, strong Bayesian greedy design, and non-physics learning under identical budgets.
7. Report false negatives, false positives, POD curves, localization/size/severity errors, calibration coverage, abstention utility, cost, latency, energy, and failure cases with confidence intervals.
8. Freeze models and thresholds before opening blind ground truth.
9. Preserve every acquisition, rejection, override, configuration, model/twin version, and result in the evidence bundle.
10. Ask a qualified structural/NDT authority—not this software—to decide whether evidence supports a field trial or certification program.

## Patent and publication boundary

The defensible invention theme remains the specific closed-loop interaction among joint structural/metrology belief, dual diagnostic-calibration control, discrepancy-aware multifidelity counterfactual planning, and fail-closed OOD/sensor-health logic with verifiable evidence. Individual components such as Bayesian design, GNNs, digital twins, guided waves, or generic AI defect detection are not claimed as firsts.

A grant is possible only if a professional search supports novelty and non-obviousness over the exact interaction. Commercial interest is possible because measurement compression, auditable autonomy, and fail-closed operation target expensive inspection workflows, but licensing value will depend far more on physical performance, proprietary data, integration cost, and certification pathway than on the simulator or manuscript alone.
