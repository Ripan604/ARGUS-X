# ARGUS NEO Implementation Report

Date: 30 August 2026  
Status: implemented, tested, locally runnable research prototype  
Safety status: not certified NDE/NDT equipment and not a sole basis for maintenance decisions

## 1. Outcome

ARGUS has been extended into ARGUS NEO (Next Experiment Optimization): a closed-loop scientific instrument that estimates a hidden structural anomaly, estimates uncertainty in the measuring process, decides whether to calibrate or diagnose, chooses the next safe source/receiver waveform, processes the response, updates belief, explains the decision, and stops, verifies, escalates, or abstains.

The implementation is end to end:

- FastAPI backend with additive SQLite persistence and legacy-compatible routes.
- Browser mission control, Argus Brain, signal diagnostics, belief timeline, benchmark lab, evidence ledger, and phone-probe application.
- Seeded physics simulator, microphone/WAV/serial paths, and a reconnecting laptop edge node.
- Joint structural/nuisance inference, dual control, counterfactual planning, Bayes risk, waveform co-design, multifidelity selection, online discrepancy, OOD gating, and decision-theoretic stopping.
- Resumable research jobs, calibration studies, paired benchmarks, ablations, blind demos, fault injection, replay, truth sealing, and integrity-checked evidence bundles.
- Detailed IEEE manuscript, compiled PDF, and upload-ready Overleaf ZIP.

## 2. Closed-loop operation

1. A session starts with a panel, material profile, acquisition device, execution profile, and uniform spatial prior.
2. The joint state tracks the structural posterior and approximate Gaussian/particle marginals for wave velocity, attenuation, timing, noise, gain, coupling, and probe pose.
3. The dual controller compares the value of reducing metrology uncertainty with the value of separating structural hypotheses. It chooses calibration, diagnostic, exploration, or verification.
4. The NEO planner forms feasible source/receiver candidates and expands them across bounded waveform families. No-go rectangles, frequency/amplitude/duration limits, source-receiver spacing, and unavailable actions are enforced before scoring.
5. Rival structural hypotheses are propagated through analytical or physics-signature forward models. Their candidate-specific predictive distributions provide average and worst-case separation.
6. A multiobjective score combines expected information, Bayes-risk reduction, calibration value, coverage, model trust, movement, energy, time, repetition, and short-horizon value.
7. The system acquires a simulated, uploaded, microphone, phone, serial, or edge response. Signal quality checks include silence, clipping, SNR, inertial deviation, visual-position error, and timestamp skew.
8. Evidence-weighted likelihood tempering prevents bad measurements from sharpening belief. Online discrepancy correction and robust/ensemble/conformal OOD indicators reduce model trust and cap decision confidence.
9. The stop controller checks confidence, entropy, credible area, Bayes risk, expected value of another measurement, OOD state, trust, and budget. It may continue, request verification/calibration, escalate, abstain, or end a research session.
10. The response, configuration, model identity, planner alternatives, rationale, posterior transition, human decision, and checksums are appended to a SHA-256-linked evidence ledger.

## 3. Implemented technical subsystems

| Subsystem | Implemented capability | Principal files |
|---|---|---|
| Joint inference | Structural grid, nuisance Gaussians, particles, uncertainty decomposition, calibration update | `backend/app/inference/` |
| Dual control | Calibration/diagnostic/exploration/verification switching with explicit values | `backend/app/control/dual_control.py` |
| Decision layer | Configurable decision loss, risk reduction, stopping and abstention | `backend/app/decision/` |
| Counterfactual planning | Candidate-specific distributions, hypothesis separation, multiobjective scoring | `backend/app/active_learning/counterfactual.py`, `neo_planner.py` |
| Co-design | Geometry plus impulse, sine, chirp, tone burst, Ricker, multisine, phase-coded, complementary-coded, and spectrally notched waveforms | `backend/app/active_learning/waveform_optimizer.py` |
| Horizon | Beam-limited receding-horizon reranking | `backend/app/active_learning/horizon.py` |
| Digital twin | Cached analytical/physics fidelities, controller, online ridge discrepancy | `backend/app/digital_twin/` |
| OOD | Robust residual, ensemble disagreement, and minimum-sample conformal tail | `backend/app/ood/` |
| Safety | Hard parameter constraints, no-go regions, unavailable-action rejection | `backend/app/safety/` |
| Evidence | Hash-linked ledger, ZIP export/import, manifest and checksum verification | `backend/app/evidence/` |
| Replay | NPZ/CSV/WAV banks, finite-action policy replay, hidden truth seal | `backend/app/replay/` |
| Research | SQLite jobs, recovery/cancel/progress, counterfactual banks, active surrogate, registry | `backend/app/research/`, `backend/app/models/registry.py` |
| Evaluation | Nine policies, ablations, calibration, blind scenarios, faults | `backend/app/evaluation/`, `backend/app/demo/` |
| Distributed probes | Phone PWA, camera/posterior overlay, inertial metadata, edge-node registration/heartbeat/poll/reconnect | `frontend/app/probe/`, `run_edge_node.py` |
| Interface | Mission control, Argus Brain, research lab, evidence ledger, no-go editor, replayable belief timeline | `frontend/` |

