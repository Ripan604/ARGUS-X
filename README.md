# ARGUS

**Adaptive Recursive Guided Uncertainty Sensing**

> AI that decides what physical experiment to perform next.

ARGUS is a local, closed-loop physical interrogation prototype for locating hidden defects in opaque panels. It generates or acquires a vibration response, maintains a Bayesian defect heatmap, predicts how leading hidden-state hypotheses would respond to possible future experiments, and recommends the source/receiver/waveform configuration expected to be most informative after physical cost and redundancy.

Ordinary defect AI answers “what does this recording contain?” ARGUS repeatedly asks “which recording should we create next?”

## What works

- Physics-inspired direct + defect-scattered wave simulation with delay, attenuation, resonance, material/domain randomization, and reproducible noise
- Easy, medium, and hard secret-defect judge modes
- Recursive normalized 2D posterior; MAP/mean estimate, covariance ellipse, entropy, confidence, and termination rules
- Adaptive Physical Experiment Planner with counterfactual hypothesis disagreement, information-gain proxy, uncertainty coverage, energy/motion cost, and repetition penalty
- Random and uniform-grid baselines with actual JSON/CSV evaluation output
- DC removal, bandpass, waveform, FFT, PSD, spectrogram, envelope timing, decay, robust noise/SNR, and interpretable features
- FastAPI/OpenAPI, local SQLite sessions, compressed raw signals, complete history, upload validation, and structured logs
- Simulation, WAV, browser/local microphone, and ESP32 serial acquisition paths
- Scientific React/Vite instrument with candidate audit, signal analysis, belief evolution, benchmark view, reveal, and camera homography
- Optional domain-randomized PyTorch forward-response surrogate with early stopping and CPU/GPU support
- ESP32 firmware and safe wiring guidance
- Patent-counsel-ready engineering disclosure and preliminary adjacent-art notes
- ARGUS NEO joint structural/metrology uncertainty with diagnostic, calibration, verification, and exploration actions
- Counterfactual hypothesis distributions, Bayes-risk objectives, waveform/geometry co-design, horizon planning, constraints, and adaptive model fidelity
- Online discrepancy correction, robust/conformal OOD detection, explicit abstention, and confidence caps
- SQLite research jobs for nine-policy benchmarks, seven ablations, calibration studies, response banks, demos, and CPU surrogate active learning
- Tamper-evident experiment ledger, verification, integrity-manifested research bundle export/import, model registry, and failure/fault tooling
- Zero-install phone probe and reconnecting Laptop-B acquisition node on a trusted local network

## Fast start

ARGUS officially targets Python 3.11+ and Node 22+. It was also verified in this workspace on Python 3.10.11.

After installing the backend and frontend dependencies once, the one-command launcher starts both services and stops both cleanly on `Ctrl+C`:

```powershell
python scripts\doctor.py
.\run_argus.ps1
```

Then open `http://localhost:5173`. The API and OpenAPI documentation are at `http://localhost:8000` and `http://localhost:8000/docs`.
The launcher also prints `http://<LAN-IP>:5173/probe` for a phone and the Laptop-B API address.

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

The dataset script varies geometry, material, noise, defect properties, and experiment parameters. The trained MLP predicts signal features for candidate physical states/experiments. A 3,000-sample CPU training run in this workspace early-stopped at epoch 27 with standardized Smooth L1 validation loss 0.2108, test loss 0.2245, standardized MAE 0.5014, and mean per-feature R² 0.409. Per-feature metrics—including strong SNR/RMS prediction and weak dominant-frequency/envelope timing prediction—are preserved transparently in `models/forward_surrogate.json`. Physics inference remains the safe default when no checkpoint exists.

## Public experimental training data

ARGUS includes a downloader and adapter for KU Leuven's CC BY 4.0 LMSD CFRP plate dataset. The complete checksum-verified local copy contains a healthy baseline plus six known added-mass damage scenarios. It converts to 294 measured source/receiver examples:

```powershell
python scripts\download_lmsd_dataset.py --profile all
python scripts\prepare_lmsd_dataset.py
```

The raw 171 MB download and derived NPZ remain local and Git-ignored; citation, license, limitations, other public datasets, and an exact laboratory collection protocol are in [Real Training Data](docs/REAL_DATA_GUIDE.md).

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
