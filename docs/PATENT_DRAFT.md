# Pre-counsel patent specification draft

**Working title:** Posterior-conditioned control of physical interrogation experiments for hidden-state localization  
**Status:** confidential drafting input; not filed, not “patent pending,” and not a patentability or freedom-to-operate opinion  
**Human inventor(s), conception dates, assignee, related applications, and disclosures:** **must be completed from real records**

This document is written to preserve the implemented technical embodiment and meaningful alternatives. Counsel should revise terminology and claims after a professional claim search, inventorship interview, and jurisdiction-specific review.

## Abstract

A physical interrogation system maintains a probabilistic belief over a hidden state of an object and sequentially controls acquisition of responses from the object. Candidate experiments jointly specify an actuator location, a receiver location, and an excitation signal. For hypotheses selected from the belief, a forward-response model predicts respective measurement signatures under each candidate. A processor determines candidate utilities using separability among the predicted signatures and one or more execution or redundancy costs, selects an experiment, and provides placement guidance or actuator commands. A measured response is processed into a likelihood and recursively fused with the belief. Candidate generation, selection, acquisition, and fusion repeat until a belief criterion or resource budget is met. Embodiments use vibration or acoustic scattering, bistatic propagation delay, matched filtering, camera-based placement projection, and a physics model or learned surrogate. The control framework may be applied to other physical interrogation modalities.

## Technical field

The disclosure relates to nondestructive evaluation, active sensing, sequential Bayesian experimental design, wave-based hidden-state localization, physical control, signal processing, and guided or robotic placement of sensing components.

## Background

Fixed scanning systems commonly acquire a predetermined spatial grid or use a sensor network designed before inspection. Passive inference systems may estimate a condition from measurements but do not control which measurement is acquired next. Both approaches can spend a constrained measurement budget on responses that poorly distinguish the hidden states still plausible after earlier measurements.

Wave-based localization adds a geometric ambiguity. A propagation delay measured between a source and receiver through a scattering location generally supports an isochronal locus rather than a unique point. Repeated measurements from uninformative or redundant geometries may preserve that ambiguity. A technical need therefore exists for a system that uses the live multi-modal belief—not only local uncertainty or a predetermined model—to jointly choose physically executable actuation, reception, and excitation parameters that discriminate the remaining hypotheses while accounting for execution constraints.

## Summary of the disclosed system

An object model defines a physical coordinate frame and permissible experiments. A posterior belief represents one or more hidden-state variables, including a spatial condition. A candidate generator produces experiments containing at least actuation position, reception position, and excitation parameters. A counterfactual response predictor applies each candidate to selected hypotheses from the current posterior. A utility engine quantifies how distinguishable the predicted responses are, optionally estimates expected posterior entropy reduction, adds uncertainty coverage, and subtracts energy, time, motion, reachability, safety, or repetition costs. A controller selects the candidate and either commands hardware or communicates placement guidance to a human. A signal interpretation engine converts the acquired waveform into a likelihood. A posterior belief engine recursively fuses the likelihood with the previous belief. The loop repeats using the updated posterior.

The acoustic embodiment subtracts a calibrated nominal response, matched-filters the residual with a known excitation, and evaluates evidence near a candidate location’s source-to-location-to-receiver propagation delay. Different source/receiver geometries generate different isochronal evidence, allowing recursive fusion to resolve spatial ambiguity.

## Brief description of proposed drawings

- **FIG. 1:** closed-loop system architecture: object, experiment controller, actuator, receiver, acquisition, signal interpretation, posterior, counterfactual predictor, utility engine, and placement guidance.
- **FIG. 2:** sequence diagram for candidate generation, prediction, scoring, execution, acquisition, likelihood creation, recursive fusion, and termination.
- **FIG. 3:** panel geometry showing a source, receiver, hidden scatterer, direct path, scattered path, and an equal-delay ellipse.
- **FIG. 4:** posterior progression from uniform prior through several experiment-conditioned likelihood intersections.
- **FIG. 5:** candidate utility decomposition into response separation, represented posterior mass, coverage, energy/motion cost, and repetition penalty.
- **FIG. 6:** human-guided embodiment using four-corner camera homography to project source and receiver coordinates onto an object image.
- **FIG. 7:** alternative robotic and multi-modal embodiment with reachability and safety constraints.
- **FIG. 8:** calibration architecture in which propagation, noise, coupling, and nominal-response parameters are measured or represented as nuisance variables.

