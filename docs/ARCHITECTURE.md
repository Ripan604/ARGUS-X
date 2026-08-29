# ARGUS architecture

ARGUS is a closed-loop physical inference system, not a sound classifier.

```text
candidate experiments ──> counterfactual forward predictions ──> scored recommendation
        ^                                                               │
        │                                                               v
posterior belief <── Bayesian likelihood <── signal features <── physical/simulated response
```

## Runtime layers

1. **Digital twin** — `AcousticSimulator` generates a direct plate wave, a path-delayed defect scatter, damped resonance, attenuation, and sensor noise. Coordinates are normalized in the API but all propagation distances are computed in physical metres.
2. **Signal Interpretation Engine** — DC removal, bandpass filtering, windowing, FFT/PSD/spectrogram, envelope, noise estimation, and a compact feature set.
3. **Posterior Belief Engine** — subtracts the calibrated baseline, matched-filters the residual against the excitation, maps candidate defect cells to source–defect–receiver time of flight, forms a likelihood, and multiplies it into the existing posterior.
4. **Adaptive Physical Experiment Planner** — predicts response signatures for the leading posterior hypotheses, estimates how distinguishable those hypotheses would be under each candidate, adds uncertainty coverage, and subtracts energy, motion, and repetition costs.
5. **Acquisition adapters** — simulation, WAV/browser microphone, local microphone, and serial probe inputs expose one conceptual `acquire()` boundary.
6. **Session/API layer** — FastAPI and SQLite persist sessions, raw signals, planner state, features, and every posterior transition.
7. **Instrument UI** — React/Vinext/Vite renders the object field, acquisition recommendation, planner audit, signal anatomy, history, benchmarks, ground-truth reveal, and camera homography.

## Extensibility

A new sensor modality should implement acquisition, preprocessing, feature extraction, and response prediction without changing the posterior/planner contract. A new actuator contributes executable experiment parameters. This makes thermal, RF, electrical-impedance, optical, or robotic tactile experiments possible future modalities without turning the prototype into microservices.

## Persistence and privacy

SQLite is local. Raw signals are compressed float32 blobs; no paid service or cloud account is required. Ground truth is stored server-side and omitted from public session state until reveal.
