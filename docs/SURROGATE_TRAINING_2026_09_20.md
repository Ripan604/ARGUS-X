# Additional surrogate training - 20 September 2026

## Scope

This run trains the optional acoustic **response-feature predictor**, not the
live defect-localization controller. The current checkpoint is retained.
No physical recordings are created or claimed. "FOC" is not an identified
component in the repository; its intended meaning needs clarification before
changing a potentially unrelated subsystem.

## Fixed protocol

- Generate 50,000 independent simulator examples with generation seed 73123.
- Retain the existing compatible 24-input, 96-hidden-unit, 15-output MLP.
- Training seed 23: 35,000 training, 7,500 validation and 7,500 internal test rows.
- Fit normalization only on training rows. Select weights using validation loss
  with a 0.0001 minimum improvement; never use test results for epoch selection.
- Train for up to 160 epochs, batch size 256, AdamW initial learning rate 0.0018,
  validation-based learning-rate reduction, early-stopping patience 22.
- Bound CPU use to four PyTorch threads. No paid compute is used.
- Compare once against the retained baseline on 4,000 additional examples from
  generation seed 73124. Test input overlap with both development banks is checked.
- Standardize comparison errors using the **same baseline training scale** for
  both models; also report native-unit errors and R-squared for each feature.
- Report paired bootstrap intervals and features with more than 10% MAE
  regression. Preserve negative results. Do not replace a runtime model silently.

## Training corrections

Validation and test losses now weight batches by their sample count. Previously
the final, potentially smaller batch was weighted equally with a full batch.
The training history, chosen epoch, dataset hash, trainer hash, generation seed,
training seed and library version are saved alongside the checkpoint.
Input matrices and split sizes are validated before fitting.

## Reproduction

```powershell
python scripts/generate_dataset.py --samples 50000 --seed 73123 --output datasets/generated/argus_forward_50000_73123.npz
python scripts/train_model.py --data datasets/generated/argus_forward_50000_73123.npz --output models/forward_surrogate_50000_73123.pt --epochs 160 --batch-size 256 --patience 22 --lr-patience 6 --threads 4 --seed 23
python scripts/generate_dataset.py --samples 4000 --seed 73124 --output datasets/generated/argus_forward_holdout_73124.npz
python scripts/compare_surrogates.py --baseline models/forward_surrogate.pt --candidate models/forward_surrogate_50000_73123.pt --data datasets/generated/argus_forward_holdout_73124.npz --training-data datasets/generated/argus_forward_15000.npz datasets/generated/argus_forward_50000_73123.npz --output research_results/surrogate_comparison_73124.json
```

Use a new report filename on subsequent comparisons; the comparison command
refuses to overwrite previous evaluation evidence.

## Observed external evaluation

Both frozen checkpoints were evaluated once on the same 4,000 new examples.
No input rows overlapped the supplied old or new development banks.

| Metric | Retained 15,000-bank model | New 50,000-bank candidate |
|---|---:|---:|
| Standardized MAE, common baseline scale | 0.446591 | 0.436300 |
| Mean per-feature R-squared | 0.464908 | 0.489023 |
| RMS native-unit MAE | 0.003217 | 0.002674 |
| Peak-amplitude native-unit MAE | 0.021204 | 0.017109 |
| Envelope-peak timing MAE | 1.5485 ms | 1.5214 ms |

The aggregate MAE improvement is **2.30%**, not a localization accuracy increase.
The paired mean standardized-error advantage is 0.010292, with bootstrap 95%
interval [0.008368, 0.012236]. This interval conditions on these two checkpoints
and the simulator's sampling distribution, not new physical specimens.
Fourteen features improved in MAE; spectral-entropy MAE worsened by about 1.96%.
No feature exceeded the reported 10% regression threshold. Mean R-squared is not
an accuracy percentage. Dominant-frequency and envelope-timing R-squared remain
weak at about 0.094 and 0.057 respectively.

Training stopped at epoch 48; the retained candidate weights are from epoch 26.
Its internal validation Smooth L1 was 0.186322 and internal test Smooth L1
0.177911. These use the candidate's normalization and different samples, so they
must not be compared directly with the original checkpoint's internal losses.
The candidate checkpoint and metadata are saved separately under
`models/forward_surrogate_50000_73123.pt` and `.json`. The full comparison and
artifact hashes are in `research_results/surrogate_comparison_73124.json`.
The existing runtime and reference checkpoint have not been replaced.

Verification: 110 backend tests passed, including sample-weighted partial-batch
evaluation, split validation, and paired-comparison direction/scale regressions.
The existing HTTP-test-client deprecation warning remains nonfatal. The local
ARGUS API still reports healthy after training.

## Remaining limitations

Randomized damping, noise level and system delay are not all present in the
24-input feature contract. More epochs cannot recover variables the network
does not observe. The predictor must average over these hidden sources of
variation; weak timing/frequency features may remain weak.

This is an IID holdout from a simplified simulator. It does not test new material
physics, hardware coupling, dispersive waves, unseen physical specimens or
measured defect localization. The live NEO planner still lacks a validated
learned-surrogate adapter, so a surrogate improvement must not be advertised as
an improvement in live CEP, confidence, or localization accuracy.