The repository UI, posterior histories, and architecture diagrams can be used as source material, but formal line drawings should be prepared to the filing office’s requirements.

## Detailed description

### 1. Object and hidden state

An object is represented in a normalized coordinate frame and may additionally store real dimensions, material parameters, allowable probe regions, obstacles, or robot kinematics. A hidden state `z` may include a defect location, extent, type, severity, count, or a physical field. The implemented embodiment uses a 20×20 discrete spatial probability grid and a single dominant localized defect while returning both a maximum a posteriori coordinate and a posterior mean.

### 2. Experiment representation

An experiment `e` contains:

```text
e = {actuator position, receiver position, frequency interval,
     amplitude, duration, waveform, modality, constraints}
```

Candidates may be enumerated, sampled, optimized continuously, retrieved from a safe library, or generated subject to physical reachability. Actuator and receiver locations are co-selected; neither needs to be fixed. Excitation parameters may include a chirp, impulse, sinusoid, coded waveform, power, duration, polarization, thermal input, RF waveform, electrical stimulus, force trajectory, or optical pattern.

### 3. Recursive belief

With existing measurements `D`, new response-derived evidence `y`, hidden state `z`, and executed experiment `e`, the posterior is updated as:

```text
p(z | D,y,e) ∝ p(y | z,e) p(z | D)
```

The previous posterior is retained as the next prior. Numerical floors, finite-value checks, and normalization prevent an invalid belief. Entropy, local posterior mass, peak probability, covariance, and confidence are derived from the distribution. Alternative implementations may use particles, continuous densities, mixtures, factor graphs, variational distributions, Gaussian processes, or ensembles.

### 4. Counterfactual response prediction

The processor selects spatially or parametrically competing hypotheses `zᵢ` from the current posterior. For each candidate experiment it predicts:

```text
s(zᵢ,e) = forward_response(zᵢ,e)
```

The implemented reduced-order acoustic signature includes time of flight, logarithmic gain, and phase components. The forward predictor may instead return a waveform, feature distribution, sensor image, or task output. It may be an analytical physical model, finite-element model, learned neural surrogate, Gaussian process, ensemble, hybrid residual model, or calibrated emulator.

“Counterfactual” here means a conditional prediction under alternative hidden-state hypotheses. It is not a claim about the cause of defect formation.

### 5. Candidate utility

The implemented real-time separability term uses posterior-weighted pairwise signature distances:

```text
D(e) = ΣᵢΣⱼ wᵢwⱼ [1 − exp(−||s(zᵢ,e) − s(zⱼ,e)||² / 2)]
```

An information proxy scales separation by current entropy and posterior mass represented by the selected hypotheses. The final utility combines information, separation, and coverage with costs:

```text
U(e) = α I_proxy(e) + β D(e) + κ C_coverage(e)
       − γ C_execution(e) − δ C_redundancy(e)
```

The cost may include excitation energy, duration, source and receiver motion, coupling operations, robot travel, expected damage, unsafe configurations, frequency reuse, acquisition latency, compute time, or similarity to prior experiments. Alternative embodiments calculate exact or Monte Carlo expected posterior entropy, task-specific decision value, Bayes risk, mutual information, expected utility, or a multi-objective Pareto score.

### 6. Acoustic signal interpretation

An emitted excitation reaches a receiver over a direct path and may scatter through a hidden anomaly. For source `S`, receiver `R`, and possible anomaly `z`, an expected scattered delay is:

```text
t(z) = t_system + [distance(S,z) + distance(z,R)] / wave_velocity
```

The implemented signal path removes DC, optionally filters and windows, subtracts a nominal direct response, correlates the residual with the known excitation, estimates a robust noise floor, and samples matched-filter evidence near `t(z)` for every grid cell. The scores are stabilized, smoothed, temperature-scaled according to signal-to-noise ratio, and normalized into a likelihood. Additional response features describe timing, spectral energy, resonance, decay, and noise.

