# ARGUS judge and technical Q&A

## Product questions

### What is ARGUS in one sentence?

AI that chooses the next physical experiment instead of only interpreting a measurement chosen by someone else.

### What is the user problem?

Scanning every point is slow and costly, while fixed or human-selected measurements may be redundant. ARGUS allocates a limited measurement budget to probes predicted to resolve the current ambiguity.

### What is the live demo proving?

It proves that the complete closed loop executes: signal generation/acquisition, evidence extraction, belief update, experiment comparison, cost-aware recommendation, persistence, termination, and reveal.

### What is it not proving?

It does not prove certified real-world NDT accuracy. The benchmark is simulator evidence and the physical interface is a research acquisition path.

## Algorithm questions

### Is this just a classifier?

No. A classifier maps one observation to a label. ARGUS maintains state across observations and controls the next experiment parameters.

### Why Bayesian inference?

It represents multiple plausible locations, supports principled evidence accumulation, exposes uncertainty, and gives the planner a distribution rather than an overconfident point estimate.

### Why does one measurement produce an ellipse?

All points with equal source-to-point plus point-to-receiver distance have the same bistatic time of flight. That locus is an ellipse.

### What exactly is expected information gain?

Exact EIG is current entropy minus expected posterior entropy after a hypothetical observation. ARGUS uses a real-time proxy based on the predicted response overlap of leading hypotheses, scaled by current entropy and represented posterior mass.

### Why not call it optimal?

The candidate set is finite and the utility is approximate. “Highest-scoring candidate under the implemented approximation” is accurate; “globally optimal experiment” is not.

### What is hypothesis disagreement?

The weighted pairwise separation between the responses that competing defect hypotheses predict for one candidate experiment.

### What prevents repeated measurements?

A history-conditioned penalty increases when source locations and frequency bands resemble earlier experiments.

### What are the costs?

Drive energy, duration, source movement, frequency repetition, and redundant geometry. The prototype’s implemented cost is primarily normalized excitation energy plus movement and a separate repetition term.

### How does ARGUS stop?

Confidence threshold, normalized entropy threshold, or maximum experiment count. Physical users can still provide a manual measurement after automatic criteria if needed.

## Physics and signal questions

### Is the simulator random labels?

No. It synthesizes time-domain direct and scattered paths from physical distance, wave velocity, delay, attenuation, defect properties, resonance, damping, and noise.

### What does matched filtering do?

It correlates the residual response with the known excitation, concentrating energy at likely echo delays and improving detection under noise.

### Why subtract a baseline?

The direct path is usually stronger than the defect scatter. A calibrated nominal response exposes the structural change that carries localization evidence.

### Which features are extracted?

RMS, peak, crest factor, zero-crossing rate, spectral centroid/bandwidth/rolloff/entropy, dominant frequency, band energies, envelope peak time, decay, robust noise, and SNR.

### Why not MFCCs?

MFCCs are useful for perceptual audio but are not automatically physically meaningful for this reduced-order vibration problem. ARGUS uses features tied to timing, energy, spectrum, resonance, and decay.

## ML questions

### Where is the AI?

In sequential decision-making under uncertainty, counterfactual response prediction, Bayesian recursive inference, and the optional learned forward-response surrogate. AI is not restricted to deep classification.

### Why use physics by default?

It is interpretable, data-efficient, and dependable for a prototype. The learned surrogate is optional so a missing checkpoint cannot break the core demo.

### How is training data generated?

Domain randomization varies panel dimensions, material propagation, attenuation, resonance, noise, defect geometry/type/severity, probe geometry, band, waveform, and amplitude.

### How would sim-to-real be addressed?

Healthy-panel calibration, paired controlled defects, repeat measurements under nuisance conditions, fine-tuning or residual learning, posterior calibration, and out-of-distribution detection.

## Benchmark questions

### Are the numbers fabricated?

No. The command writes per-run JSON and CSV. The repository includes seeds, individual runs, trajectories, paired comparisons, and bootstrap intervals.

### Why compare with random and grid probing?

