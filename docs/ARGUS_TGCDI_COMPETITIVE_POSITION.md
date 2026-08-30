# ARGUS TG-CDI: Competitive, Patent, and Commercial Position

Date of landscape review: 30 August 2026  
Status: engineering and business positioning; not legal advice or a patentability/freedom-to-operate opinion

## Executive answer

ARGUS is not yet better than established NDT leaders as a complete inspection product. Those companies have superior transducers, channel counts, imaging fidelity, rugged hardware, trained operators, installed bases, qualified procedures, and field evidence.

The credible invention and licensing wedge is narrower: **trust-gated counterfactual dual-control interrogation (TG-CDI)**. It is an inspection-planning/control layer for situations where measurements, movements, access, energy, or time are scarce. Instead of accepting a predetermined raster scan or permanent sensor layout, it uses the current uncertainty to decide:

1. which structural explanations still genuinely compete;
2. whether the next physical action should diagnose the structure, calibrate the measuring process, verify a tentative conclusion, explore, or abstain;
3. which safe source position, receiver position, waveform, and model fidelity should best distinguish the hardest remaining rivals;
4. how strongly the new observation is allowed to change structural belief given signal quality, sensor reliability, model discrepancy, and out-of-distribution evidence; and
5. how to preserve the selection rationale, physical settings, raw-response hash, model identity, and posterior transition as one replayable evidence record.

This ordered interaction—not “AI plus acoustics”—is the candidate patent nucleus. Its commercial claim must be tested as: **fewer or lower-cost physical interrogations to reach a fixed decision risk, without increasing false negatives or unsupported stops**.

## 1. What TG-CDI does

At iteration `t`, ARGUS holds a joint belief

`b_t(z, eta) = p(z, eta | D_t)`,

where `z` contains structural variables such as location, effective size, severity, and defect family, while `eta` contains measurement-system variables such as wave velocity, attenuation, time offset, gain, noise, coupling, and probe-pose error.

### Step 1 — Construct live rivals

ARGUS extracts separated modes from the current structural posterior. These are not a permanent list of classes. They are the plausible explanations that remain after all evidence so far.

### Step 2 — Predict candidate-specific outcomes

For every safe candidate experiment `e` and rival `h_i`, it predicts an observation distribution

`q_i,e(y) = integral p(y | z, eta, e) b_t(z, eta | h_i) dz d eta`.

The implemented compact form uses forward-response feature means and nuisance-dependent predictive variances. It combines Jensen–Shannon, Bhattacharyya, symmetric-KL, predictive-variance, and worst-pair terms.

### Step 3 — Protect the hardest rival

Average information gain can look good while leaving one important pair unresolved. TG-CDI therefore includes a worst-rival score:

`S_min(e) = min_(i != j) S(q_i,e, q_j,e)`.

This rewards an experiment that separates the most confusable live alternatives, not only one that performs well on average.

### Step 4 — Decide what kind of physical action is justified

The controller compares:

- diagnostic value: expected reduction in structural decision risk and rival ambiguity;
- calibration value: expected reduction in metrology uncertainty and increase in model trust;
- verification value: repeatability or an orthogonal confirmation before stopping;
- exploration value: broad coverage when posterior structure is weak;
- abstention value: avoidance of an unsupported structural conclusion; and
- physical cost: movement, time, excitation energy, repetition, device availability, no-go regions, and safety.

The winner is selected from the safe action set. If the model is untrusted and calibration or verification cannot restore support, the correct output is abstention—not a forced defect location.

### Step 5 — Gate the evidence, not only the displayed confidence

The likelihood is tempered before fusion:

`b_(t+1) proportional_to b_t * p(y_t | z, eta, e_t)^beta_t`,

with `beta_t` determined by acquisition quality, accumulated channel reliability, model trust, discrepancy, OOD state, and mismatch temperature. `beta_t = 0` means the packet does not sharpen structural belief. A calibration-only action updates nuisance state while suppressing structural updating.

### Step 6 — Bind decision and evidence

The system records candidate scores, selected physical settings, deterministic rationale, response checksum, model identity, prior and resulting belief, decision, and hash link. This is useful for replay, investigation, regulated-development evidence, and OEM integration. Hashing alone is not the invention; its causal binding to the adaptive physical decision is the relevant combination.

## 2. Where ARGUS is prospectively better—and where it is not