### 7. Execution and guidance

The selected experiment may be automatically executed by a robot or probe controller. In a human-guided embodiment, the system presents normalized and real object coordinates, receiver coordinates, waveform parameters, a rationale derived from utility components, and ranked alternatives. A planar homography derived from four user-selected object corners maps the coordinates onto a camera image. Reachability, coupling, or safety confirmation may gate acquisition.

### 8. Calibration

A calibration profile may include a healthy-object response, propagation velocity, attenuation, resonance, system delay, sensor noise, amplitude scale, temperature, and coupling condition. Parameters may be fixed estimates or nuisance variables within a hierarchical posterior. Repeated reference measurements can identify coupling instability and out-of-distribution operation.

### 9. Termination and continuation

Automatic termination occurs when confidence exceeds a threshold, entropy falls below a threshold, expected information falls below a threshold, a task decision is sufficiently certain, or a measurement/resource budget is exhausted. A human or supervisory controller may request an additional experiment. The extra response is fused into the same posterior rather than starting a new independent prediction.

### 10. Alternative modalities

The control loop is not restricted to audible sound. A modality adapter may provide experiment execution, acquisition, preprocessing, feature extraction, likelihood generation, and forward-response prediction for ultrasound, thermal excitation, radio frequency, electrical impedance, optical structured illumination, force, or robotic tactile sensing. A controller may choose between modalities as part of the candidate experiment.

## Implemented example

The reference implementation contains a seeded direct-plus-scattered acoustic simulator, signal-processing pipeline, Bayesian grid, candidate generator, cost-aware counterfactual planner, FastAPI/SQLite service, scientific browser interface, camera homography, WAV/microphone/serial acquisition, and ESP32 firmware. A deterministic 600×400 mm easy case at seed 17 terminated at the confidence threshold after eight measurements with 10.0 mm simulated physical error. A 30-case paired medium benchmark found lower normalized posterior entropy for the adaptive policy than random and uniform-grid policies. These examples demonstrate operation under the declared simulator, not real-world inspection efficacy.

## Draft claim discussion set

These claims are issue-spotting language for counsel, not a recommendation to file them unchanged. References identified in `PRIOR_ART_NOTES.md` should be charted element by element before scope is selected.

