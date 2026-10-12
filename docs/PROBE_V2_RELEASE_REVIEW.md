# ARGUS acquisition v2: project explanation and evidence review

**Date:** 7 October 2026. This review describes the current apparatus code and
software, while keeping older evidence attached to its original source revision.
It is a detailed project briefing and a local technical-review package.

## The project in one explanation

ARGUS means Adaptive Recursive Guided Uncertainty Sensing. It is a research
prototype that chooses the next acoustic experiment on a rectangular panel.
Instead of analysing a single fixed recording, it repeats a loop: select a
source/receiver position and excitation, acquire the response, check whether the
measurement is usable, update a location probability map, and choose another
measurement. It can request a propagation reference, a diagnostic measurement,
or a fresh verification, and can abstain when the model or measurement is unsupported.

The practical idea is useful when measurement positions and budgets are limited.
Different paths provide different constraints on a possible scatterer. The
implemented demonstration assumes one dominant scatterer on a known panel.
Its map is conditional on that modelling assumption; it does not establish that
a defect exists or infer a reliable defect type, depth, size, or severity.

## Technology and responsibility of each part

| Part | Technology | Responsibility |
|---|---|---|
| Operator interface | Next.js, React, TypeScript | Heatmap, signal plots, recommendations, research evidence, acquisition setup and human controls |
| API and sessions | Python, FastAPI, Pydantic, WebSockets | Bounded requests, synchronized session/device operations, state and event delivery |
| Scientific computation | NumPy, SciPy | Waveform generation, resampling, matched filtering, probability updates, covariance conditioning and candidate scoring |
| State and evidence | SQLite, compressed signals, SHA-256 ledger | Persistent history and detection of changed recorded content against a retained checkpoint |
| Optional models | PyTorch, pickle-free checkpoints | Research surrogate workflow; it is separate from claims of validated live physical inference |
| Apparatus reference | Classic ESP32, Arduino C++, DAC25, ADC34, GPIO26 | Concurrent source/receiver recording with explicit sample times and an external trigger marker |

The default server is local to the laptop. An explicit LAN mode uses an operator
access key and exact permitted hosts/origins. Hardware execution has per-device
locks, session locks, an emergency latch and experiment constraints. These
software controls are not an independent physical power cutoff.

## Physics behind the observation

A vibration source excites the panel. Elastic motion propagates along the panel;
a receiver measures the response. A boundary or anomaly can scatter, attenuate
or alter the motion. Real panels can be dispersive, anisotropic and multimodal,
and coupling or temperature can change the signal without damage. ARGUS uses a
compact path-delay model to study the control loop, rather than solving the
elastic wave equation or a high-fidelity Lamb-wave finite-element model.

For a source S, receiver R and location hypothesis z:

```text
direct path d = distance(S, R)
scatter path ell(z) = distance(S, z) + distance(z, R)
direct arrival = timing_offset + d / effective_speed
scatter arrival = timing_offset + ell(z) / effective_speed
```

Distances use physical panel dimensions, not the normalized interface coordinates.
The simulator combines delayed direct and scattered excitations, attenuation,
frequency-sensitive gain and damped ringing. Its illustrative 180 m/s effective
speed is a simulation parameter, not a certified material constant.

Matched filtering correlates the recording with a declared reference excitation
to obtain a delay-related response. The structural likelihood compares these
responses across location hypotheses. This requires a known excitation time
origin: an arbitrary microphone file does not reveal when the source began.
Resampling can change the computational sample rate but cannot recover missing
early arrivals or reverse aliasing in the original recording.

At 16 kHz, nominal sample spacing is 62.5 microseconds. At an illustrative
180 m/s, one interval corresponds to 11.25 mm of propagation distance. This is
not a localization-resolution guarantee: geometry, multiple paths, noise,
dispersion, bandwidth and clock uncertainty also determine identifiability.

## How inference and planning work

The location map is a normalized two-dimensional grid. For accepted structural
evidence, the runtime combines the prior with a tempered likelihood and normalizes
the result. Tempering limits how aggressively an approximate signal model can
concentrate the map. Entropy, local probability mass, MAP position and a physical
containment radius describe that map; these are not certified correctness probabilities.

Separate metrology variables represent propagation speed, electronics timing,
noise and coupling proxies. Speed and timing retain a correlated 2 by 2 covariance.
Other variables remain approximate marginal blocks. The implementation therefore
does not claim a fully joint posterior over every structural and instrument variable.

The default controller ranks a finite candidate bank using labelled heuristic
information, discrimination, movement, energy, redundancy and trust terms. An
optional finite-horizon controller branches on at most two scalar arrival
observations and compares calibration and diagnosis under a declared loss.
An additional optional fast selector chooses the direct reference most relevant
to the nominated next diagnostic geometry. It stays off by default and can be
enabled through the session API or `--task-calibration` in the demonstration CLI.

