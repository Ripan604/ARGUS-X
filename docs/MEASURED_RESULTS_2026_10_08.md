# ARGUS measured-data campaign and results

**Prepared:** 8 October 2026. Public measured-data evaluations, preserved with complete source and raw-data provenance.

## What has now been achieved

Two new measured datasets were acquired: 18 complete Open Guided Waves banks (250.18 MB) and the MORPHO curated dataset (97.89 MB). The existing GFRP and Bologna recordings were also audited and reanalysed. No downloaded code or pickle model was executed. Public lab measurements were used directly at their documented sampling rates; missing paths, labels and reciprocal responses were not synthesized.

The strongest positive finding is plate-held-out audio-tap screening. Measured source localization also improves over a train-centroid baseline. The native ultrasonic path study exposes substantial location errors and healthy false positives. The cross-panel signal-quality classifier fails at its frozen threshold. These four outcomes describe different tasks and cannot be combined into one inspection-accuracy percentage.

## Sources, licenses and actual independent units

| Dataset | Measured subset and task | Independent units / license |
|---|---|---|
| [TU Darmstadt GFRP](https://tudatalib.ulb.tu-darmstadt.de/items/33756af4-eb6d-4156-8708-a41cbed33e7b) | 2,568 microphone taps, 51.2 kHz; pointwise intact/defect screening | Eight plates; CC BY 4.0 |
| [Bologna AE](https://zenodo.org/records/10875042) | Nine 2 MHz, three-sensor position records; transient source localization | One plate / nine positions; CC BY 4.0 |
| [Open Guided Waves 2](https://doi.org/10.6084/m9.figshare.c.4488089.v1) | 18 native 10 MHz banks / 40 kHz excitation / 66 actual paths | One plate / four removable mass positions; CC0 |
| [MORPHO](https://zenodo.org/records/20120070) | 12,504 native 1 MHz signals; 1,011 selected GOOD/BAD labels | Five panels; labels actively selected; CC BY 4.0 |

OGW whole archives exceed 160 GB; bounded ZIP64 byte ranges retrieved only the selected full HDF5 banks. Each selected member has checked CRC32 and local SHA-256. The publisher whole-archive MD5 remains explicitly unverified. MORPHO files and the existing GFRP/Bologna source files were checked against published checksums. Exact URLs, actual temperatures, coordinates, schemas and licenses remain in acquisition manifests.

## GFRP: a positive measured screening result

Four folds held out whole plates; all channels, points and repeats from a test plate stayed out of training. Features were recomputed from raw WAVs, filename/coordinate labels were excluded, scaling was fitted on training data, and all out-of-fold predictions were retained.

| Model | Balanced accuracy | ROC-AUC | F1 | Overall accuracy |
|---|---|---|---|---|
| Majority baseline | 0.500 | 0.500 | 0.000 | 0.818 |
| Logistic regression | 0.838 | 0.922 | 0.649 | 0.833 |
| Random forest | 0.768 | 0.913 | 0.626 | 0.866 |

Logistic regression balanced accuracy is 83.8%, with a plate-cluster percentile interval of 75.2-91.5%. Its confusion counts are 396 detected defect-labelled taps, 72 missed taps, 1,743 correctly intact-labelled taps and 357 false defect-labelled taps. RF has higher overall accuracy but worse balanced accuracy, AUC and F1. Class imbalance makes the majority baseline 81.8% accurate despite detecting no defect-labelled taps.

The interval uses only eight plate clusters and conditions on fitted predictions; models are not refitted inside the bootstrap. Ten within-plate label permutation controls were near chance. This supports pointwise screening within this acquisition domain, not location, defect type, adaptive measurement efficiency or the user apparatus.

## Bologna: measured source localization with strict position holdouts

Each complete position was held out. A bounded inverse-speed/two-relative-offset TDoA calibration used the other eight positions. The complete 1 m plate was searched on a fixed 5 mm grid. Three-neighbour preprocessing also used training data only. No numerical simulation data entered this reanalysis.

| Method | Mean error (mm) | Median (mm) | Within 100 mm |
|---|---|---|---|
| Train centroid | 181.07 | 168.75 | 11.1% |
| One neighbour | 211.91 | 212.13 | 0.0% |
| Three neighbours | 140.56 | 146.34 | 22.2% |
| Calibrated TDoA | 108.99 | 80.78 | 55.6% |

The 108.99 mm mean TDoA error is about 39.8% below the train-centroid error, but no held-out event is within 20 mm. This is a previously seen record on one plate, not new unseen validation or a persistent hidden-defect test. The CSV schema is 5,000 by three with columns s1/s2/s3; a separately identified repetition axis is absent even though the provider description mentions repeated experiments.

## OGW: first native measured-path replay result

A new offline evaluation branch preserves 40 kHz/10 MHz observations instead of converting them into audio-range data. A fixed RAPID-style elliptical response model was calibrated on three reference positions; every temperature of the fourth position stayed held out. The second healthy thermal cycle was never used for calibration. Five policies revealed only the requested test path, with the same inference and path budgets.

The 960 trajectories include random-order repetitions and repeated trained models. They are not 960 independent physical trials: only four reference positions, twelve damage-condition banks and three unique healthy test banks support evaluation.

| 32-path policy | Matched mean conditional error (mm) | 20 C baseline mean error (mm) | Matched conditional success within 50 mm |
|---|---|---|---|
| Cyclic | 178.72 | 218.72 | 8.3% |
| Geometry spread | 263.65 | 276.01 | 8.3% |
| Training static | 213.04 | 229.04 | 8.3% |
| Random (16 orders) | 190.70 | 248.45 | 8.9% |
| Adaptive disagreement | 160.76 | 200.04 | 25.0% |

Adaptive matched-baseline conditional MAP error is 160.76 mm versus random 190.70 mm. However, its model calls only 50% of the reference-scatterer conditions damaged and falsely flags 66.7% of healthy condition/model evaluations. Those evaluations reuse three healthy test banks under four trained models. Conditional distance success is not joint operational detection/localization success.

The full 66-path model has matched-baseline mean error 213.28 mm; classical full-bank RAPID has 209.43 mm. The full banks cost 66 reveals and are not equal-budget competitors. More evidence can worsen error when an observation model is misspecified. With a 20 C baseline at all test temperatures, adaptive mean error is 200.04 mm and there are no conditional 50 mm successes at 32 paths.

All trajectories completed with zero rejected opportunities. Modeled containment can be broad despite its apparent coverage; it is not a calibrated confidence region. The fixed global kernel/noise model and cross-date temperature/coupling differences remain major limitations. No beta, window or threshold was retuned on held-out results. A successful first run was preserved as a preflight pilot; the final rerun changed only validation/exception handling and meaningful causality tests. Every location metric remained identical.

## MORPHO: a negative cross-panel quality result

Five complete panels were held out in turn. GOOD/BAD are actively selected human signal-quality labels, not defect labels. One panel has no BAD-labelled examples, so that fold has undefined AUC/balanced accuracy; it remains in the recorded evaluation. Actual HDF5 cycle counts disagree with the README, and the schema audit retains both.

| Model | Balanced accuracy | BAD found / 136 | BAD recall |
|---|---|---|---|
| Logistic regression | 0.512 | 27 / 136 | 19.85% |
| Random forest | 0.500 | 1 / 136 | 0.74% |
| Majority baseline | 0.500 | 0 / 136 | 0.00% |

RF misses 135 of 136 BAD signals at the frozen 0.5 threshold. Its 0.772 ranking AUC and 85.95% overall accuracy do not make it a working rejection gate. The majority baseline is 86.55% accurate while rejecting none of the BAD signals. Strong panel prevalence differences and selected labels limit interpretation. No threshold was retuned and no quality classifier was deployed.

## What the project now contains

The repository contains reproducible public-data acquisition, native HDF5 validation, a causally restricted path oracle, whole-group evaluation, simple baselines, complete failures/negative findings, and source/raw hashes. The new replay module is for offline research and is separate from physical session execution. The operating apparatus still needs its own measured timing/transfer bench and blind physical inspection.

The full measured release verification passed 541 tests with one deliberate legacy-pickle skip. No physical probe was flashed or actuated for this campaign. Licenses and attribution remain with each source. Data acquisition alone does not establish patent novelty.

## Reproduction

```powershell
.venv\Scripts\python.exe scripts\download_open_guided_waves.py
.venv\Scripts\python.exe scripts\download_morpho_dataset.py
.venv\Scripts\python.exe scripts\validate_measured_gfrp.py
.venv\Scripts\python.exe scripts\validate_measured_impact.py
.venv\Scripts\python.exe scripts\validate_measured_guided_waves.py
.venv\Scripts\python.exe scripts\validate_measured_morpho_quality.py
.venv\Scripts\python.exe scripts\export_measured_web_summary.py
```

Preserve final reports. The impact/OGW commands refuse overwriting existing evidence; choose a new dated output when intentionally repeating them. The other commands should likewise be run with a new output path when retaining an earlier result. Dependency pins include h5py 3.16.0. All full study reports and protocols are under research_results/ and docs/. The Research page shows a compact task-separated summary.

## Source-bound result artifacts

| Study | Result file | SHA-256 |
|---|---|---|
| GFRP | research_results/measured_gfrp_validation_2026_10_08.json | d6a4a536243bb928fc6e073775a6c00f771914b0a1bf27f4391e0e3d41da9edc |
| IMPACT | research_results/measured_impact_validation_2026_10_08.json | 878533aff4d0df7623d76899ed745b569d81b075f86b888f130df0f35661dfe5 |
| OGW | research_results/measured_guided_wave_validation_2026_10_08.json | 4e3d97ca4cab63f97900363a76cbb74c65ba75624e58f014f4ccf03ae80cfbf6 |
| MORPHO | research_results/measured_morpho_quality_2026_10_08.json | e034c9488f97d05ae2dbe78f5246e59c4c5659c57dec8ad47c0c1c7e9f4a22c1 |