| Dimension | Established leaders | Prospective TG-CDI advantage | Present ARGUS gap |
|---|---|---|---|
| Acquisition hardware | Industrial arrays, robots, permanent networks, calibrated instruments | Hardware-agnostic planning layer can sit above sparse or reconfigurable sensing | Prototype transducers/acquisition are not qualified |
| Inspection strategy | Dense scan, electronic focusing, fixed network, long-range screening, or passive monitoring | Chooses the next physical experiment from the live posterior and current trust state | No physical proof yet that it needs fewer actions |
| Ambiguity handling | Strong reconstruction or operator interpretation | Explicit live rivals plus hardest-rival discrimination | Compact single-dominant-anomaly representation |
| Metrology errors | Calibration is normally a procedure or subsystem | Calibration actions compete directly with diagnostic actions for the next scarce measurement | Calibration policy is an engineering approximation |
| Domain shift | Mature procedures and expert judgment | Model discrepancy/OOD/reliability can temper or block belief updates | Poor small-sample calibration has already been observed |
| Decision behavior | Product- and procedure-specific | Explicit verify, escalate, and abstain states under configured losses | Losses are not certified maintenance economics |
| Auditability | Mature reporting ecosystems | One replayable causal chain from recommendation through posterior transition | Needs independent security/replay audit |
| Deployment maturity | Field deployments, service organizations, certifications | Potentially lightweight SDK/OEM integration | No POD campaign, blind-panel study, certification, or installed base |

The defensible language is **“prospectively more measurement-efficient for constrained sequential inspection”**, not “more accurate than every leader.” Accuracy, probability of detection, false-alarm behavior, and cost must be compared at matched operating points.

## 3. Competitor and adjacent-system map

### Gecko Robotics / Cantilever

Public position: robotic inspection captures high-fidelity asset data; Cantilever unifies data and supports analysis and repair planning.  
Official source: https://www.geckorobotics.com/

ARGUS distinction: TG-CDI is intended to optimize the next information-bearing interrogation rather than treat dense coverage as the default acquisition product.  
ARGUS disadvantage: no industrial robot fleet, throughput record, deployment evidence, or comparable asset-scale digitalization.

### Evident OmniScan X3

Public position: phased-array ultrasonics, FMC/TFM, phase-coherence imaging, large apertures, scan planning, and high-resolution inspection.  
Official source: https://ims.evidentscientific.com/en/products/flaw-detectors/omniscan-x3

ARGUS distinction: selects movable bistatic geometry, waveform family, model fidelity, calibration, verification, or abstention under joint uncertainty.  
ARGUS disadvantage: much lower acoustic fidelity, channel count, resolution, qualification, and field maturity.

### Eddyfi Sonyks / Teletest

Public position: long-range ultrasonic guided-wave testing for pipe screening, supported by dedicated tooling, procedure, training, and domain heritage.  
Official source: https://www.eddyfi.com/en/news/eddyfi-technologies-proudly-introduces-sonyks-the-next-generation-of-guided-wave-testing

ARGUS distinction: sequential posterior-conditioned action choice on a bounded accessible surface.  
ARGUS disadvantage: cannot match pipe-specific range, established tooling, standards, and field credibility.

### Acellent SMART Layer

Public position: permanently attached, precisely located PZT sensor networks for active and passive structural health monitoring.  
Official source: https://www.acellent.com/products/smart-layer-sensors

ARGUS distinction: treats source/receiver placement and excitation as reconfigurable decision variables and explicitly arbitrates calibration versus diagnosis.  
ARGUS disadvantage: lacks the repeatability, ruggedization, and longitudinal evidence of an installed network.

### MISTRAS AEScout

Public position: passive acoustic-emission monitoring for active damage mechanisms, source localization, and expert-assisted interpretation.  
Official source: https://www.mistrasgroup.com/resources/newsroom/2026/07/15/mistras-launches-aescout-help-industrial-operators-detect-active/

ARGUS distinction: actively creates the next discriminating wave experiment and can request verification or abstain.  
ARGUS disadvantage: it cannot replace continuous passive AE monitoring of damage activity or the surrounding service expertise.

### NIST SAMS (adjacent research, not a product competitor)

Public position: physics-informed machine learning, active learning/Bayesian optimization, adaptive calibration, and autonomous metrology.  
Official source: https://www.nist.gov/programs-projects/machine-learning-driven-self-correcting-autonomous-metrology-systems-sams

Relevance: this strongly limits any broad claim to self-correcting active metrology. The patent argument must be tied to the particular acoustic rival-discrimination, action arbitration, trust-tempered evidence, and physical execution sequence.

## 4. Prior-art boundary

Known reviewed references already occupy major pieces of the landscape:

- Flynn and Todd, Bayesian sensor/actuator placement for active guided-wave structural health monitoring, *Mechanical Systems and Signal Processing*, 2010, DOI: https://doi.org/10.1016/j.ymssp.2009.09.003
- Cantero-Chinchilla et al., robust Bayesian guided-wave damage localization, 2019, DOI: https://doi.org/10.1016/j.ymssp.2018.12.021
- Hall and Michaels, multi-path active guided-wave defect detection/localization/characterization, U.S. Patent 10,126,274 B2: https://ntrs.nasa.gov/citations/20190000745
- Giurgiutiu, Bao, and Zagrai, embedded Lamb-wave structural radar, EP 1 514 217 A2: https://patents.google.com/patent/EP1514217A2/en
- FEI Electron Optics, recursive Bayesian digital-twin calibration and active instrument-setting adjustment, EP 4 592 907 A1: https://data.epo.org/publication-server/rest/v1.2/publication-dates/2025-07-30/patents/EP4592907NWA1/document.pdf
- Boeing, pseudo-baseline structural health monitoring with guided-wave sensor pairs, US 2025/0377339 A1: https://patents.google.com/patent/US20250377339A1/en

