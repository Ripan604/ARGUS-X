# Patent technical disclosure notes

This is an engineering disclosure aid, not legal advice and not a patentability, inventorship, freedom-to-operate, validity, grant, licensing, or valuation opinion. A qualified patent professional must compare claims against worldwide patent and non-patent prior art before public disclosure.

## Technical nucleus A: joint defect–metrology posterior

- Problem: an adaptive locator can confuse propagation, timing, coupling, pose, or model error with structure and become overconfident.
- Inputs: waveform samples, experiment geometry/waveform, direct-path diagnostics, signal/placement/coupling proxies, residual history.
- Transform: a spatial structural posterior is updated with quality-tempered likelihood while factorized nuisance distributions and an online discrepancy model update separately.
- Physical effect: calibrated nuisance means alter predicted propagation and therefore change the next source/receiver/waveform.
- Output: separate structural/metrology uncertainty, corrected model prediction, trust/OOD, and action rationale.
- Alternatives: particles, Gaussian mixtures, Laplace/variational distributions, Gaussian processes, learned residual ensembles, or full hierarchical Bayes.

## Technical nucleus B: adaptive diagnostic/calibration switching

- Problem: a detector-only controller spends measurements on the specimen when inspection-system uncertainty dominates.
- Transform: compare expected diagnostic value with metrology-reduction value, OOD, trust, and diminishing calibration return.
- Changed action: select direct-path, repeat, reference, sweep, pose, or level calibration instead of defect discrimination.
- Feedback: calibration updates nuisance state but supplies no structural likelihood; the controller then recomputes counterfactual diagnostic actions.
- Measurable effects: nuisance variance change, model-trust change, false-confidence/measurement/motion changes against a no-calibration ablation.

## Technical nucleus C: counterfactual waveform/geometry co-design

- Problem: fixed excitation/geometry may produce nearly identical observations under rival hidden states.
- Transform: predict distributions under top hypotheses and nuisance samples; compute JS/Bhattacharyya/KL/variance/worst-pair separation; combine information/risk/calibration value with motion, energy, time, repetition, feasibility, and trust.
- Changed action: jointly select TX, RX, family, band, amplitude, duration, code/notches, sampling, and evaluation fidelity.
- Alternatives: exact nested Monte Carlo EIG, Bayesian optimization, differential evolution, learned policy, or robotic trajectory planning.

## Technical nucleus D: discrepancy-directed fidelity and abstention

- Problem: cheap/surrogate models fail locally and can make high-confidence decisions.
- Transform: track residuals by frequency/path/geometry/material/session, predict correction/uncertainty, choose fidelity, and conservatively fuse residual/conformal/ensemble OOD scores.
- Changed action: invoke physics/imported data, calibrate, verify, or abstain rather than trusting an unsupported surrogate.
- Measurable effects: residual before/after correction, model choice/cache cost, false confidence, abstention, and localization under paired mismatch.

## Technical nucleus E: physical-quality-aware action selection

Coupling, repeat consistency, direct energy, spectral stability, motion, and visual placement error alter evidence weight, nuisance uncertainty, feasibility, and next action. Alternative embodiments use force sensors, optical trackers, robotic encoders, or calibrated transducers.

## Technical nucleus F: adaptive-decision evidence chain

Each physical action is linked to raw/processed/posterior hashes, calibration/OOD state, model fidelity, score decomposition, software revision, and predecessor. This binds the reason an adaptive action was chosen to the measurement and belief transition it caused. Alternatives include signed manifests, hardware roots of trust, external timestamping, or append-only institutional storage.

## Evidence needed before claim drafting

Preserve dated human conception records; identify human contributors to each mechanism; run a professional search; capture paired ablations and failure cases; preserve result bundles and source revisions; and avoid asserting broad ownership over established Bayesian experimental design, active sensing, NDE sensor placement, calibration, OOD, or hash chaining. The potentially distinctive subject for counsel is the specific closed-loop combination and physical feedback, not the component buzzwords in isolation.

