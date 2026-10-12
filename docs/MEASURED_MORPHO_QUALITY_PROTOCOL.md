# Prospective measured MORPHO quality protocol — 8 October 2026

This protocol is fixed after inspecting file schema and label support, before
training or inspecting classification results. It evaluates **operator GOOD/BAD
signal-quality labels** on an actively selected subset of measured guided waves.
It does not evaluate persistent damage localization, sensor authenticity, or the
performance of a deployed ARGUS apparatus.

## Dataset and independent split

Use the verified CC-BY-4.0 versioned deposit
[10.5281/zenodo.20120070](https://doi.org/10.5281/zenodo.20120070), citing the
original [10.5281/zenodo.14627730](https://doi.org/10.5281/zenodo.14627730).
The five pinned publisher files total 97,887,928 bytes. Official MD5 and local
SHA-256 are retained. No author software or pickle is executed.

The HDF5 contains 12,504 traces at 1 MHz, 50 kHz excitation, and 2,001 samples
per trace. Only the 1,011 existing operator-labelled traces are scored: 875 GOOD
and 136 BAD. Labels were selected through a human active-learning process;
they are not an unbiased random sample of all traces or future acquisitions.

| Held-out panel | GOOD | BAD | Actual unique HDF5 cycles | README cycles |
|---|---:|---:|---:|---:|
| FOD3 | 32 | 86 | 22 | 9 |
| FOD4 | 200 | 16 | 19 | 26 |
| FOD5 | 241 | 14 | 22 | 24 |
| FOD6 | 175 | 0 | 21 | 23 |
| FOD7 | 227 | 20 | 22 | 22 |

Use five leave-one-panel-out folds. All cycles, repetitions, and paths from a
panel remain together. No random row split, test-label selection, oversampling,
hyperparameter search, threshold optimization, or panel-ID feature is allowed.
The observed README/file discrepancy remains visible. Every labelled row must
bind exactly once to a finite-size numeric HDF5 leaf before evaluation.

## Fixed native waveform features

Read only the first 500 samples at the original 1 MHz rate. No decimation to the
live engine rate or reinterpretation as its synthetic propagation model occurs.
Compute sixteen numerical quality features using waveform values only:

1. Log10 RMS (floor 1e-12).
2. Absolute mean divided by RMS.
3. Centered peak divided by RMS.
4. Normalized power-spectrum entropy.
5. Power fraction in 40–60 kHz.
6. Power fraction below 10 kHz, including DC.
7. First-50-sample RMS divided by total RMS.
8. Last-50-sample RMS divided by total RMS.
9. Last-edge RMS divided by first-edge RMS.
10. Fraction of centered values within 2% of the absolute peak.
11. RMS of first differences divided by total RMS.
12. Centered zero-crossing fraction.
13. Absolute uncentered peak divided by RMS.
14. Centered lag-20 autocorrelation divided by centered total energy.
15. Centered RMS divided by raw RMS.
16. Fraction of finite samples.

Nonfinite samples, if present, are counted in feature 16 and replaced by zero
for the other descriptive statistics. Entirely zero or nonfinite traces receive
finite floor-defined features and remain in the labelled denominators. The peak
pile feature is a waveform-shape proxy, not proof of ADC saturation without the
original ADC range. No IDs, cycles, paths, timestamps, metadata, or labels enter
feature extraction.

## Fixed methods

- Logistic regression: training-only StandardScaler, C=1, balanced class
  weights, lbfgs, max_iter=2000, seed 20261008, BAD probability threshold 0.5.
- Random forest: 300 trees, max_depth=8, min_samples_leaf=3, balanced class
  weights, seed 20261008, one worker, threshold 0.5.
- Majority dummy: most frequent training class; no waveform features.
- Diagnostic control: the same forest with training labels shuffled **within
  each training panel**, preserving its class counts, using seed 20261008.
  Held-out labels remain original. Exactly one shuffle is used; no permutation
  p-value or confidence interval is claimed.

The shuffled-training control checks whether panel-dependent signal structure
and selected-label prevalence can produce apparent prediction without the
original within-panel quality relation. It is a diagnostic comparison, not an
additional tuned model. StandardScaler is fitted separately on training panels
only. No model pickle, joblib, or executable checkpoint is exported.

## Outcomes, failures and interpretation

BAD is the positive class. Retain every out-of-fold probability and predicted
class, all split membership, per-fold confusion counts, accuracy, BAD precision,
BAD/GOOD recalls, balanced accuracy, AUROC, and Brier loss. FOD6 has only GOOD:
its fold balanced accuracy and AUROC are **null**, while GOOD recall and false
BAD counts are reported. Undefined metrics never become artificial zero scores.

Report pooled out-of-fold balanced accuracy/AUROC and macro BAD and GOOD recalls
across folds where each class exists, with explicit class-support denominators.
Retain all attempted labels and failed fold/method records. Pooled metrics from
successful predictions are labelled conditional on completed folds, alongside
the attempted and scored counts. No failed case is silently removed.

There are five specimen groups and a strongly panel-dependent, actively selected
label distribution. This supports a conditional held-out-panel quality study;
it cannot establish an unbiased prevalence, generic population reliability,
probability calibration, or defect localization. No confidence interval over
1,011 correlated traces is represented as an independent-specimen interval.
Negative results and an outperforming majority/control baseline are preserved.

## Reproduction and source boundary

```powershell
.venv\Scripts\python.exe -m pytest backend\tests\test_measured_morpho_quality.py -q -o addopts=""
.venv\Scripts\python.exe scripts\validate_measured_morpho_quality.py
```

The default output is `research_results/measured_morpho_quality_2026_10_08.json`.
Before and after training, hash every retained publisher file, download manifest,
study/downloader source, protocol, and owned tests. Record installed NumPy,
SciPy, scikit-learn and h5py versions. A changed fingerprint invalidates frozen
source attribution; preserve such an output and rerun after source edits stop.
Every run retains feature values, complete splits and predictions, quality-label
scope, schema discrepancy, timing, and failure records. Runtime is bounded to
five panels, four methods, and at most 1,011 labelled signals.
