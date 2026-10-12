# ARGUS model artifacts

## Additional candidate, 20 September 2026

`forward_surrogate_50000_73123.pt` is a separately saved local candidate trained
using a 50,000-example synthetic bank (35,000 actual training rows). On a fresh
4,000-example paired comparison, common-scale MAE improved from 0.44659 to
0.43630 and mean feature R² from 0.46491 to 0.48902. The original
`forward_surrogate.pt` remains unchanged. Neither checkpoint is a validated
live NEO localization model. See `../docs/SURROGATE_TRAINING_2026_09_20.md` and
`../research_results/surrogate_comparison_73124.json` for the complete protocol,
uncertainty, per-feature regressions, and limitations. Generated candidate
weights remain local/Git-ignored.

## Retained reference and measured-domain artifacts

ARGUS runs with its interpretable physics likelihood when no checkpoint is present. `python scripts/train_model.py` creates an optional `forward_surrogate.pt` plus transparent training metadata. The 59 KB reference checkpoint and JSON metrics are intentionally small enough to share; other generated checkpoints remain excluded from Git.

The current checkpoint was trained on 15,000 domain-randomized simulator examples, five times the original training set. It was promoted only after a fixed 3,000-case external simulator benchmark improved mean feature R² from 0.407 to 0.461 and reduced standardized MAE from 0.468 to 0.437. Reproduce the same-checkpoint comparison with `scripts/evaluate_surrogate_checkpoints.py`; the recorded result is `research_results/surrogate_external_benchmark.json`.

`lmsd_surrogate.json` records the scenario-held-out experiment on the downloaded KU Leuven data. Its mean held-out feature R² is approximately zero despite a low aggregate Smooth L1 loss, demonstrating why six physical damage configurations are useful for pipeline validation but insufficient for a deployable response model. The generated weights remain local and ignored.

The sim-to-real workflow creates these transparent artifacts:

- `sim2real_acoustic_reference.json`: a robust empirical reference fitted to 2,568 measured GFRP microphone taps. For external physical acquisitions only, its upper 10% nonconformity tail contributes to ARGUS caution/abstention; simulated sessions are unaffected.
- `sim2real_feature_transport.json`: separate healthy/damage robust CORAL transforms from simulated features to measured GFRP feature moments. This is feature alignment, not fabricated physical waveforms.
- `sim2real_metrics.json`: complete-plate-held-out detection metrics and alignment diagnostics.
- `ae_timing_calibration.json` and `ae_sim2real_metrics.json`: paired simulation/experiment timing and leave-one-impact-position-out localization results, including a negative-transfer decision.

Generated `.joblib` estimators are intentionally Git-ignored and reproducible with `scripts/fit_sim2real_models.py` and `scripts/benchmark_ae_sim2real.py`.
