# ARGUS complete project knowledge

Use this document as the canonical briefing before judging, technical review, or an IP meeting. It describes what the repository actually implements; it deliberately separates demonstrated results from future claims.

## The shortest correct explanation

ARGUS is an AI-guided physical interrogation system. It does not merely classify a recording. It maintains a probability map of where a hidden defect may be, predicts which possible source/receiver/waveform experiment would make the remaining hypotheses respond most differently, asks for or executes that experiment, fuses the new signal into the existing belief, and repeats until uncertainty is low enough.

## The problem

Traditional inspection commonly follows one of two patterns:

1. A fixed scan collects measurements everywhere, which is reliable but expensive and slow.
2. A model classifies measurements selected by a human, which can be intelligent about interpretation but passive about acquisition.

ARGUS addresses the experiment-selection problem: given limited time, energy, probe movement, and measurements, what physical intervention should be performed next to learn the most about the hidden state?

## What happens in one loop

1. Start with a normalized 2D prior over possible defect locations.
2. Enumerate physically executable experiments specifying source, receiver, frequency band, waveform, amplitude, and duration.
3. Take the highest-probability defect hypotheses from the current belief.
4. Predict a response signature for every hypothesis under every candidate experiment.
5. Score how strongly the candidate separates those predicted responses.
6. Add uncertainty coverage and subtract energy, movement, and repetition costs.
7. Recommend the highest-scoring candidate and explain the selection from its score components.
8. Simulate or acquire the waveform.
9. Remove the nominal response, matched-filter the residual, and turn time-of-flight evidence into a likelihood map.
10. Multiply that likelihood into the previous posterior and normalize.
11. Stop on confidence, entropy, or measurement budget; otherwise repeat.

## Why different probe geometries localize a defect

For one source `S`, receiver `R`, and possible defect location `z`, the scattered path length is:

```text
L(z) = distance(S,z) + distance(z,R)
```

Locations with the same `L(z)` form an ellipse. One measurement therefore tends to produce an elliptical band of plausible locations rather than a single point. A second source/receiver geometry produces a different ellipse. Recursive Bayesian fusion concentrates probability where multiple pieces of evidence agree. ARGUS chooses geometries whose predicted responses best separate the live competing regions.

## The simulator

The digital twin produces a time-domain signal containing:

- an excitation waveform: impulse, sine burst, or chirp;
- a direct source-to-receiver plate wave;
- a defect-scattered source-to-defect-to-receiver wave;
- propagation and system delays;
- distance attenuation and geometric spreading;
- defect severity, area, and type-dependent reflection sign/gain;
- frequency-dependent local resonance and damped ringing;
- white sensor noise and low-frequency drift.

Every run is seeded. It is a physically inspired reduced-order model, not a finite-element solver.

## Signal processing

ARGUS performs DC removal, optional bandpass filtering, windowing, FFT, Welch PSD, spectrogram, analytic-envelope extraction, and robust noise estimation. The exposed feature vector covers amplitude, impulsiveness, timing, spectral distribution, resonance/decay, and SNR without treating arbitrary audio features as inherently useful.

For spatial inference, the most important operation is matched filtering. The known nominal direct response is removed, the residual is correlated with the excitation, and each candidate location samples that correlation near its predicted bistatic delay.

## Bayesian belief update

For hidden location `z`, history `D`, candidate experiment `e`, and observed waveform-derived evidence `y`:

```text
p(z | D,y,e) ∝ p(y | z,e) · p(z | D)
```

The implementation uses numerical floors, non-negative likelihoods, and normalization checks. It reports:

- the maximum a posteriori cell;
- posterior mean location;
- peak probability and local probability mass;
- covariance/confidence ellipse;
- Shannon entropy and normalized entropy;
- a composite confidence measure.

Measurements accumulate. A new prediction never replaces the old posterior.

## Adaptive planner mathematics

For top hypotheses `zᵢ`, ARGUS predicts:

```text
s(zᵢ,e) = [time of flight, log gain, sin phase, cos phase]
```

Weighted pairwise response distances are converted to bounded distinguishability:

```text
D(e) = ΣᵢΣⱼ wᵢwⱼ [1 − exp(−||s(zᵢ,e)−s(zⱼ,e)||²/2)]
```

The final planner score is:

```text
score(e) = α · information-gain proxy
         + β · counterfactual disagreement
         + κ · uncertainty coverage
         − γ · execution cost
         − δ · repetition penalty
```

The information value is a fast proxy, not exact mutual information or a global optimality guarantee. The UI makes this approximation auditable instead of hiding it.

## What “counterfactual” means here

It is not a causal claim about how the defect formed. It means ARGUS asks a controlled predictive question:

> If hypothesis A were the hidden defect, what response would experiment E produce? If hypothesis B were true instead, how different would that response be?

The chosen experiment is one where competing hidden-state hypotheses predict strongly different measurements.

## Machine learning

The reliable default is the physics likelihood. An optional PyTorch forward surrogate learns `physical state + experiment → response features` from domain-randomized simulation data. The training path has seeded splits, standardization, CPU/GPU selection, Smooth L1 loss, AdamW, early stopping, checkpoint metadata, and a physics fallback.

This is intentionally pragmatic: the project does not force a neural network into the critical loop when interpretable physics is more dependable.

## Physical acquisition

Physical sessions can accept:

- PCM WAV upload;
- browser microphone captured and encoded as WAV;
- local OS microphone through `sounddevice`;
- serial ESP32/piezo or accelerometer samples.

The API rejects simulation execution and ground-truth reveal in physical sessions. Missing microphones or serial devices return explicit errors while simulation stays usable.

## Calibration

The reference profile records estimated noise, propagation velocity, resonance, attenuation context, and baseline RMS values. In a real deployment, calibration must use a healthy or otherwise characterized reference panel with repeatable sensor coupling.

## Camera positioning

The user clicks four physical panel corners in camera coordinates. ARGUS solves the eight-parameter planar homography and projects normalized next-probe and estimated-defect coordinates onto the live image. It is practical AR-lite, not ARCore/ARKit.

## Persistence and security

SQLite stores session state and experiment history. Raw float32 signals are compressed; ground truth remains server-side until reveal. WAV uploads are size/type validated, decoded in memory, and never executed. User-provided filenames are not used as filesystem paths. Serial input is parsed conservatively. The frontend stores only the last session identifier locally; the backend remains the source of truth.

## Benchmark interpretation

The benchmark uses identical seeded defect cases for random, uniform-grid, and ARGUS strategies. It records error, entropy, experiment count, execution cost, thresholds at 10/15/20/30 mm, full experiment trajectories, paired win rates, and bootstrap confidence intervals.

The saved 30-case medium run produced final normalized entropy 0.419 for ARGUS, 0.498 for random, and 0.621 for uniform grid. ARGUS reached ≤15 mm in 73.3% of cases versus 56.7% and 60.0%. Its paired entropy advantages were 0.079 over random (95% CI 0.063–0.095) and 0.202 over grid (0.180–0.224). Mean error favored ARGUS but its paired intervals crossed zero, so error superiority is not claimed as statistically established.

Do not say “ARGUS is proven more accurate in the real world.” Say:

> Under the declared simulator, ARGUS achieves lower uncertainty with comparable or better localization efficiency than non-adaptive baselines. Physical validation is the next milestone.

## Why this is a strong hackathon project

- The secret-defect reveal makes success emotionally and visually legible.
- Judges can see the AI make decisions, not only see a final classification.
- The top-five candidate table makes the planner falsifiable and auditable.
- Signal plots prove that real waveform processing exists under the interface.
- Baselines and limitations increase scientific credibility.
- The same software runs without hardware and has a concrete ESP32 path.
- Camera placement turns abstract normalized coordinates into a physical action.

## Novelty thesis — not a legal conclusion

The broad ingredients are not new. Bayesian wave localization, adaptive acoustic scanning, active-learning inspection, and optimal sensor placement all have prior art. The narrow combination worth professional investigation is:

1. a recursive posterior over a hidden physical state;
2. sequential, measurement-conditioned selection of a *joint* actuator/receiver/spectral/waveform experiment;
3. selection based on counterfactual predicted response separation among live competing hypotheses;
4. explicit physical execution and redundancy costs;
5. human- or robot-executable placement guidance and a score-derived explanation;
6. acquisition followed by recursive fusion into the same belief;
7. a modality-independent contract for replacing acoustic experiments with other physical interventions.