Therefore, do not attempt to patent these broad ideas alone:

- AI or machine learning for acoustic defect detection;
- Bayesian guided-wave localization;
- choosing sensor locations using information gain;
- active learning or Bayesian optimization of measurements;
- digital-twin calibration;
- waveform or frequency selection;
- OOD detection or confidence gating;
- an inspection dashboard; or
- a hash-chained log.

## 5. Candidate claim architecture for counsel

This is invention-disclosure language, not a ready-to-file legal claim.

### Candidate independent method nucleus

A computer-controlled structural interrogation method in which one or more physical acoustic sources and receivers interrogate a structure, comprising:

1. maintaining, from prior acoustic observations, a joint machine-readable belief over a structural state and a measurement-system state;
2. deriving from the structural belief a plurality of currently competing, spatially separated structural hypotheses;
3. for each of a plurality of physically executable source–receiver–waveform candidate actions, generating hypothesis-conditioned predicted acoustic-observation distributions while marginalizing at least part of the measurement-system uncertainty;
4. determining an average hypothesis-separation value and a minimum or worst-rival separation value for each candidate action;
5. within one action-selection process, comparing a structural diagnostic value with a measurement-system calibration value and at least one verification, exploration, or abstention value;
6. selecting and causing execution of a safe candidate physical action based on decision-loss reduction, the worst-rival separation, measurement-system calibration value, model trust, and physical cost;
7. computing an evidence exponent from at least acquisition quality and model-domain support, and tempering or suppressing a structural likelihood update using that exponent; and
8. storing a causally linked record associating the selected action and rejected alternatives with a response integrity identifier, model identity, and belief transition.

### Useful dependent-claim families to discuss

- Source/receiver motion and no-go-region constraints.
- Joint selection of waveform family, frequency band, amplitude, duration, and fidelity.
- Calibration action types: direct path, timing, coupling repeat, healthy reference, pose, receiver level, or frequency sweep.
- A zero structural evidence exponent for calibration-only or rejected packets.
- Evidence exponent based on accumulated beta-binomial channel reliability.
- Abstention when all safe action values are unsupported or trust is below threshold.
- Verification chosen before a stop decision when rivals or repeatability remain material.
- Worst-rival separation computed from Jensen–Shannon, Bhattacharyya, symmetric-KL, Mahalanobis/predictive variance, or a weighted combination.
- Receding-horizon selection over executable action sequences.
- A robot, handheld guide, edge node, or fixed multiplexer causing the selected action.
- Hash-linked replay package binding alternatives, action, waveform, observation, posterior transition, and software/model version.

### Likely examiner/defendant arguments

- Every component was independently known.
- Combining Bayesian experimental design, calibration, robust updating, and audit logging was obvious to try.
- The claims are mathematical decision logic without enough physical limitation.
- “Model trust,” “rival,” or “value” is indefinite unless operationally defined.
- The specification does not enable the full claimed breadth across materials, geometries, defects, and modalities.
- Reported simulation results do not prove an unexpected technical effect.

### Counter-position that needs evidence

The combination produces a specific physical measurement-control effect that no component alone provides: under measurement-system shift and limited physical access, the controller sometimes spends the next action calibrating rather than diagnosing, then chooses the acoustic shot that protects the hardest live structural distinction, and limits how much that observation can alter structural state according to verified support. A blind, preregistered ablation must show that this ordered coupling reduces safe measurement cost at matched decision risk and prevents unsupported stopping.

## 6. Is a patent grant possible?

Yes, a grant is possible, but no responsible assessment can give a reliable probability from this preliminary review. The most favorable path is a narrow, hardware-anchored filing supported by:

- a dated invention disclosure and complete code/version provenance;
- named human inventors based on conception of each claimed element;
- an element-by-element search by patent counsel, including non-patent literature;
- a specification with executable embodiments, fallback positions, and concrete sensor/control details;
- experimental evidence of the claimed technical effect;
- claims directed to physical acquisition/control and data-quality effects, not an abstract business decision; and
- filing before non-confidential disclosure where the applicable jurisdiction requires absolute novelty.

Risk remains meaningful because the field is crowded and several reviewed documents cover close subsets. “Patent granted” also does not mean “free to operate”; a product may still practice another party’s broader or separate claims.