Random is a minimal non-adaptive baseline; uniform grid represents structured brute-force coverage. Both isolate whether measurement-conditioned experiment choice adds value.

### Which metric matters most?

For this prototype, normalized posterior entropy under a fixed experiment budget is the clearest planner metric. Localization error matters too, but simulation error alone does not show uncertainty quality.

### What are the measured headline numbers?

Across 30 paired medium cases, final normalized entropy was 0.419 for ARGUS, 0.498 random, and 0.621 grid. Success within 15 mm was 73.3%, 56.7%, and 60.0%. The paired entropy confidence intervals exclude zero; paired localization-error intervals do not, so claim uncertainty reduction and threshold success—not statistically proven error superiority.

### Why can error briefly get worse?

Noisy Bayesian measurements can move the MAP cell before later evidence corrects it. Requiring monotonic error would be scientifically incorrect.

## Hardware questions

### Does it run without hardware?

Yes. The full simulation loop is mandatory and is the reliable judge mode.

### What hardware is supported?

Browser/local microphone, WAV, and an ESP32 serial probe controlling an exciter and reading a piezo/analog sensor.

### Why the camera feature?

It maps normalized AI recommendations into a human-executable physical point on the panel without requiring a robot.

### Is the ESP32 safe to connect directly to a motor?

No. The exciter requires a driver and suitable external power; the analog input needs protection and biasing.

## Software questions

### Why FastAPI and React?

Python keeps simulation, inference, signal processing, and ML in one scientific stack. The browser provides portable visualization, camera/microphone permissions, and a judge-friendly interface.

### Does state survive a restart?

Yes. SQLite stores session and measurement state. The browser stores only the last session ID and can resume the authoritative backend record.

### What happens if hardware is absent?

Device discovery reports unavailable status, physical acquisition returns an explicit error, and simulation remains unaffected.

### How are uploads secured?

Size/type limits, in-memory WAV decoding, finite sample validation, no execution, and no use of the supplied filename as a filesystem path.

## Novelty and IP questions

### Is it patentable?

Unknown until professional claim-level analysis. The repository contains a disclosure and an initial adjacent-art map, not a legal conclusion.

### What is the strongest novelty thesis?

The posterior-conditioned sequential co-selection of actuator, receiver, and excitation parameters using counterfactual response separation plus physical cost/redundancy, followed by execution guidance and recursive fusion.

### What is already known?

Bayesian acoustic defect localization, optimal sensor placement, value-of-information sensor design, adaptive acoustic scanning, and active-learning inspection locations.

### What should never be said?

“World’s first,” “patentable,” “patent pending,” “mathematically optimal,” “field validated,” or “certified,” unless the corresponding evidence or legal event exists.

### What should be done before the hackathon?

Tell patent counsel the exact public presentation date, repository visibility, all contributors, and the disclosure document. If international rights matter, discuss filing before public disclosure.

## Business questions

### Who could use it?

Inspectors and manufacturers working with composite panels, bonded structures, wind blades, civil components, or enclosures where measurements are expensive and internal state is hidden.

### What is the economic promise?

Reduce low-value probing and guide the operator toward measurements predicted to change the decision or reduce uncertainty most.

### What becomes the moat?

Validated physical data, calibrated domain models, coupling/robotics expertise, workflow integration, reliability evidence, and modality-specific forward models.

### How does it scale beyond acoustics?

Replace acquisition, preprocessing, feature extraction, and response prediction while keeping the belief, candidate, cost, planner, persistence, and explanation contracts.

## Failure and limitation questions

### When can ARGUS fail?

Incorrect wave velocity, a bad baseline, unstable coupling, multiple defects under a single-defect model, out-of-plane modes, boundary reflections, excessive noise, or a candidate pool that cannot distinguish hypotheses.

### How should failure be detected?

Low information scores, persistently high entropy, inconsistent repeated measurements, posterior predictive checks, calibration residuals, and explicit out-of-distribution models in a future physical version.

### What is the next most credible experiment?

Use a healthy panel plus panels with known cavities, collect repeated calibrated chirp responses with a spring-loaded fixture, and compare adaptive and fixed probing at identical budgets while hiding truth from the planner.
