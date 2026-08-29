# Confidential invention disclosure draft — ARGUS

**Status:** counsel-ready engineering input, not a filed patent application. Complete human inventorship and dates before sending to counsel.

## Administrative record

- Working title: Adaptive recursive selection of physical interrogation experiments for hidden-state localization
- Human inventor(s): **[complete with counsel]**
- Conception date(s): **[complete]**
- First reduction to practice: repository build and deterministic demo logs, August 2026
- Public disclosures, hackathon dates, repository visibility, presentations, offers, or sales: **[complete immediately]**

## Technical field

Active nondestructive evaluation, sequential Bayesian experimental design, physical sensing, vibration/acoustic signal processing, and human-guided or robotic probe positioning.

## Problem

Conventional inspection typically fixes sensor positions or scan paths before seeing data, or uses AI only after acquisition. Such systems can spend time on measurements that do not distinguish the remaining plausible internal states. Uncertainty is often shown but not used to control the next physical intervention.

## Implemented system

ARGUS stores a probabilistic spatial belief over a hidden condition. After each waveform it removes/calibrates a nominal response, extracts signal evidence, maps propagation paths to likelihood, recursively updates the belief, identifies leading competing hidden-state hypotheses, predicts counterfactual responses under candidate actuator/receiver/excitation configurations, and selects a human- or machine-executable experiment according to predicted information, hypothesis disagreement, coverage, execution cost, and redundancy. The process terminates on quantitative belief criteria.

## Candidate inventive nucleus for counsel

1. Generate a candidate set whose members jointly specify actuation position, receiver position, excitation spectral content, amplitude, duration, and waveform.
2. Select multiple latent-state hypotheses from a recursive posterior, including spatially competing modes.
3. Predict a response signature for each `(hypothesis, candidate experiment)` pair with a physics model or learned surrogate.
4. quantify candidate usefulness from weighted separability of those predicted response signatures, not merely local posterior uncertainty.
5. Combine usefulness with physical execution costs and redundancy relative to measurement history.
6. communicate both coordinates and a causal, programmatically generated selection rationale to a human or actuator.
7. acquire the selected response and fuse it into the existing belief without discarding prior measurements.
8. repeat across acoustic, thermal, RF, impedance, optical, force, or tactile modality implementations using a shared experiment/belief contract.

The novelty and non-obviousness of this combination are unverified. See `PRIOR_ART_NOTES.md`.

## Concrete embodiment

The acoustic embodiment uses a panel coordinate frame, source and receiver points, chirp/impulse/sine excitation, a direct-plus-scattered wave model, time of flight `d(source,z)+d(z,receiver)`, attenuation, resonance, matched filtering, a 20×20 normalized probability field, and a counterfactual signature `[delay, log amplitude, sin phase, cos phase]`. A four-corner camera homography maps normalized selected coordinates to the physical panel. The ESP32 serial probe executes excitation/read commands.

## Demonstrated technical effects

- The closed loop runs locally without a model checkpoint or cloud service.
- A deterministic easy case at seed 17 reached 10.0 mm localization error after eight adaptive experiments on the 600 × 400 mm digital panel.
- The saved 30-case medium benchmark produced mean final normalized entropy 0.419 for ARGUS, versus 0.498 random and 0.621 uniform-grid probing. Paired entropy advantages were 0.079 versus random (bootstrap 95% CI 0.063 to 0.095) and 0.202 versus grid (0.180 to 0.224). Success within 15 mm was 73.3% for ARGUS, 56.7% random, and 60.0% grid. Mean errors were 12.33, 13.38, and 13.26 mm respectively, but paired error intervals crossed zero and are not claimed as statistically significant. These are simulator results only.
- A domain-randomized 3,000-sample forward-surrogate run early-stopped at epoch 27 with standardized Smooth L1 validation loss 0.2108, test loss 0.2245, standardized MAE 0.5014, and mean per-feature R² 0.409. This supports a learned-response embodiment but is not a field-accuracy result.
- Every selection is auditable through top-five component scores and a generated rationale.

## Alternative embodiments to preserve

- exact Monte Carlo expected posterior entropy in place of the fast overlap proxy;
- learned forward emulator, ensemble, Gaussian process, differentiable simulator, or finite-element solver;
- multiple simultaneous defects and joint type/size/severity belief;
- robot-controlled transducers or human placement with AR projection;
- candidate generation subject to reachability, safety, power, time, or sensor-coupling constraints;
- calibration treated as a hierarchical nuisance-parameter posterior;
- multi-modal experiments selected from different physical modalities in one loop;
- task-oriented utility such as pass/fail risk or repair decision value rather than location entropy.

## Evidence preservation checklist

- preserve dated source snapshots, benchmark outputs, lab notebooks, raw measurements, and design discussions;
- record who conceived each claimed feature and when;
- record every disclosure and NDA;
- do not edit benchmark outputs by hand;
- export diagrams and representative posterior histories for counsel.

## Filing caution

Public disclosure before filing can destroy novelty in many jurisdictions; the United States has a limited inventor disclosure grace period, but relying on it can eliminate foreign rights. A U.S. provisional must adequately describe the invention and does not itself mature into a patent. Current USPTO guidance applies ordinary human-inventorship law to AI-assisted inventions and permits only natural persons to be named. Engage qualified patent counsel before publishing or presenting claim-level details.
