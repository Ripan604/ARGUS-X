# ARGUS verification report

**Last verified:** 5 September 2026
**Workspace:** Windows, Python 3.10.11, Node 24.14.1, npm, CPU PyTorch 2.5.1  
**Target:** local operation without Docker, cloud services, or a mandatory learned checkpoint

This report records commands actually executed in the delivered workspace. It is not a prediction that the code should work.

## Acceptance run

| Check | Command or action | Result |
|---|---|---|
| Readiness | `python scripts\doctor.py` | Ready; scientific imports, SQLite, Node/npm, frontend dependencies, benchmark artifact, and one closed-loop experiment passed |
| Backend | `python -m pytest backend/tests -q` | 71 passed; one upstream deprecation warning |
| Frontend tests | `cd frontend; npm test` | 12 passed |
| Frontend lint | `cd frontend; npm run lint` | Passed, zero errors |
| Frontend type check | `cd frontend; npm run typecheck` | Passed, zero errors |
| Production compile | `cd frontend; npm run build` | Passed; client, server, RSC, and SSR environments built |
| Python dependency integrity | `python -m pip check` | No broken requirements |
| Production dependency audit | `cd frontend; npm audit --omit=dev --audit-level=high` | 0 vulnerabilities |
| Judge demo | `python scripts\demo_simulation.py --preset easy --seed 17 --experiments 8` | Stopped at the eight-action budget; 10.0 mm error; 53.3% entropy reduction |
| Paired benchmark | `python scripts\evaluate_model.py --cases 30 --preset medium --experiments 10 --seed 100 --output benchmark_results` | Completed 90 policy runs and wrote JSON/CSV |
| Learned surrogate | 15,000 generated samples; `python scripts\train_model.py --data datasets/generated/argus_forward_15000.npz --epochs 200 --batch-size 256 --patience 25 --seed 23` | Early stopped at epoch 46; checkpoint and held-out metrics saved |
| Independent surrogate comparison | 3,000 fresh simulator cases, seed 104729; `python scripts\evaluate_surrogate_checkpoints.py ...` | Mean feature R² increased from 0.407 to 0.461 and standardized MAE fell from 0.468 to 0.437 versus the original checkpoint |
| Public experimental data | `python scripts\download_lmsd_dataset.py --profile all` | Healthy baseline and six damage NPZ files downloaded; all published MD5 values verified |
| Experimental adapter | `python scripts\prepare_lmsd_dataset.py` | 294 finite examples from 6 scenarios and all 7×7 source/receiver paths |
| Sim-to-real downloads | `python scripts\download_sim2real_datasets.py` | TU GFRP and Bologna impact records downloaded; every selected file passed publisher MD5 verification |
| GFRP adapter | `python scripts\prepare_tud_gfrp_dataset.py` | 2,568 measured microphone taps from 8 plates; 468 defect and 2,100 intact |
| GFRP held-out benchmark | `python scripts\fit_sim2real_models.py` | Complete-plate-held-out balanced accuracy 0.775, ROC-AUC 0.911, average precision 0.699 |
| Paired impact transfer | `python scripts\prepare_ae_impact_dataset.py`; `python scripts\benchmark_ae_sim2real.py` | 1,000 simulated paths plus 27 measured channels; measured few-shot calibration reduced LOPO mean error 0.175 m to 0.141 m |
| Physical-reference smoke | Process one publisher waveform and one deliberately alien 6.9 kHz tone through `ArgusEngine` | Publisher waveform reference score 0.0/NOMINAL; alien tone score 1.0/ABSTAIN |
| Unified startup | `python run_argus.py` | Both services started; frontend HTTP 200 and API health `ok` |
| Live API loop | create session, then run recommended experiment over HTTP | Initial entropy 1.0; one experiment stored; 20×20 normalized posterior and waveform returned |
| Unified shutdown | `Ctrl+C` | Launcher reported clean shutdown; no listeners remained on ports 5173 or 8000 |

The only test warning is an upstream Starlette notice that its `TestClient` compatibility import will eventually move from `httpx` to `httpx2`; it does not affect runtime behavior or test correctness.

### Physical posterior containment display

Mission Control now replaces the ambiguous headline confidence percentage with adjustable posterior mass inside 10, 15, 20, 25, or 50 mm of the MAP estimate. It also reports CEP50 (the MAP-centered radius containing 50% of discrete posterior mass) and R90. These quantities use physical panel dimensions and posterior grid-cell centers. They are explicitly labeled as model-based posterior containment, not field-calibrated coverage. In the deterministic eight-action easy run, the display reported 31.0% mass within 25 mm, CEP50 36.1 mm, and R90 72.1 mm; the subsequently revealed simulator error was 10.0 mm.

### ARGUS NEO tail-risk regression

After correcting structural-identifiability weighting in discrepancy and OOD attribution, the full ARGUS NEO policy was rerun on 30 previously unused medium-preset seeds (1000 through 1029), with eight total actions per sealed case. Mean localization error was 10.35 mm, median 9.58 mm, 90th percentile 16.73 mm, and maximum 20.10 mm; all 30 cases were within 25 mm. This is a deterministic simulator regression, not a field-accuracy claim. The deliberately mismatched-material scenario still selected one calibration action and produced 10.01 mm error versus 76.67 mm for the no-calibration/no-OOD ablation under that scenario.