## Task-conditioned reference mathematics

A reference measurement observes `y = b + d/v + noise`, where b is timing offset
and v is effective speed. One path provides one constraint on two unknowns.
Repeated short paths can leave uncertainty in predictions for longer paths even
when one parameter becomes precise.

The selector uses every cell of the location grid. It computes a weighted target
arrival sensitivity matrix W, predicts the speed/timing covariance after each
feasible reference and ranks the resulting diagnostic prediction variance plus cost:

```text
g(z) = [-ell(z)/v^2, 1]
W = sum_z probability(z) * transpose(g(z)) * g(z)
h(d) = [-d/v^2, 1]
K = C * transpose(h) / (h*C*transpose(h) + R/q)
C_after = (I-K*h)*C*transpose(I-K*h) + K*(R/q)*transpose(K)
objective = v^2 * trace(W*C_after) + declared_acquisition_cost_m2
```

The covariance update is established Gaussian conditioning in Joseph form.
Prediction variance is a standard experimental-design objective. The candidate
technical contribution is the specific acoustic apparatus/control interaction,
not a new Bayesian principle or a new general optimal-design formula.
The objective is path-equivalent propagation uncertainty; it is not predicted
defect-position error. Declared cost conversion and assumed quality are research
preferences rather than measured monetary loss or actuator energy.

## What changed in acquisition v2

The earlier firmware excited the panel and only then began ADC capture. It could
miss the early response and lacked a verified excitation-relative time origin.
The v2 reference firmware precomputes a quantized chirp or tone burst, captures
16 pretrigger samples, drives DAC25 while reading ADC34, and records each sample's
elapsed time and commanded DAC code. GPIO26 marks source onset for an external
oscilloscope. Timing deadlines use the declared rate instead of labelling a
truncated 62-microsecond interval as exactly 16 kHz.

The bounded frame contains a fresh request identifier, complete experiment hash,
original sample count/rate, drive family, exact frequencies/amplitude/window,
trigger position, drive interval, ordered ADC samples and timestamps, DAC codes,
checksum and completion/overrun status. The host checks all of these before any
samples can enter inference. Wrong, incomplete, stale, late, unsupported or
checksum-inconsistent frames revoke the connection's acquisition permission.

An operator record binds a specific chip identifier, sampling rate and drive
family to an external timing/transfer report digest. Its age and declared error
bounds are checked. This is an operator attestation; a JSON record and a hash do
not prove that bench measurements occurred. The 90-day age bound and error limits
are explicit project policies, not a metrology certification standard.

The classic ESP32 DAC adapter supports chirp and equal-endpoint sine/tone burst,
100 Hz through min(6000 Hz, 0.40 times the source sampling rate), amplitude at most
0.60, windows from 20 to 250 ms, and at most 4096 total samples. Coded waveforms
and other simulated families are rejected before excitation. DAC codes describe
commanded voltage; they do not measure pressure, amplifier power or panel motion.

## Physical evidence gate and persistence

The ingestion service supplies a timing assessment to inference through a
server-only argument. A client cannot obtain host-checked status by setting a
sensor name or a similarly named metadata flag. Missing timing/adapter support
keeps the signal available for plots and history but assigns zero structural
evidence and blocks calibration, nuisance updates and verification.

The public WAV upload endpoint additionally accepts a bounded optional
`sensor_metadata_json` form field. An exact trigger-aligned declaration binds the
complete experiment, source rate, zero trimmed trigger index, external report,
operator, date, clock/alignment bounds and validated arrival adapter. It is labelled
operator-declared, separately from a checked serial frame. Ordinary browser/phone
and WAV recordings without this support remain diagnostic-only recordings.

Original serial ADC values, sample times, DAC codes and declaration metadata are
stored in diagnostics before the evidence ledger is appended. Tests demonstrate
that changing the retained declaration makes integrity verification fail.
Checksums and the ledger detect inconsistent content; they do not authenticate
the sensor or prevent a privileged operator from replacing an entire history
without an independently retained checkpoint.

## What to say in Review 1

"ARGUS chooses the next acoustic experiment from the current location map and
instrument uncertainty. It can select a propagation reference before diagnosis.
The new probe records during excitation, retains actual timing and drive metadata,
and blocks unsupported physical recordings before they influence the map. We have
software and synthetic-model evidence; physical localization and patent novelty
still require independent validation."

If asked why calibration matters, explain that speed and electronics delay can
both shift an arrival. Different reference lengths constrain that ambiguity.
If asked why a high confidence value is insufficient, explain that a concentrated
map can still be wrong under model mismatch. If asked what is new, identify the
specific integrated apparatus/control sequence and acknowledge established
matched filtering, Bayesian inference and optimal experimental design.

## Running and reproducing the project