1. **A physical interrogation system**, comprising: an interface configured to obtain responses from an object; a memory storing a probability distribution representing uncertainty in a hidden physical state of the object and a history of executed experiments; and one or more processors configured to: generate candidate experiments that each jointly specify an actuator location, a receiver location, and an excitation signal; select a plurality of hidden-state hypotheses according to the probability distribution; for each candidate experiment, use a forward-response model to predict respective responses corresponding to the plurality of hidden-state hypotheses; determine a utility of each candidate experiment from at least (i) separability among the respective predicted responses and (ii) a physical execution cost or a redundancy cost determined from the history; cause execution of a selected candidate experiment according to the utilities; obtain a measured response to the selected candidate experiment; recursively update the probability distribution using evidence derived from the measured response; and select a subsequent experiment using the updated probability distribution.
2. The system of claim 1, wherein the actuator location and the receiver location are independently movable and are co-selected for the candidate experiment.
3. The system of claim 1, wherein the excitation signal is specified by at least a frequency interval and a waveform type selected from a chirp, an impulse, a sinusoid, or a coded waveform.
4. The system of claim 1, wherein selecting the plurality of hidden-state hypotheses comprises selecting hypotheses from spatially separated modes of the probability distribution.
5. The system of claim 1, wherein each predicted response comprises a propagation-delay component and at least one amplitude, phase, spectral, resonance, or decay component.
6. The system of claim 1, wherein the separability comprises a posterior-weighted aggregation of pairwise distances between the respective predicted responses.
7. The system of claim 1, wherein the utility further comprises expected reduction in entropy calculated by sampling hypothetical responses and updating a copy of the probability distribution.
8. The system of claim 1, wherein the physical execution cost includes at least one of excitation energy, excitation duration, actuator movement, receiver movement, acquisition latency, robot travel, or a safety constraint.
9. The system of claim 1, wherein the redundancy cost is increased according to similarity between a candidate probe geometry or excitation spectrum and one or more experiments in the history.
10. The system of claim 1, wherein deriving the evidence comprises subtracting a calibrated nominal response and matched-filtering a residual response with the excitation signal.
11. The system of claim 10, wherein a likelihood for a candidate hidden location is determined using a source-to-candidate-to-receiver propagation delay.
12. The system of claim 1, wherein the recursive update preserves the updated probability distribution as a prior for processing the subsequent experiment.
13. The system of claim 1, further comprising a camera, wherein the one or more processors determine a planar mapping from an object coordinate frame to an image and display the selected actuator location or receiver location in the image.
14. The system of claim 1, wherein causing execution comprises commanding a robot subject to a reachability constraint or displaying placement instructions and awaiting a coupling or placement confirmation from a human.
15. The system of claim 1, wherein the probability distribution jointly represents the hidden physical state and at least one calibration or sensor-coupling nuisance parameter.
16. The system of claim 1, wherein the forward-response model comprises an ensemble or learned surrogate and the utility is further based on predictive uncertainty of the forward-response model.
17. The system of claim 1, wherein the candidate experiments include different physical sensing modalities and the selected candidate experiment selects a modality in addition to experiment parameters.
18. **A computer-implemented method of controlling physical interrogation of an object**, comprising: maintaining a posterior distribution over a hidden physical state based on responses to previously executed physical experiments; generating candidate experiments that jointly vary physical actuation, reception, and excitation parameters; predicting, for each candidate experiment, responses under competing hidden-state hypotheses selected from the posterior distribution; ranking the candidate experiments according to predicted response separation and an execution or history-dependent redundancy cost; communicating or executing a highest-ranked candidate experiment; acquiring a physical response; generating a likelihood from the acquired physical response and parameters of the executed experiment; recursively fusing the likelihood with the posterior distribution; and repeating the generating, predicting, ranking, communicating or executing, acquiring, and fusing using the recursively updated posterior distribution.
19. The method of claim 18, further comprising automatically terminating the repeating according to posterior entropy, posterior confidence, expected utility, or a resource budget, and accepting a supervisory continuation command that causes an additional measurement to be fused with the recursively updated posterior distribution.
20. **A non-transitory computer-readable medium** storing instructions that, when executed by one or more processors coupled to a physical acquisition interface, cause the one or more processors to perform the method of claim 18.

## Claim-scope questions for counsel

1. Does the closest art disclose sequential posterior-conditioned *joint* source/receiver/excitation selection, or only fixed placement, scan refinement, or inspection-location sampling?
2. Is weighted separation of live posterior modes with explicit history-dependent physical cost a distinguishing control mechanism over the cited Bayesian design work?
3. Which elements were actually conceived by each human contributor, and on what dates?
4. Which alternatives have adequate written-description support for the intended filing jurisdictions?
5. Should the first filing focus narrowly on acoustic bistatic interrogation and reserve the modality-independent controller for a continuation strategy?
6. Has any public disclosure, repository access, offer, demonstration, sale, or submission already occurred?

## Filing package still requiring human action

- confirmed legal names, residences, citizenship/domicile details if requested, and contribution-based inventorship;
- conception and reduction-to-practice chronology with corroborating records;
- assignee and funding/government-interest facts;
- complete disclosure log and the exact hackathon/publication date;
- formal drawings and inventor review of the specification;
- professional search, claim chart, and filing-strategy decision;
- signed forms, fees, and an official filing receipt.

The [USPTO provisional-application guidance](https://www.uspto.gov/patents/basics/apply/provisional-application) explains that a provisional must support the invention and expires after twelve months unless followed appropriately. The [USPTO’s AI-assisted-invention guidance](https://www.uspto.gov/subscription-center/2025/revised-inventorship-guidance-ai-assisted-inventions) applies human inventorship law; only actual natural-person inventors should be named. International disclosure consequences require jurisdiction-specific advice; see the [WIPO patent FAQ](https://www.wipo.int/en/web/patents/faq_patents).