## 4. Scientific safeguards

- Ground truth is omitted from normal simulated-session payloads and replay truth remains sealed until stop/reveal.
- Silence and very low-quality observations cannot create strong evidence.
- Waveforms are peak-normalized after coding/modulation and checked against hard execution limits.
- OOD confidence gating applies to the confidence used by stopping, not only the displayed diagnostic.
- Conformal scoring is withheld until at least ten reference residuals exist.
- Empty feasible-action sets fail explicitly rather than selecting an unsafe action.
- Every demo result is labeled simulated unless it identifies a measured source.
- The software never labels itself certified equipment.

## 5. Data available now

The complete public KU Leuven LMSD 2021 plate dataset is already downloaded locally under `datasets/external/lmsd2021/`:

- DOI: `10.48804/GDE9TW`
- Zenodo record: `11033677`
- License: CC BY 4.0
- Local contents: healthy baseline, six known added-mass scenarios, metadata, position image, and license.
- Adapted output: `datasets/generated/lmsd_forward.npz` with a leakage-resistant scenario-held-out split.

This is valuable measured CFRP frequency-response data, but added masses are not literal cavities or delaminations and its fixed hammer/accelerometer grid is not a fully adaptive acquisition bank. It validates ingestion and exposes sim-to-real shift; it does not prove physical defect-localization performance.

A generated forward set and a two-scenario tiny counterfactual bank are also present under `datasets/generated/`. The active-learning study treats simulator targets as a sealed synthetic physics oracle until queried.

## 6. Physical data still required

For a publishable and commercially persuasive adaptive inspection study:

1. Use at least three nominally identical panels and independently characterize their ground truth.
2. Start with reversible masses, damping patches, or paired magnets; then manufacture flat-bottom holes or embedded release-film delaminations.
3. Use eight repeatably mounted perimeter transducers, an instrumented excitation chain, and healthy measurements before and after each damage block.
4. Record every admissible non-self source/receiver pair, at least three bands, and five repeats. With eight nodes this is `56 x 3 x 5 = 840` waveforms per physical state.
5. For 20 known locations plus healthy controls, target roughly 17,000 raw waveforms.
6. Store specimen/material/thickness, truth method, defect geometry, source/receiver coordinates, waveform, band, drive, coupling force, remount ID, temperature, humidity, calibration, timestamp, and code/model version.
7. Split by complete location for development, by complete specimen for validation, and keep a final panel blind until predictions and stopping decisions are frozen.
8. Record a complete counterfactual bank for offline fair policy comparison: every policy must query the same response table.
9. Report localization error versus budget, credible-region coverage, ECE, false confidence, abstention, measurement count, movement, energy, remount robustness, and temperature shift.

## 7. Observed results (do not overclaim)

### Earlier 30-case matched-model ARGUS baseline

- Final normalized entropy: ARGUS `0.419`, random `0.498`, grid `0.621`.
- Mean localization error: ARGUS `12.33 mm`, random `13.38 mm`, grid `13.26 mm`.
- Entropy improvement was consistent, but paired localization-error confidence intervals crossed zero. The defensible conclusion is stronger uncertainty concentration in this simulator, not proven localization superiority.

### New NEO checks