```powershell
.venv\Scripts\python.exe run_argus.py
.venv\Scripts\python.exe -m pytest backend\tests -q -o addopts=""
.venv\Scripts\python.exe scripts\run_frontend_release_checks.py
powershell -ExecutionPolicy Bypass -File firmware/esp32/tests/run_host_tests.ps1
.venv\Scripts\python.exe scripts\validate_reference_design_extended.py
```

The interface runs at `http://localhost:5173`. Select a simulation session for a
fully runnable demonstration without apparatus. A physical session needs an actual
characterized source/receiver setup; importing an invented calibration declaration
would undermine the evidence. The serial inventory during this review found no
connected serial device. No flashing or physical excitation was performed.

The following dated verification and extended-study results are generated from
saved check artifacts. They must be rechecked against source hashes after changes.

## Dated verification and extended comparison

The full backend suite passed 470 tests, with 1 intentionally skipped legacy-pickle checkpoint test. A nonfatal framework deprecation warning remains. All 30 frontend tests, TypeScript checking, lint and production build passed.

The extended study used 48 independent seed clusters, four fixed diagnostic geometries, two prespecified noise regimes, five reference policies and three opportunities each. Sealed truth/noise were never supplied to selection. The A/D baselines use dimensionless covariance scales and the same declared cost conversion; cyclic/random are charged the same costs.

All 1,920 attempted runs remain in the means and paired contrasts. 1,909 completed without a rejected opportunity; 11 reference-update opportunities were rejected. The failed runs consume their budget and retain the current state. Source hashes were unchanged during the run and match the current backend.

| Regime / reference policy | Arrival RMSE (microseconds) | Latent 95% interval coverage | Completed / attempted |
|---|---|---|---|
| nominal prior noise / cyclic | 229.82 | 93.11% | 192 / 192 |
| nominal prior noise / random | 232.30 | 94.96% | 192 / 192 |
| nominal prior noise / scaled a optimal | 200.23 | 92.13% | 192 / 192 |
| nominal prior noise / scaled d optimal | 190.85 | 91.72% | 192 / 192 |
| nominal prior noise / task conditioned | 189.09 | 91.83% | 192 / 192 |
| double acquisition noise / cyclic | 419.26 | 71.25% | 191 / 192 |
| double acquisition noise / random | 396.96 | 69.17% | 191 / 192 |
| double acquisition noise / scaled a optimal | 363.06 | 65.86% | 189 / 192 |
| double acquisition noise / scaled d optimal | 342.63 | 67.41% | 189 / 192 |
| double acquisition noise / task conditioned | 343.47 | 66.19% | 189 / 192 |

Pooled paired advantages are comparator minus task RMSE: positive favours task selection. Intervals resample the 48 seed clusters, preserving within-seed geometry/regime dependence. They are exploratory 95% intervals without multiplicity correction.

| Comparator | Mean task advantage (microseconds) | Seed-cluster 95% interval | Interpretation |
|---|---|---|---|
| cyclic | 58.26 | [35.13, 82.52] | Interval above zero in this model |
| random | 48.35 | [26.69, 70.91] | Interval above zero in this model |
| scaled a optimal | 15.37 | [4.79, 26.57] | Interval above zero in this model |
| scaled d optimal | 0.46 | [-5.70, 6.90] | Inconclusive difference |

The D-optimal comparison is inconclusive for both pooled arrival RMSE and prediction-plus-cost. Task RMSE is slightly worse than D-optimal under doubled noise. No general superiority claim is supported. Under nominal noise, task selection improves arrival prediction while worsening timing-offset parameter error (186.23 versus 168.23 microseconds for cyclic). These different outcomes must not be conflated.

Task latent-arrival interval coverage is 91.83% under nominal noise and 66.19% under doubled noise. These first-order parameter intervals do not achieve nominal 95% coverage in the study and do not certify physical defect confidence. The rejection reason retained by the study is: Direct-path observation is outside propagation-model support (11 opportunities).

The earlier 192-run scalar study and 48-run waveform localization study remain historical, source-bound evidence. This larger scalar study does not replace the need for measured waveforms, independent defect truth or a blind physical campaign.

## What remains before stronger publication and patent claims

The code and disclosure can now undergo a substantive technical review. A measured timing/transfer bench and blind specimen-held-out adaptive inspection are still missing. The apparatus compilation status is stated in PROBE_V2_DESIGN.md. Real inventors, ownership, conception records and earlier public disclosures need confirmation. Claim-specific novelty and inventive-step analysis remains open against close active-calibration and acoustic-reference prior art.

No justified 10/10 publication readiness or 6/10 grant probability follows from the implemented changes. Patent application publication is a filing procedure, whereas substantive grant depends on examination. A manuscript publication also depends on the venue and its reviewers. The package is locally prepared; it has not been filed or published.

