# ARGUS

**Adaptive Recursive Guided Uncertainty Sensing**

> AI that decides what physical experiment to perform next.

ARGUS is a local, closed-loop physical interrogation prototype for locating hidden defects in opaque panels. It generates or acquires a vibration response, maintains a Bayesian defect heatmap, predicts how leading hidden-state hypotheses would respond to possible future experiments, and recommends the source/receiver/waveform configuration expected to be most informative after physical cost and redundancy.

Ordinary defect AI answers “what does this recording contain?” ARGUS repeatedly asks “which recording should we create next?”

## What works

### Spatial observatory (11–12 October 2026)

The overview restores 3D as its default, prominent visualization, with drag
orbit, camera presets, zoom, measurement paths and physical uncertainty rings.
Switch to 2D for cell-level inspection and exclusion-zone drawing, or compare
both views together. Candidate route cards expose the geometry and actual
planner terms behind the next experiment. Linked cell inspection now highlights
the same location in both views, with exact row/column profiles and CSV export;
camera settings survive view switches. Read the
[visualization guide and verification limits](docs/VISUALIZATION_UPGRADE_2026_10_11.md).

The 3D surface now supports direct cell selection through **Inspect surface**,
with linked 2D/profile readouts and keyboard navigation. **Orbit camera** retains
the camera controls. The latest frontend checks passed 88 tests, type checking,
lint and a production build; connected-browser visual review remains pending.
The [12 October visual refinement](docs/VISUAL_AESTHETICS_2026_10_12.md) adds a
shared graphite/teal palette, clearer typography, rounded panels, framed
profiles, polished candidate cards and physical axis ticks in the 3D scene.
Startup verification now includes a real component hydration regression and an
explicit local-router check; see the [hydration diagnostics](docs/HYDRATION_DIAGNOSTICS_2026_10_12.md).

### Wave-packet imaging development (12 October 2026)

An offline experimental branch retains waveform arrival timing rather than
compressing the whole record into one discrepancy. It calibrates an effective
packet-delay model from healthy recordings and compares source-correlated
residual images with RAPID using the same recorded paths. The first measured
experiment qualified only two of six propagation models and did not improve
localization on their eligible cases. These are previously inspected measurements
from one specimen, not new confirmation or validation of the ARGUS apparatus.
The separate qualified-path revision improved directional 40 C mean error from
302.97 mm for RAPID to 63.31 mm on the same four cases, while isotropic 60 C
remained worse than RAPID. Each branch supports only four of twelve damage
conditions; the incomplete coverage and all negative results remain explicit.
Read the [wave-packet protocol](docs/WAVE_PACKET_IMAGING_PROTOCOL.md) and the
[development results](docs/WAVE_PACKET_DEVELOPMENT_RESULTS_2026_10_12.md).

For read-only development status and an explicit local checkpoint, use
`.venv\Scripts\python.exe scripts\dev_checkpoint.py`. The
[continuation guide](docs/DEVELOPMENT_CONTINUITY.md) records how to resume after
a session stops; it does not monitor account usage or schedule automatic resets.

### Instrument workspace and evidence laboratory (9 October 2026)