- Nine-policy quick matrix, `n=2`, five-measurement budget: no policy met the joint stopping criterion; all used five measurements; compression was `1.0x`. Full NEO mean error was `21.70 mm`, normalized entropy `0.909`, success `0.50`. This is a pipeline smoke test.
- Quick calibration, `n=4`: nominal 50/80/90/95% empirical coverages were all `1.0`, but ECE was `0.715`. This is poor calibration evidence with a tiny sample.
- Controlled seed-17 mismatch, one paired case: NEO ended at `14.65 mm`, trust `0.517`, and caution/OOD handling; a deliberately naive controller ended at `157.54 mm` with false confidence. This illustrates a mechanism, not a population effect.
- Active synthetic surrogate, `n=180`: MAE changed from `94.10` to `89.01` (5.41% reduction) against a synthetic physics oracle. This is not measured-data accuracy.

Machine-readable artifacts are under `research_results/`.

## 8. Verification completed

Commands and outcomes on 30 August 2026:

```text
python -m pytest -q
36 passed; one upstream Starlette test-client deprecation warning

cd frontend
npm test
3 passed
npm run lint
passed
npm run build
passed; / and /probe built

python scripts/doctor.py
ready: true; closed-loop, SQLite, dependencies, Node/npm and artifacts passed

pdflatex + bibtex + two pdflatex passes
11-page IEEE PDF; bibliography/cross-references resolved; no overfull boxes
```

All 11 PDF pages were rendered to PNG and visually checked for clipping, overlap, broken glyphs, table overflow, and bibliography flow.

## 9. Run and demonstrate

```powershell
python scripts\doctor.py
.\run_argus.ps1
```

The launcher prints:

- desktop UI URL,
- backend API/health URL,
- LAN phone URL for `/probe`, and
- the edge-node connection command.

For a deterministic research demo:

```powershell
python scripts\run_neo_demo.py rival_hypotheses
python scripts\run_neo_demo.py model_mismatch
python scripts\run_neo_demo.py measurement_compression --cases 4
```

For an edge laptop:

```powershell
python run_edge_node.py --help
```

## 10. Novelty position

The broad ingredients are not individually new: guided-wave inspection, Bayesian experimental design, dual control, digital twins, OOD detection, active learning, waveform design, and evidence ledgers all have prior art.

The strongest candidate technical nucleus is narrower: maintaining coupled structural and measurement-system uncertainty; choosing whether to calibrate the instrument or distinguish structural rivals; counterfactually co-designing a physically executable source/receiver waveform under discrepancy, OOD, loss, and safety constraints; then binding the observation, planner rationale, posterior transition, model identity, and human decision into a replayable integrity chain.

That combination appears specific, technically grounded, and claim-chartable, but this implementation report is not a patentability opinion. Novelty, inventive step/non-obviousness, eligible subject matter, ownership, disclosure timing, and freedom to operate require a professional search and jurisdiction-specific counsel.

## 11. Commercial readiness

Current stage: compelling research prototype and hackathon demonstrator, not a field-validated product.

Potential customers/partners include NDE service providers, aerospace/composites labs, wind-energy inspection groups, research instrumentation vendors, robotics/inspection integrators, and digital-twin platforms. They are more likely to fund a pilot or option/license than buy the IP outright before independent physical results.

The commercial evidence package still needed is:

- blind multi-specimen performance versus credible alternatives,
- calibrated failure/abstention behavior,
- repeatability under remounting and environmental change,
- time/cost savings at an agreed decision threshold,
- hardware safety and integration proof,
- a professional patent/claims/FTO analysis,
- clean contributor/data-license/IP ownership records, and
- two or three design-partner letters or paid pilot results.

## 12. Delivered artifacts

- `paper/main.tex` - detailed IEEE/Overleaf source.
- `paper/main.pdf` and `output/pdf/ARGUS_NEO_IEEE_Paper.pdf` - visually verified 11-page paper.
- `paper/argus-ieee-overleaf.zip` - upload-ready source archive.
- `docs/ARGUS_NEO_ARCHITECTURE.md` - system architecture.
- `docs/SCIENTIFIC_MODEL.md` - inference model and assumptions.
- `docs/DUAL_CONTROL.md`, `docs/MULTIFIDELITY.md`, `docs/OOD_AND_ABSTENTION.md` - core decision mechanisms.
- `docs/BENCHMARK_PROTOCOL.md`, `docs/REPRODUCIBILITY.md`, `docs/LIMITATIONS.md` - scientific evaluation boundary.
- `docs/PHONE_PROBE.md`, `docs/DISTRIBUTED_DEMO.md` - field demonstration instructions.
- `docs/EVIDENCE_LEDGER.md` - integrity and bundle workflow.
- `docs/PATENT_TECHNICAL_DISCLOSURE_NOTES.md` - invention-record drafting notes.