This differs from a fixed optimal sensor network, an uncertainty-selected inspection pixel, or Bayesian localization after a predetermined batch. Whether the combination is novel and non-obvious depends on claim-level prior-art analysis.

## Important adjacent art

- [EP2214009A2](https://patents.google.com/patent/EP2214009A2/en): Bayesian/probabilistic wave-based defect localization using source/sensor responses and a reference.
- [US6981417B1](https://patents.google.com/patent/US6981417B1/en): adaptive acoustic micro-imaging in which processed inspection information can affect subsequent scanning.
- [US9964468B1](https://patents.google.com/patent/US9964468B1/en): optimized structural-health sensor placement based on simulated damage scenarios.
- [US20230401694A1 / US12548141B2](https://patents.google.com/patent/US20230401694A1/en): active-learning selection of semiconductor substrate locations to inspect and use for model training.
- [Flynn and Todd, 2010](https://doi.org/10.1117/12.847744): Bayesian probabilistic structural modeling for ultrasonic guided-wave sensor placement.
- [Flynn and Todd, 2010, MSSP](https://doi.org/10.1016/j.ymssp.2009.09.003): Bayesian optimal sensor placement with an active ultrasonic sensing example.

## Patent and disclosure rules you must know

- This repository is not a filed patent application.
- A provisional application needs an enabling written description; a title and a few diagrams are not enough.
- A provisional expires after 12 months unless a corresponding nonprovisional filing preserves its benefit.
- The United States has a limited inventor-disclosure grace period, but pre-filing public disclosure can eliminate foreign rights.
- Only actual human inventors are named. AI tools can assist but are not inventors.
- Record conception dates, each human’s contribution, source history, disclosures, presentations, public repository dates, offers, and sales.

Do not say “patent pending” unless an application has actually been filed.

## Business framing

Potential domains include composite panels, aircraft/automotive parts, wind blades, civil structures, bonded assemblies, manufactured enclosures, and maintenance triage. The product value is fewer low-value measurements and guided inspection under a measurement budget.

The defensible long-term assets would be calibrated forward models, proprietary paired physical data, coupling/robotics know-how, workflow integration, and validated performance—not the heatmap UI alone.

## Honest limitations

- no field-validated defect-detection claim;
- one dominant defect in the current posterior;
- approximate experiment utility;
- calibration and probe coupling remain major sim-to-real problems;
- simplified wave propagation without boundaries, dispersion, or complex modes;
- text serial transfer is buffered rather than real-time streaming;
- camera alignment is manual;
- no safety certification.

## Best next scientific milestones

1. Build three panels with known cavities/delaminations and one healthy reference.
2. Create a repeatable spring-loaded source/receiver fixture.
3. Collect calibrated repeated measurements across temperature/coupling conditions.
4. Measure posterior calibration, error versus budget, and out-of-distribution failure detection.
5. Compare the proxy planner with Monte Carlo expected entropy under identical budgets.
6. Add multi-defect inference only after single-defect physical calibration is trustworthy.

## Thirty-second pitch

“Most defect AI waits for a human to choose measurements and then classifies them. ARGUS closes the loop. It maintains uncertainty about a hidden defect, simulates how competing hypotheses would respond to possible physical probes, and chooses the source, receiver, and waveform that should reduce uncertainty most after accounting for time, movement, and energy. Every real or simulated waveform updates the same posterior until the defect is localized. It is AI that decides what experiment to perform next.”

## Ninety-second technical pitch

“An acoustic source, receiver, and hidden defect define a bistatic path. A measured echo therefore supports an ellipse of possible defect locations. ARGUS starts with a uniform Bayesian grid, subtracts a calibrated nominal response, matched-filters the residual, and maps expected time of flight into a likelihood. The posterior accumulates every measurement. Before the next measurement, it finds the leading spatial hypotheses and predicts delay, gain, and phase signatures for dozens of candidate source/receiver/frequency configurations. It chooses the candidate with the best weighted hypothesis separation and uncertainty coverage after energy, motion, and repetition penalties. The UI shows the selected experiment, its top alternatives, the actual waveform and spectrum, the changing posterior, and a secret ground-truth reveal. A physics model guarantees a reliable demo; an optional neural surrogate shows the ML extension path.”
