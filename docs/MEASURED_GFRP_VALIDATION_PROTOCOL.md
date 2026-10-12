# Measured GFRP validation protocol — 8 October 2026

This protocol is written before the new classifier fits. It reanalyses an existing public dataset, previously examined in ARGUS; it is not an independent prospective blind trial. No historical metric, model binary, raw recording, or derived archive will be overwritten.

## Physical data and attribution

Use the unaugmented clipped microphone recordings from [TU Darmstadt's dataset record](https://tudatalib.ulb.tu-darmstadt.de/items/33756af4-eb6d-4156-8708-a41cbed33e7b), attributed to Robert Feldmann, Finn Meding and Tobias Melz (2026), *Audio Signal-Based Delamination Detection for Wind Turbine Rotor Blades Using an Autoencoder*. The downloaded publisher README declares [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). The publisher page/API could not be accessed through the browser during this audit; retain and checksum-verify the previously downloaded publisher README and manifest rather than claiming fresh online verification.

The inspected local data contain 2,568 mono float32 clips, each 5,120 samples at 51,200 Hz (100 ms), from eight physical plates. There are 2,100 intact-labelled and 468 defect-labelled taps. These labels support pointwise audio-tap defect screening, not persistent-defect coordinates, arrival-time localization, adaptive inspection, probability of detection, or certification of the user's apparatus. The publisher warns that the separate hammer force channel clipped; this study uses microphone clips only.

## Label and input audit

Read labels from the publisher's intact/defect directories and independently compare them with the downloaded README's filename/point rules: ordinary plates 1–4 intact; their Schlagschaden recordings defect; plates 5/6 points {9,10,15,16,32,35,38,41} defect; plate 7 points 25–30 and all Zusatz recordings defect; plate 8 points 19–30 defect. Reject mismatches. Filenames, paths, point coordinates, plate IDs, modifiers, run/side identifiers and labels never enter the feature matrix. The rules themselves are publisher annotations, not new independent physical truth measurements.

Hash every WAV file and its decoded PCM payload. If identical decoded recordings occur in different plates, exclude every member of that cross-plate duplicate set before any fit, retaining their indices and reasons. Ordinary within-plate repeats remain grouped. The preliminary format/label audit found no mismatches or duplicate PCM clips; no performance metric has been calculated for this protocol.

Verify publisher MD5s and sizes for the downloaded ZIP and README files, then compare each extracted WAV's SHA256 against the corresponding ZIP member bytes and require the same complete member list. Require the registered 2,568-clip cohort and original 2,100/468 class counts before exclusions. Record SHA256s for these files, the local manifest, every WAV, the historical numeric NPZ, feature-processing code, adapter code, this script, tests and protocol before and after the complete run. Any change invalidates the run and remains explicitly reported.

## Fixed feature preprocessing

Recompute all 15 existing ARGUS features separately from each raw clip: RMS, peak amplitude, crest factor, zero-crossing rate, spectral centroid/bandwidth/rolloff, dominant frequency, spectral entropy, three band energies, envelope-peak time, decay time and SNR. Preserve signed PCM normalization before any channel averaging; float32 audio needs no integer scaling. Rational polyphase resampling to 16 kHz and the existing 250–7,000 Hz signal filter are fixed per-record operations, with no labels or statistics from other recordings. Do not use CORAL, the previously fitted acoustic reference, or any .joblib/pickle checkpoint. Inspect the historical NPZ only with `allow_pickle=False`, compare metadata/path/label/group alignment and recomputed feature differences, and never use it to fit the new models.

## Frozen models and split

Use deterministic four-fold `GroupKFold` over complete physical plates, retaining all eight plate groups. Save exact row indices, training/test plates, class counts and scaler statistics for each fold. Train/test plate overlap is prohibited. Reject and retain any fold whose training or test partition has fewer than two classes; do not replace it or conceal its missing predictions.

The fixed seed is **20261008**. Fit these three baselines without tuning, feature selection or threshold optimization:

- No-feature majority baseline: `DummyClassifier(strategy='most_frequent')`, receiving one constant zero column.
- Linear baseline: `Pipeline(StandardScaler(), LogisticRegression(C=1, class_weight='balanced', solver='lbfgs', max_iter=2000, random_state=seed+fold))`.
- Tree baseline: `Pipeline(StandardScaler(), RandomForestClassifier(n_estimators=300, max_features='sqrt', min_samples_leaf=3, class_weight='balanced_subsample', n_jobs=1, random_state=seed+fold))`.

Fit each scaler only on that fold's training rows. The probability threshold remains 0.5. No final all-data classifier or unsafe model binary is saved; outputs are JSON evidence and predictions only.

## Metrics, uncertainty and leakage diagnostic

Retain every out-of-fold probability, failure, warning and runtime. Report aggregate and per-fold accuracy, balanced accuracy, ROC-AUC, F1, and labelled TN/FP/FN/TP counts. Separately report metrics for each held-out plate and equal-weight plate means. Failed-fold rows remain null; any aggregate over valid rows must disclose coverage and its conditional denominator.

For uncertainty, use 2,000 seeded bootstrap resamples of the **eight plate clusters**, retaining all rows/predictions belonging to each selected plate, including repeated clusters. Report percentile 95% intervals and the number of valid resamples. These intervals condition on already fitted out-of-fold predictions; they do not account for model selection or refitting uncertainty. Eight independent plates remain a small population regardless of the number of correlated taps.

For a leakage sanity check, run ten fixed within-plate label permutations, preserving each plate's class counts, with the same whole-plate folds and freshly trained linear/tree pipelines. Both training and test targets are permuted for the control. Retain all control metrics and label hashes. This destroys the tap-feature/label relationship without introducing train/test plate overlap. It is a diagnostic, not a formal significance test: correlated repeated points are not generally independently exchangeable. Do not select a permutation seed or model after seeing its result.

## Execution and output

Run meaningful focused tests of held-out scaler isolation, plate disjointness, rejection accounting, publisher labels, duplicate exclusion, safe numeric NPZ handling and cluster bootstrap before fitting the actual recordings. Then freeze the protocol/script/tests and run:

```powershell
.venv\Scripts\python.exe scripts\validate_measured_gfrp.py
```

The new report is `research_results/measured_gfrp_validation_2026_10_08.json`; refuse to overwrite it. Retain the original inputs and historical `models/sim2real_metrics.json`. Interpretation must state the actual observed results, including failure or no improvement, and retain the pointwise-screening scope.