## Measured simulator benchmark

Thirty identical seeded medium defects were evaluated under every policy with a maximum of ten experiments.

| Policy | Mean error | Final entropy | Success ≤15 mm | Experiments | Cost |
|---|---:|---:|---:|---:|---:|
| Random | 13.38 mm | 0.498 | 56.7% | 10.00 | 2.66 |
| Uniform grid | 13.26 mm | 0.621 | 60.0% | 10.00 | 2.48 |
| ARGUS | 12.33 mm | 0.419 | 73.3% | 9.83 | 2.59 |

Paired ARGUS entropy advantages are 0.079 over random (bootstrap 95% CI 0.063 to 0.095; 93.3% strict win rate) and 0.202 over uniform grid (0.180 to 0.224; 100% strict win rate). Mean error differences favor ARGUS by 1.05 mm and 0.93 mm, but both 95% intervals cross zero. The defensible conclusion is strong simulated uncertainty reduction and improved 15 mm success—not proven field accuracy or statistically established error superiority.

Raw evidence is in `benchmark_results/benchmark.json` and `benchmark_results/benchmark.csv`, including every run, seeds, trajectories, stopping reasons, paired comparisons, and intervals.

## Learned surrogate evidence

The included 59 KB PyTorch checkpoint was retrained on 15,000 domain-randomized simulator examples with a seeded 70/15/15 split. It achieved standardized Smooth L1 validation loss 0.1847, test loss 0.1982, standardized MAE 0.4569, and mean per-feature R² 0.476 on its internal holdout. SNR (0.926), RMS (0.922), and peak amplitude (0.905) were strongest; dominant frequency (0.085) and envelope timing (0.040) remain honest limitations. Full per-feature values and preprocessing metadata are in `models/forward_surrogate.json`.

The replacement was accepted only after both old and new checkpoints were evaluated on the same independent 3,000-case simulator set generated with seed 104729. On that untouched set, mean feature R² increased from 0.407 to 0.461 (13.2% relative), while standardized MAE decreased from 0.468 to 0.437 (6.6%). The fixed comparison and per-feature results are saved in `research_results/surrogate_external_benchmark.json`. These are simulator-domain response-prediction metrics, not physical-panel localization accuracy.

The checkpoint is optional. Core inference deliberately remains physics-based, so a fresh environment still works if the checkpoint is deleted.

## Original 20 completion criteria

| # | Criterion | Evidence | Status |
|---:|---|---|:---:|
| 1 | Backend starts without Docker | `backend/run_backend.py`, unified launcher, live `/health` | Pass |
| 2 | Frontend starts without Docker | `frontend/package.json`, unified launcher, live HTTP 200 | Pass |
| 3 | Simulation session can be created | `POST /sessions`, API lifecycle test | Pass |
| 4 | Secret defect can be generated | seeded `random_defect`; truth withheld until reveal | Pass |
| 5 | Initial uniform posterior displayed | 20×20 heatmap; live initial entropy ≈1 | Pass |
| 6 | ARGUS recommends a real next experiment | planner returns source, receiver, band, waveform, score, and rationale | Pass |
| 7 | Experiment generates a signal | functional `SimulationDevice`; integration tests and live loop | Pass |
| 8 | Signal plots work | waveform, FFT, PSD, spectrogram payloads and compiled UI | Pass |
| 9 | Posterior updates | matched-filter likelihood and recursive normalized update | Pass |
| 10 | Multiple experiments accumulate | history API, SQLite, belief evolution UI, integration test | Pass |
| 11 | Entropy is shown | engine metrics, history chart, benchmark trajectories | Pass |
| 12 | Final defect estimate produced | MAP, posterior mean, covariance, confidence | Pass |
| 13 | Ground truth can be revealed | simulation-only reveal API and UI guard | Pass |
| 14 | Localization error calculated | physical millimetre error after reveal and in evaluation | Pass |
| 15 | Random probing baseline works | seeded random policy in benchmark engine | Pass |
| 16 | ARGUS versus random benchmark runs | 30 paired cases plus grid baseline; saved JSON/CSV | Pass |
| 17 | WAV upload works | real PCM WAV integration test updates the posterior | Pass |
| 18 | Serial abstraction is functional | pyserial discovery, handshake, commands, parsing, errors; ESP32 firmware included | Pass* |
| 19 | Tests pass | 71 backend and 12 frontend tests passing | Pass |
| 20 | README has exact setup instructions | backend, frontend, unified launcher, demo, training, evaluation, and hardware commands | Pass |

`*` The software/firmware path is implemented and absence is handled, but actual electrical hardware was not available in this workspace. Physical sensing performance therefore remains unvalidated.

## Claims boundary

Verified software behavior and simulator results are complete. Three facts cannot be manufactured by software: measured physical-panel accuracy, human inventorship/conception records, and a patent-office filing receipt. Those require laboratory work, the actual contributors, and qualified counsel respectively.