## 7. Can companies license or buy it?

Potentially, but companies normally buy evidence and integration readiness, not only an algorithm description. The natural targets are NDT instrument OEMs, inspection robotics companies, SHM-network suppliers, monitoring/service providers, and asset-integrity software vendors.

### Most credible offer

An **adaptive inspection orchestration SDK** that accepts:

- an admissible action set from the OEM hardware;
- measured waveform/features and quality metadata;
- geometry, access, time, energy, and safety constraints; and
- an OEM forward model or ARGUS adapter;

and returns:

- the next diagnostic/calibration/verification action;
- decomposed value and risk terms;
- trust/OOD/abstention status; and
- a signed or hash-linked replay record.

### Business models

- OEM SDK license plus integration and validation fee.
- Per-instrument or per-robot runtime royalty.
- Per-asset or per-inspection usage license.
- Joint development for one narrow asset class.
- Field-of-use exclusive license after validation.
- Assignment/buyout only after IP diligence and evidence; retain milestone or royalty upside where possible.

### What makes a buyer engage

1. One narrow beachhead: for example, low-channel composite-panel inspection with costly probe moves.
2. A complete physical counterfactual bank and blind test.
3. Results against strong baselines at matched false-negative risk.
4. A component ablation proving the TG-CDI combination, not merely the forward model.
5. An integration API, deterministic replay, latency/resource profile, and security review.
6. A patent filing and clean code/data/IP ownership records.
7. A quantified ROI: time, robot travel, couplant/remount operations, energy, operator interventions, or avoided reference inspections.

## 8. Required validation gates

### Gate A — Bench integrity

- Synchronized acquisition and excitation.
- Repeatable coupling/force or measured coupling metadata.
- Healthy references before and after damage blocks.
- Temperature/humidity and remount identifiers.
- Independent defect truth.

### Gate B — Complete response bank

Record every admissible action for every hidden state so all policies query identical physical outcomes. This prevents an adaptive policy from receiving easier measurements than its baselines.

### Gate C — Preregistered baselines and ablations

Compare raster, uniform, random, fixed-network reconstruction, entropy-only selection, and the full method. Disable calibration arbitration, trust tempering, and worst-rival protection one at a time.

### Gate D — Decision metrics

Primary: measurement count and physical cost to a fixed decision-risk operating point.  
Secondary: localization error, probability of detection with confidence bounds, false-positive and false-stop rates, abstention, calibration coverage, robustness to remount and temperature shift, wall-clock time, and failure disposition.

### Gate E — Blind specimen holdout

Freeze the controller, losses, thresholds, and analysis before truth is revealed. Hold out complete specimens, not correlated waveforms from known specimens.

### Gate F — Product diligence

- Safety and hazard analysis.
- Cybersecurity and evidence-integrity review.
- Latency and edge-resource validation.
- Relevant NDT qualification/certification pathway.
- Patentability, freedom-to-operate, inventorship, open-source, dataset-license, and contractor-assignment review.

## 9. Exact language to use with judges, investors, and counsel

### Strong, defensible one-sentence pitch

“ARGUS TG-CDI is an adaptive acoustic interrogation controller that decides whether to calibrate the measuring process or which safe physical experiment to run next, explicitly targets the hardest live structural ambiguity, and limits belief updates when the sensor or model is not trustworthy.”

### Strong technical differentiation statement

“Existing products excel at dense robotic acquisition, phased-array imaging, long-range guided-wave screening, permanent sensor networks, or passive acoustic-emission monitoring. ARGUS is a complementary orchestration layer for constrained sequential measurement: it chooses the next source–receiver–waveform action from joint structural and metrology uncertainty, can abstain, and preserves a replayable causal record.”

### Do not say yet

- “It is the first in the world.”
- “It is patented” or “patent guaranteed.”
- “It detects defects better than Gecko/Evident/Eddyfi/Acellent/MISTRAS.”
- “It is ready for safety-critical inspection.”
- “It reduces measurements” without specifying the simulation-only context or completing the physical study.
- “OOD detection guarantees safety.”

### Honest current evidence statement

“The implementation and assurance mechanisms are test-covered. An earlier matched-model simulation showed faster posterior concentration than simple random and grid policies, but localization-error superiority was not established. Small NEO studies verify software behavior and expose calibration weaknesses. The product and patent thesis therefore remains a precise, testable hypothesis pending blind physical validation.”

## Bottom line

There is a potentially valuable algorithm here, but its value is in a narrow sequence of physical control decisions, not the vast category of acoustic AI. The strongest strategy is to file and test around TG-CDI as a hardware-anchored orchestration method, choose one constrained inspection use case, prove fewer safe interrogations at matched decision risk, and partner with established hardware providers. If that evidence succeeds, ARGUS can be positioned as technology those leaders integrate rather than another immature instrument trying to replace them.
