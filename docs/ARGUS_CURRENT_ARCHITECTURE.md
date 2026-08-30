# ARGUS current architecture — pre-NEO baseline

This document records the repository state audited on 2026-08-30 before the
ARGUS NEO upgrade. It is deliberately descriptive: it distinguishes behavior
verified in code and tests from behavior proposed for the next architecture.

## Baseline verification

- Backend entry point: `backend/run_backend.py` creates the FastAPI application
  in `backend/app/main.py` and starts Uvicorn on port 8000.
- Frontend entry point: `frontend/app/page.tsx`, built with React 19, Vinext and
  Vite and served locally on port 5173.
- One-command entry point: `python run_argus.py` starts both processes and
  terminates them together.
- Backend baseline: 19 tests passed.
- Frontend baseline: production build and ESLint passed. There was no frontend
  test script or component test suite.
- Runtime smoke test: health, session creation, one closed-loop experiment,
  posterior normalization and the frontend route all succeeded.
- Deterministic showcase (`easy`, seed 17): eight experiments, 0.403 normalized
  entropy, 0.732 reported confidence and 10.0 mm simulator-truth error. This is
  synthetic evidence, not physical validation.

## Runtime data flow

```text
ExperimentPlanner
    -> Experiment(source, receiver, band, amplitude, duration, waveform)
    -> acquisition adapter or AcousticSimulator
    -> signal preprocessing and features
    -> baseline-subtracted matched-filter likelihood on a 2-D grid
    -> recursive posterior multiplication and normalization
    -> persisted experiment plus next recommendation
    -> React scientific-instrument view
```

### Digital twin

`backend/app/simulation/physics.py` implements an interpretable lumped wave
model. It combines an attenuated direct response, a bistatic delayed scattered
response, defect-dependent reflection polarity, resonance/ringing,
environmental drift and seeded Gaussian noise. Coordinates are normalized at
the API boundary and converted to panel dimensions in metres. It is not an FEM
solver and has no learned or imported fidelity controller.

### Signal processing

`backend/app/signal/processing.py` performs DC removal, optional Butterworth
bandpass filtering, FFT distribution, Welch PSD, spectrogram, Hilbert envelope
features, robust noise estimation and an SNR proxy. Plot payloads are
downsampled for the browser.

### Posterior representation and update

`backend/app/inference/belief.py` stores one normalized `grid_size × grid_size`
array representing a single dominant defect location. The likelihood subtracts
the simulator baseline, matched-filters the residual against the excitation,
samples the correlation at every cell's predicted bistatic delay, smooths the
map and applies an SNR-dependent temperature. The posterior update is

```text
p_next(z) = normalize(p_current(z) * max(likelihood(z), epsilon)).
```

The estimate includes MAP and mean positions, covariance, local mass, Shannon
entropy and a heuristic confidence combining local mass with entropy. Radius,
severity, type, propagation, coupling, pose, timing and discrepancy are not
posterior variables.

### Planner algorithm

`backend/app/active_learning/planner.py` builds a deterministic bounded set of
candidate experiments from perimeter points and leading posterior cells across
three bands. For the top posterior hypotheses it predicts delay, log-gain and
circular phase signatures. Pairwise weighted separation supplies a bounded
counterfactual disagreement, which contributes to an approximate
information-gain proxy. The final baseline score is

```text
information + disagreement + coverage - energy/motion cost - repetition.
```

This is a one-step greedy planner. It has one objective, no explicit
calibration actions, no constraints/no-go regions, no waveform optimization,
no model-fidelity choice and no OOD-aware abstention.

### Acquisition adapters

`backend/app/hardware/devices.py` exposes a common acquisition boundary for the
seeded simulator, WAV uploads, a local microphone through `sounddevice`, and an
ESP32 serial protocol. Browser microphone capture is encoded as WAV in the
frontend. There is no smartphone-specific probe route, capability/heartbeat
protocol or second-laptop edge client.

### Persistence and schema

`backend/app/database/repository.py` owns a local SQLite file. The baseline
schema has:

- `sessions`: identity, timestamps, mode, preset and a JSON serialized runtime
  state;
- `experiments`: ordered parameters, feature payload, posterior before/after,
  likelihood, planner payload, diagnostics and compressed float32 signal.

Schema creation is idempotent but there is no migration-version table. Runtime
hydration recreates the engine from the saved state and therefore requires
backward-compatible dataclass/config fields. Experiment rows are immutable in
normal use but are not linked by cryptographic hashes.

### Existing API routes

| Method | Route | Baseline behavior |
|---|---|---|
| GET | `/health` | Readiness and version |
| POST/GET | `/sessions` | Create or list sessions |
| GET | `/sessions/{id}` | Public state; truth sealed until reveal |
| POST | `/sessions/{id}/calibrate` | Store nominal simulated reference summary |
| GET | `/sessions/{id}/recommendation` | Current greedy plan and top candidates |
| POST | `/sessions/{id}/experiments/run` | Run simulated recommended/custom action |
| POST | `/sessions/{id}/experiments/upload` | Validate and process WAV measurement |
| POST | `/sessions/{id}/experiments/device` | Acquire from local microphone/serial probe |
| GET | `/sessions/{id}/posterior` | Posterior grid and estimate |
| GET | `/sessions/{id}/history` | Persisted experiment records |
| POST | `/sessions/{id}/reveal` | Reveal simulation truth |
| GET/POST | `/devices*` | Discover, connect and disconnect devices |
| GET | `/benchmarks` | Saved or generated three-policy benchmark |

### Existing UI

The single instrument route contains session creation/resume, a posterior
heatmap, current experiment geometry, candidate audit, signal plots, belief
evolution, three-policy benchmark, truth reveal and camera corner-based
homography overlay. It is a coherent scientific-instrument UI and must be
extended rather than replaced.

## Limitations and technical debt found

1. Structural and metrology uncertainty are conflated; calibration does not
   update an inferred nuisance state.
2. A physical measurement is evaluated against the simulator's nominal
   baseline and material even when they are wrong.
3. Repeated correlated or low-quality observations can over-concentrate the
   posterior because evidence dependence is not discounted.
4. Planner explanation is prose derived from a small score record rather than
   a complete structured audit object.
5. Stop logic has only confidence, entropy and budget conditions.
6. No OOD, discrepancy, model-trust or abstention mechanism exists.
7. Benchmark policies are random, uniform and baseline ARGUS only; there are no
   ablations, paired tests beyond bootstrap intervals, calibration studies or
   failure explorer.
8. No background research jobs, cancellation, progress stream, deterministic
   forward cache, model registry, replay dataset abstraction or research
   bundle import/export exists.
9. SQLite initialization has no explicit versioned migration trail.
10. Frontend types mirror only the baseline state and there are no frontend
    automated tests.

## Migration requirements

- Preserve all existing routes and baseline JSON fields.
- Extend `Experiment` with defaulted fields so old serialized experiments load.
- Extend configuration with default values and filter unknown/missing fields
  during hydration.
- Store NEO state as an optional versioned sub-document; generate a default
  state when opening a legacy session.
- Add tables and columns only through idempotent numbered migrations. Never
  delete or rewrite the existing database during startup.
- Keep baseline planner behavior available as a named comparison policy.
- Preserve truth sealing: no planner, replay policy or public state may access
  hidden truth before evaluation/reveal.