The instrument now has grouped workspace navigation, keyboard view search,
responsive controls, a persistent stop toolbar and a focused inspection overview.
Posterior review compares recorded before/after fields, probability changes,
entropy, physical mean shift and tied-cell mass regions, with CSV export.
The [Evidence laboratory](http://localhost:5173/research) includes interactive
measured-task comparisons and the completed 29-bank confirmation.

Request ownership prevents late responses from restoring an old session;
stop/release acknowledgments retain engine ordering, and successful acquisition
with an unavailable history refresh is reported as partial success. Deferred
views, error boundaries and visibility-aware polling improve operation.
Read [the workspace guide and validation](docs/WORKSPACE_UPGRADE_2026_10_09.md).

### Measured datasets and reference-conditioned fundamentals

Public measured data now support four task-specific evaluations: whole-plate
GFRP tap screening, Bologna transient source localization, native ultrasonic
path replay, and MORPHO signal-quality rejection. Read the
[measured results](docs/MEASURED_RESULTS_2026_10_08.md) and visit
[the local Research page](http://localhost:5173/research) for positive and negative findings.

New experimental modules fit healthy waveform drift, use measured source pitch
for clock alignment, qualify feasible paths, and calibrate complete adaptive
trajectories before issuing reference/verification/review requests. Their
[fundamental results](docs/FUNDAMENTAL_UPGRADE_RESULTS_2026_10_08.md) include
improved healthy reference prediction, worsened conditional localization and
withheld decisions when calibration is insufficient. The separate confirmation
completed on 9 October after temporary public-download HTTP 403 failures:
29 verified native banks supplied 19 healthy calibration blocks and ten test
banks. At 16 paths, adaptive conditional location errors were 161.20 mm for raw
references versus 206.49/215.39 mm for transported variants. All adaptive
variants raised no supported alerts on eight damage conditions, so zero false
alarms on two unique healthy banks does not establish a useful detector.
Limited early random-order alerts are retained separately. Cooling-block
correlation and one specimen prevent a field-coverage claim; these mechanisms
remain outside production physical acquisition. No signals were fabricated.

### Clock-referenced acquisition v2 and extended evidence

The classic ESP32 reference firmware now captures ADC34 during DAC25 excitation,
with pretrigger samples, GPIO26 onset marker, actual timestamps, recorded DAC
codes and a bounded experiment-bound frame. The host requires a chip-specific
operator timing/transfer record and checks the entire frame before ingestion.
Unaligned physical recordings are saved with zero inference weight; their sensor
names or metadata flags cannot bypass the time-origin gate.

Read [current project and evidence review](docs/PROBE_V2_RELEASE_REVIEW.md),
[apparatus and wire contract](docs/PROBE_V2_DESIGN.md), and
[claim-specific prior-art assessment](docs/PATENT_STRENGTHENING_ASSESSMENT.md).
The extended comparison includes cyclic, random, scaled A-optimal, scaled
D-optimal and task-conditioned reference selection. It evaluates synthetic
arrival prediction, separately from physical defect localization.

### Final technical method extension

The optional `enable_task_conditioned_calibration` setting selects direct-reference
geometry using the complete spatial posterior and correlated propagation covariance.
It minimizes expected downstream arrival variance plus declared reference cost.
Activate it with `python scripts/demo_simulation.py --task-calibration --preset easy --seed 17 --experiments 8`,
or the session API. The default stays off; the two-step physical-loss policy is
a separate method and takes precedence when enabled.

Read the [earlier method disclosure](docs/ARGUS_FINAL_TECHNICAL_DISCLOSURE.md) and
[earlier bounded evidence](docs/FINAL_PATENT_EVIDENCE.md) for the pre-v2 revision.
Legacy post-excitation firmware remains refused. Current v2 acquisition requires
the external operator evidence described above; wire version alone is insufficient.
An aligned external WAV can carry a bounded operator declaration through the API.

### Security and scientific release hardening (7 October 2026)

Localhost is now the default. Explicit `python run_argus.py --lan` enables
authenticated sharing with exact origins/hosts and a per-run access key. The
launcher prefers the project virtual environment; this workspace uses patched
PyTorch 2.6.0+cpu and Next.js 16.3.8. Phone microphone/camera capture requires a
trusted HTTPS context; a plain HTTP LAN page supports manual guidance only.

Security controls now run before device acquisition and before structural or
calibration updates. Original source bandwidth/window checks reject aliased and
incomplete recordings; sensor names cannot disable physical-reference gating.
Model persistence is pickle-free, artifact allocations are bounded, and source
identity includes the actual dirty/untracked working tree. Historical pickle
checkpoints are refused, and unchanged attribute priors are explicitly labelled.

Read [security and operation](docs/SECURITY.md), the
[dated release report](docs/RELEASE_READINESS_REPORT.md),
[publication evidence](docs/PUBLICATION_READINESS.md), and
[technical IP review package](docs/PATENT_REVIEW_PACKAGE.md). These are local
review materials, not field validation, a novelty conclusion, or a patent filing.

### Audit remediation (20 September 2026)

The controller now preserves velocity/timing correlation, uses different calibration
path lengths, checks OOD before structural fusion, and requires a fresh accepted
verification measurement before a confident stop. An optional **Calibration-aware
risk planning** mode branches over up to two future observations and compares
diagnosis and calibration in squared position-error units. It remains experimental;
improved mathematical accounting does not establish physical accuracy or novelty.

Evidence verification checks stored measurement content and can compare against an
independently retained checkpoint. Physical response-bank plans and metadata audits
are available through `scripts/physical_campaign.py`. Read the complete
[changes and unresolved restrictions](docs/AUDIT_REMEDIATION.md) and
[current technical disclosure](docs/CURRENT_INVENTION_DISCLOSURE.md).

The historical benchmark figures below describe their saved source versions, not
the changed controller. New paired results are in
`research_results/audit_risk_validation.json`. Do not mix versions in a superiority claim.

### Research and spatial-interface update

ARGUS now includes an opt-in **nuisance-aware arrival-time design** method,
an app-wide animated spatial environment, a live 3D posterior relief, physical
R90 geometry, and an in-app **Research** evidence report. Enable the experimental
method on the launch screen and inspect its calculation in **Reasoning**.

The paired study has 80 completed synthetic runs. Nominal mean localization
error is essentially tied (15.12 versus 15.10 mm); under mismatch/noise it is
180.14 versus 146.56 mm. Both paired uncertainty intervals include zero, and both
methods fail the 30 mm threshold in 17/20 stress cases. Therefore the new method
remains experimental, not a demonstrated accuracy or field-performance upgrade.
See [method and related work](docs/RESEARCH_CONTRIBUTION.md) and
[protocol, results and failures](docs/RESEARCH_EVALUATION.md).

Motion can be paused throughout the app; reduced-motion preferences are
respected. 3D relief depicts posterior probability, not actual defect depth.

### Existing capabilities

- Physics-inspired direct + defect-scattered wave simulation with delay, attenuation, resonance, material/domain randomization, and reproducible noise
- Easy, medium, and hard secret-defect judge modes
- Recursive normalized 2D posterior; MAP/mean estimate, physical containment radii, entropy, confidence, and termination rules
- Adaptive Physical Experiment Planner with counterfactual hypothesis disagreement, information-gain proxy, uncertainty coverage, energy/motion cost, and repetition penalty
- Random and uniform-grid baselines with actual JSON/CSV evaluation output
- DC removal, bandpass, waveform, FFT, PSD, spectrogram, envelope timing, decay, robust noise/SNR, and interpretable features
- FastAPI/OpenAPI, local SQLite sessions, compressed raw signals, complete history, upload validation, and structured logs
- Simulation, WAV, browser/local microphone, and ESP32 serial acquisition paths
- Scientific React/Vite instrument with candidate audit, signal analysis, belief evolution, benchmark view, reveal, and camera homography
- Optional domain-randomized PyTorch forward-response surrogate with early stopping and CPU/GPU support
- ESP32 firmware and safe wiring guidance
- Engineering disclosure requiring human inventorship, disclosure-date and professional prior-art review
- ARGUS NEO joint structural/metrology uncertainty with diagnostic, calibration, verification, and exploration actions
- Counterfactual signatures, finite waveform/geometry candidate selection, constraints and analytical/physics-signature selection; optional two-step squared-location-loss planning
- Online discrepancy correction, robust/conformal OOD detection, explicit abstention, and confidence caps
- SQLite research jobs for nine-policy benchmarks, seven ablations, calibration studies, response banks, demos, and CPU surrogate active learning
- Tamper-evident experiment ledger, verification, integrity-manifested research bundle export/import, model registry, and failure/fault tooling
- Zero-install phone probe and reconnecting Laptop-B acquisition node on a trusted local network

## Fast start

ARGUS officially targets Python 3.11+ and Node 22+. It was also verified in this workspace on Python 3.10.11.

After installing the backend and frontend dependencies once, the one-command launcher starts both services and stops both cleanly on `Ctrl+C`:

```powershell
.venv\Scripts\python.exe scripts\doctor.py
python run_argus.py
```

Then open `http://localhost:5173`. The API and OpenAPI documentation are at `http://localhost:8000` and `http://localhost:8000/docs`.
The API port is configurable with `ARGUS_API_PORT` or the local frontend
`NEXT_PUBLIC_ARGUS_API_PORT` setting used by the launcher. In this workspace ARGUS
uses port **8001** because another application owns 8000. The frontend checks the
service identity before reporting the engine online.
Use `python run_argus.py --lan` for explicit authenticated sharing. In that mode
the launcher prints `http://<LAN-IP>:5173/probe`, the Laptop-B API address and an
operator access key. Phone microphone/camera capture requires trusted HTTPS;
plain HTTP supports the manual interface.

### 1. Backend

```powershell
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r backend\requirements.txt
python backend\run_backend.py
```

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r backend/requirements.txt
python backend/run_backend.py
```

Backend: `http://localhost:8000`

OpenAPI: `http://localhost:8000/docs`

Or use `start_backend.bat` / `./start_backend.sh`.

### 2. Frontend

In a second terminal:

```powershell
cd frontend
npm install
npm run dev -- --hostname 127.0.0.1 --port 5173
```

Frontend: `http://localhost:5173`

Or use `start_frontend.bat` / `./start_frontend.sh`.

If the API runs elsewhere, copy `frontend/.env.example` to `frontend/.env.local` and change `NEXT_PUBLIC_ARGUS_API_URL`.

## No-browser simulation

```powershell
python scripts\demo_simulation.py --preset easy --seed 17 --experiments 8
```

That deterministic showcase localizes the committed secret defect, prints every chosen geometry and information score, reveals at the end, and reports millimetre error.

## Closed-loop mathematics

For hidden state `z`, measurement history `D`, and new experiment `e`:

```text
p(z | D, y, e) ∝ p(y | z, e) p(z | D)
```

The likelihood comes from matched-filtered residual energy at each candidate cell’s bistatic propagation delay. For planning, ARGUS predicts response signatures for top posterior hypotheses and scores how distinguishable they would be:

```text
score(e) = α · information_gain_proxy
         + β · counterfactual_disagreement
         + κ · uncertainty_coverage
         − γ · physical_cost
         − δ · repetition
```

This is a documented real-time approximation, not a claim of exact globally optimal Bayesian design. See [Active Experiment Design](docs/ACTIVE_EXPERIMENT_DESIGN.md).

## Actual benchmark

The saved `benchmark_results/benchmark.json` and CSV came from:

```powershell
python scripts\evaluate_model.py --cases 30 --preset medium --experiments 10 --seed 100 --output benchmark_results
```

| Strategy | Mean error | Final normalized entropy | Success ≤15 mm | Mean experiments | Mean cost |
|---|---:|---:|---:|---:|---:|
| Random | 13.38 mm | 0.498 | 56.7% | 10.00 | 2.66 |
| Uniform grid | 13.26 mm | 0.621 | 60.0% | 10.00 | 2.48 |
| ARGUS active | **12.33 mm** | **0.419** | **73.3%** | 9.83 | 2.59 |

On identical cases, ARGUS reduced final normalized entropy by 0.079 versus random (paired bootstrap 95% CI 0.063 to 0.095) and 0.202 versus uniform grid (0.180 to 0.224). Its mean localization error was lower, but those error-difference intervals cross zero, so this benchmark does **not** establish statistically significant error superiority. These results measure performance inside the declared simulator and do not establish real-world inspection accuracy.

## Generate data and train the learned surrogate

```powershell
python scripts\generate_dataset.py --samples 2500
python scripts\train_model.py --epochs 80 --patience 10
```

The dataset script varies geometry, material, noise, defect properties, and experiment parameters. The current `models/forward_surrogate.json` records 15,000 synthetic samples, validation loss 0.18470, test loss 0.19815, standardized MAE 0.45690 and mean feature R² 0.47567. These are response-feature metrics, not defect-localization accuracy. The older 3,000-sample result is historical. The live NEO planner currently uses analytical/physics-signature levels; its learned and imported higher-fidelity options are not yet integrated as validated live models.

## Public experimental training data

ARGUS includes checksum-verifying downloaders and adapters for KU Leuven LMSD, TU Darmstadt GFRP microphone data, and the University of Bologna paired simulated/experimental impact-localization data:

```powershell
python scripts\download_lmsd_dataset.py --profile all
python scripts\prepare_lmsd_dataset.py
python scripts\download_sim2real_datasets.py
python scripts\prepare_tud_gfrp_dataset.py
python scripts\fit_sim2real_models.py
python scripts\prepare_ae_impact_dataset.py
python scripts\benchmark_ae_sim2real.py
```

The TU adapter processed 2,568 measured taps from eight physical plates. Complete-plate-held-out evaluation achieved 0.775 balanced accuracy and 0.911 ROC-AUC for pointwise intact/defect screening. On the separate aluminium impact record, eight-position measured calibration reduced leave-one-position-out localization error from 0.175 m to 0.141 m; this is impact localization on one plate, not validation of persistent hidden-defect localization. The runtime now uses the GFRP reference as an additional OOD caution/abstention signal for uploaded or device-acquired physical waveforms while leaving simulation sessions unchanged.

Raw downloads, derived NPZ files, and generated estimator binaries remain local and Git-ignored. Reproducibility, citations, exact limitations, other public datasets, and the remaining physical campaign are in [Sim-to-Real Report](docs/SIM2REAL_REPORT.md) and [Real Training Data](docs/REAL_DATA_GUIDE.md).

## Calibration

```powershell
python scripts\calibrate.py
```

In the UI, **Run Reference** stores the session’s noise, velocity, resonance, and baseline response profile.

## ESP32 probe

1. Open `firmware/esp32/argus_probe.ino` in Arduino IDE using ESP32 Arduino core 2.x.
2. Wire the exciter through a transistor/MOSFET driver and the analog sensor through a protected, biased front end.
3. Flash and connect at 115200 baud.
4. Start ARGUS and inspect `GET /devices` or use the physical workspace.

Protocol commands include `PING`, `STATUS`, `EXCITE`, `READ`, `EXPERIMENT`, and `STOP`. Exact wiring and message format are in [Hardware](docs/HARDWARE.md) and [firmware notes](firmware/esp32/README.md).

## Real WAV and browser microphone

Create a **Physical** session, place source/receiver as recommended, then open Signal and upload a PCM WAV or use **Capture Microphone**. Uploads are limited to 10 MB, decoded in memory, converted to mono/16 kHz, and never executed or addressed by their supplied filename. Browser capture requires microphone permission.

## Test and verify

```powershell
python -m pytest backend\tests -q
python scripts\doctor.py
python scripts\demo_simulation.py --preset easy --seed 17 --experiments 8
python scripts\evaluate_model.py --cases 30 --preset medium --experiments 10 --seed 100
cd frontend
npm test
npm run lint
npm run build
```

ARGUS NEO research checks:

```powershell
python scripts\neo_calibration.py --quick
python scripts\neo_benchmark.py --cases 2 --max-experiments 5
python scripts\neo_benchmark.py --ablation --cases 2
python scripts\run_neo_demo.py rival_hypotheses --output research_results\rival.json
python scripts\run_neo_demo.py model_mismatch --output research_results\mismatch.json
python scripts\active_learn_surrogate.py --samples 240 --query-count 24
```

The **Research** tab runs these in a one-worker SQLite-backed queue. The **ARGUS Brain** tab explains uncertainty, rivalry, counterfactual responses, utility, fidelity, OOD, and alternatives. The **Evidence** tab verifies/exports the adaptive decision chain.

The backend suite covers simulation reproducibility, baseline/scatter physics, probability normalization, entropy, Bayesian update, signal preprocessing/features, candidate planning, repetition cost, API health, session lifecycle, persistence, and a multi-experiment integration loop.

## Repository map

```text
backend/app/
  active_learning/   candidate generation and counterfactual planner
  assurance/         healthy/unknown screening, channel reliability, drift and failure state
  database/          SQLite persistence
  evaluation/        random/grid/ARGUS benchmark
  hardware/          microphone, upload, serial adapters
  inference/         likelihood, posterior, entropy, estimates
  models/            domain types and PyTorch surrogate
  signal/            preprocessing, features, plot payloads
  simulation/        acoustic/vibration digital twin
  services/          closed-loop engine and sessions
frontend/
  app/                instrument route and design system
  components/         heatmap, signal, history, benchmark, camera
  hooks/ services/    API-backed session state
firmware/esp32/       reference physical probe
scripts/              demo, calibration, data, train, evaluate
docs/                 architecture, algorithms, demo, hardware, IP notes
```

## Demo and research docs

- [3-minute judge demo](docs/DEMO_GUIDE.md)
- [Complete project knowledge](docs/PROJECT_KNOWLEDGE.md)
- [Judge and technical Q&A](docs/JUDGE_QA.md)
- [Pitch brief](docs/HACKATHON_PITCH.md)
- [Architecture](docs/ARCHITECTURE.md)
- [ML pipeline](docs/ML_PIPELINE.md)
- [API](docs/API.md)
- [Preliminary adjacent art](docs/PRIOR_ART_NOTES.md)
- [Invention disclosure draft](docs/INVENTION_DISCLOSURE.md)
- [Pre-counsel patent specification and claim discussion set](docs/PATENT_DRAFT.md)
- [Verification report and success criteria](docs/VERIFICATION_REPORT.md)
- [Real training data and collection protocol](docs/REAL_DATA_GUIDE.md)
- [ARGUS NEO architecture](docs/ARGUS_NEO_ARCHITECTURE.md)
- [Scientific model](docs/SCIENTIFIC_MODEL.md)
- [Dual control](docs/DUAL_CONTROL.md)
- [Multi-fidelity digital twin](docs/MULTIFIDELITY.md)
- [OOD and abstention](docs/OOD_AND_ABSTENTION.md)
- [Benchmark protocol](docs/BENCHMARK_PROTOCOL.md)
- [Phone probe](docs/PHONE_PROBE.md)
- [Distributed demo](docs/DISTRIBUTED_DEMO.md)
- [Evidence ledger](docs/EVIDENCE_LEDGER.md)
- [Reproducibility](docs/REPRODUCIBILITY.md)
- [Limitations](docs/LIMITATIONS.md)
- [Technical disclosure notes](docs/PATENT_TECHNICAL_DISCLOSURE_NOTES.md)
- [ARGUS-X 1,331-problem disposition](docs/ARGUS_X_DISPOSITION.md)
- [Complete ARGUS-X coverage register](docs/ARGUS_X_PROBLEM_REGISTER.md)

## Limitations

- The current simulator is a physically inspired lumped wave model, not validated finite-element acoustics.
- The inference core still optimizes one dominant localized scatterer. ARGUS-X exposes separated candidate modes and defect-count screening, but does not claim a validated joint multi-defect inverse solution.
- Healthy/damaged/unknown probabilities and type/size/severity values are research-screening outputs; minimum detectable size and POD require a representative physical campaign.
- Physical inference needs a measured healthy baseline and coupling/calibration discipline; the provided path is not certified NDT.
- The planner’s expected-information value is an overlap proxy, not exact Monte Carlo mutual information.
- Text serial transfer is buffered and slower than real time.
- The optional learned surrogate is not shipped as a checkpoint; train it for the target domain.

## Highest-value next work

1. Collect paired healthy/defective panel data and fit hierarchical calibration/nuisance parameters.
2. Replace the information proxy with batched Monte Carlo expected posterior entropy and compare decisions.
3. Extend the latent state to multiple defects plus size/type/severity and perform calibrated posterior checks.
4. Integrate robot reachability and automatic probe positioning with repeatable coupling force.
5. Run a professional claim-level patent/freedom-to-operate search before any public disclosure.

## Research and IP note

This is a research prototype. Patentability requires professional prior-art analysis and legal review. The broad fields of Bayesian wave localization, adaptive acoustic scanning, active-learning inspection, and sensor placement have substantial prior art. The repository’s disclosure materials intentionally identify a narrower technical nucleus for counsel to evaluate without claiming novelty.

Before a hackathon or public repository release, discuss filing strategy with qualified counsel. Public disclosure can eliminate rights in many jurisdictions. Human inventorship must be determined from actual human conception and contribution; an AI tool is not named as an inventor.
