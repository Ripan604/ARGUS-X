# Measured structural/acoustic dataset catalog — 8 October 2026

The most immediately useful additional source is the **97.65 MB numeric MORPHO
curated subset**, now acquired and verified locally. It supports independent
panel holdouts for **signal-quality classification**, not defect-position truth.
None of the sources below provides a quick replacement that simultaneously
combines numerous independent specimens, numerous true persistent defect
positions, complete counterfactual transducer banks, and small open files.

This catalog adds six sources beyond the existing LMSD/TUGFRP/Bologna studies.
Open Guided Waves is being handled separately. Exact details not verified in the
primary record are marked unknown rather than inferred from excitation frequency.

## 1. MORPHO curated 50 kHz universe — acquired

- [Official versioned record](https://zenodo.org/records/20120070), DOI
  [10.5281/zenodo.20120070](https://doi.org/10.5281/zenodo.20120070).
  Official API and retained `LICENSE` both verify **CC BY 4.0**.
- Five files, 97,887,928 bytes total; numeric HDF5 is 97,647,899 bytes, plus
  README, license, citation, and JSON labels. Official MD5 and local SHA-256
  provenance are retained in `datasets/external/morpho_50khz/download_manifest.json`.
- Source campaign: [10.5281/zenodo.14627730](https://doi.org/10.5281/zenodo.14627730),
  CC BY 4.0; its live inventory currently offers FOD7 HDF5 (8,342,365,080 bytes),
  a 1,210,287-byte README PDF, and a MATLAB example. The curved, varying-thickness
  3D-woven engine-blade substructure is approximately 800 x 350 mm, with an impact
  followed by escalating four-point-bending fatigue. This original inventory
  does not independently document all five specimens of the derived deposit.
- Actual curated HDF5: FOD3–FOD7, 12 directed conventional-PZT paths per panel,
  `/<panel>/50kHz/actA/recvR/cycleC/data`, numeric float32 arrays
  `(n_repetitions, 2001)` at **1 MHz**. Screen-printed channels and drive channels
  are excluded. 12,504 traces are present; 1,011 unique GOOD/BAD labels bind valid
  rows. GOOD means a clean wave packet; BAD includes noisy, saturated, low-energy,
  or mean-drifting signals. These are actively selected operator quality labels.
- Independent split: hold out an entire panel, including all paths, cycles,
  repeats, and labels. Do not treat repetitions as independent specimens or
  infer a damage coordinate from quality labels.

| Panel | Verified traces | Verified distinct cycles | README cycles | GOOD labels | BAD labels |
|---|---:|---:|---:|---:|---:|
| FOD3 | 1,104 | 22 | 9 | 32 | 86 |
| FOD4 | 3,120 | 19 | 26 | 200 | 16 |
| FOD5 | 2,880 | 22 | 24 | 241 | 14 |
| FOD6 | 2,760 | 21 | 23 | 175 | 0 |
| FOD7 | 2,640 | 22 | 22 | 227 | 20 |

The documented cycle counts disagree with the actual file. Preserve both;
verified trace totals agree. FOD6 has no selected BAD labels. Its fold AUROC and
balanced accuracy are undefined, and must not be invented or removed. Strong
panel-dependent label prevalence and active selection limit population inference.

The frozen [MORPHO quality protocol](MEASURED_MORPHO_QUALITY_PROTOCOL.md) was
subsequently executed on all 1,011 selected labels, with five panel holdouts and
no failed fold. Source and input hashes remained unchanged. The complete record
is `research_results/measured_morpho_quality_2026_10_08.json`.

| Fixed quality method | Pooled balanced accuracy | Pooled AUROC | BAD recall at frozen threshold |
|---|---:|---:|---:|
| Logistic regression | 0.5124 | 0.2675 | 27/136 = 0.1985 |
| Random forest | 0.4997 | 0.7715 | 1/136 = 0.0074 |
| Majority dummy | 0.5000 | 0.5000 | 0/136 |
| Forest with shuffled training labels | 0.4989 | 0.5216 | 0/136 |

These measured results do **not** justify deploying a general BAD-signal
classifier. The forest has some ranking discrimination but fails to reject BAD
signals at the prespecified 0.5 threshold; the majority dummy achieves higher
ordinary accuracy because most selected labels are GOOD. No held-out threshold
was retuned. This negative result is retained as a transfer/selection limitation,
separate from ARGUS's physics-based measurement-quality checks.

## 2. SmartDATA long-term guided waves — excellent nuisance evidence, deferred

[Dataset DOI 10.6084/m9.figshare.28112504.v1](https://doi.org/10.6084/m9.figshare.28112504.v1)
and [primary data paper](https://doi.org/10.1038/s41597-025-05300-5).
The live official API verifies CC BY 4.0: **56 monthly pickle files,
101,612,250,985 bytes** total; the smallest file is 599,491,623 bytes.
No pickle has been downloaded or loaded.

One 530 x 530 x 3 mm aluminum plate was observed outdoors in 2018–2022.
Two transmitters and four receivers yield eight measured paths. The published
traces retain 2,000 samples at **1 MHz**; excitation is a 1 ms chirp spanning
5–350 kHz. Environment tags and 13 progressively altered central damage states
include attached mass, dents, and through-holes. This is strong environmental
and sensor-drift evidence, but all damage positions are central, so it cannot
validate general location recovery.

Recommended future split: consecutive calendar blocks with guard gaps; a
healthy-only training period, later untouched healthy false-alarm periods,
and untouched damage transitions. Keep eight paths of one timestamp together.
Request or independently produce an inert numeric subset in an isolated
conversion environment; the current no-pickle workflow cannot consume it.

## 3. NASA/PHM 2019 fatigue crack growth in aluminum lap joints — promising small source

[NASA official record](https://data.nasa.gov/dataset/fatigue-crack-growth-in-aluminum-lap-joint)
links [PHMDC2019_Data.zip](https://data.nasa.gov/docs/legacy/PHMDC2019_Data.zip).
NASA explicitly lists the US-government-works license URL and Arizona State
University creators; do not substitute a guessed CC0 license. No standalone
dataset DOI is stated in that NASA record.

The [challenge organizer's documentation](https://data.phmsociety.org/2019datachallenge/)
describes eight specimens: T1–T6 training, T7–T8 validation. Two wave captures per
measurement point and a 161 mm actuator–receiver separation accompany optical
crack lengths and load history. T8 uses variable-amplitude loading. Only sensor
pairs bracketing cracks are provided, rather than a full arbitrary action bank.
The organizer advertises a **983 KB corrected training archive**, and the
[final validation page](https://data.phmsociety.org/2019datachallengesubmission/)
advertises 301.69 KB. Current NASA archive bytes, internal file counts, raw
sample count and sampling rate remain unverified; derive rates from published
time columns before any timing model.

Keep entire specimens separate and preserve chronological cycles. Crucially,
the [organizer's correction notice](https://data.phmsociety.org/phmdata-forums/topic/question-on-validation-data/)
documents that the original T6 mistakenly contained three T8 wave sets. Require
the corrected 18 July 2019 training version and check cross-split numeric hashes.
This is crack-length/prognosis evidence, not arbitrary 2D localization.

## 4. Wind-turbine blade guided waves during cyclic loading — real fatigue, larger archive

[Record and dataset DOI 10.5281/zenodo.13692213](https://doi.org/10.5281/zenodo.13692213),
[primary data paper DOI 10.1061/JSENDH.STENG-14724](https://doi.org/10.1061/JSENDH.STENG-14724).
Live API verifies **CC BY 4.0**, one ZIP of **1,695,645,067 bytes**.
No raw archive was downloaded.

One Sonkyo Windspot 3.5 kW blade has one PZT source and four receivers, strain
gauges, and a temperature channel. Fatigue and eventual overload are measured.
Dynamic signals are synchronized to three phases of mechanical loading;
static measurements follow 1,000-cycle blocks and average ten wave captures.
The inspected record does not specify raw sampling frequency or signal length;
these require the archived readme/time arrays. There are no independently
held-out blade specimens in this record.

Use blocked fatigue-stage holdouts, keeping loading phases, receivers, repeats,
and averaged signals from the same block together. Never split a static average
from the raw captures that formed it. A bounded remote-ZIP metadata extraction
would be needed before selecting a small acquisition subset.

## 5. Guided-wave pipeline monitoring — compact domain-specific severity evidence

[Primary Mendeley record, DOI 10.17632/ttb63krg6d.1](https://doi.org/10.17632/ttb63krg6d.1)
explicitly provides **CC BY 4.0**.
One 6.4 m steel pipe includes a 1 m composite repair and a corrosion-like
machined defect 2.6 m from the commercial probe. Six damage-growth steps and
19–26 °C environmental variation span about three months.

The author describes 236 acquisition records: 207 healthy and 29 damaged.
Each Excel record has sheets for 14, 18, 24, 30, and 37 kHz, containing distance,
torsional response, flexural response, and distance-amplitude correction.
These are **distance-domain responses**; raw temporal fs/count and live file
inventory bytes were not exposed by the inspected landing page. Do not treat
the excitation frequencies or distance column as a measured source sample rate.

A useful split is an early healthy baseline versus later held-out healthy and
damage-stage blocks, with all frequency sheets of an acquisition kept together.
Single-probe pipeline modes do not constitute a plate's full 2D action bank.

## 6. Plastic-plate impact events — accessible, but a different label/task

[Official Zenodo record](https://zenodo.org/records/7199346) lists
[publication DOI 10.1145/3560905.3567764](https://doi.org/10.1145/3560905.3567764).
Its live API verifies **CC BY 4.0**, one ZIP of **66,107,140 bytes**.
The [authors' repository](https://github.com/Smart-Objects/Impact-Events-Dataset)
is an additional primary reference; author scripts have not been executed.

Four corner PZTs on one plastic plate record 5,000 samples each at **100 kHz**.
A steel ball dropped from 10–20 cm generates low-energy impacts, with at least
three repeats per configuration. Plate dimensions, exact event/file counts and
the position grid need archived metadata verification before a physical map.
This identifies the **source of an impact event**, not a pre-existing persistent
defect via actively selected source–receiver experiments.

Hold out complete spatial impact configurations, keeping all four channels,
heights and repeats together. Split entire events before windowing. It is useful
for timing/embedded acquisition studies, but cannot substantiate ARGUS's hidden
defect-localization claim without a separately scoped passive-impact branch.

## Predeclared Open Guided Waves replay safeguards

These are methodology recommendations, not dataset facts or performance claims.

1. Describe the experiment as offline measured-path revelation on one plate
   carrying reversible mass surrogates. Do not call path reveals new physical
   acquisitions or imply independent specimen generalization.
2. Use healthy cycle 1 only for baseline selection, time windows, mode-specific
   calibration, and noise scales. Hold healthy cycle 2 blind for false alarms.
   If 60 °C healthy references inform calibration, 60 °C is not a held-out
   environmental condition. Preserve this distinction in the protocol.
3. Split entire damage positions before fitting velocity, ellipse width, map
   likelihood scale, thresholds, or stopping rules. Every temperature, repeat,
   and transducer path of a held-out position stays in that group.
4. The policy receives only revealed damaged paths. Computing unused damaged
   path decorrelations or ranking all damaged paths before choosing the next
   path leaks the measurement budget. Healthy reference banks are allowed only
   as pre-existing common information with their cost disclosed.
5. Compare identical inference with random paths, a deterministic geometry-spread
   sequence, and a training-only learned static sequence at equal reveal budgets.
   Also retain fixed full-bank RAPID as a separately cost-labelled comparator.
   Tune RAPID width and windows only on training positions/healthy references.
6. Work at native frequency and sampling units. A 40 kHz composite-guided mode
   cannot reuse the backend's 180 m/s synthetic parameter without calibration.
   A normalized RAPID map is an imaging score, not certified posterior confidence.
7. Report per-position and per-temperature outcomes, failures, and healthy false
   alarms. Four positions do not become hundreds of independent cases because
   they have many paths and temperatures. Any resampling clusters by physical
   position and clearly acknowledges the tiny number of independent groups.

RAPID is an established comparator; a
[primary experimental methods paper](https://www.mdpi.com/1996-1944/16/23/7390)
details its baseline correlation features and ellipse-width parameter. Combining
RAPID-like maps and Bayesian updates is also established: the
[2024 IEEE pipeline paper, DOI 10.1109/TIE.2024.3366209](https://doi.org/10.1109/TIE.2024.3366209)
uses correlation density, elliptical likelihoods and Bayesian position updates.
Neither a measured cell map nor adding Bayesian terminology establishes novelty.

## Retained primary metadata and reproducibility

Four small primary API responses are retained in
`datasets/external/catalog_sources/`, with source URLs, exact byte counts, and
SHA-256 in `catalog_metadata_manifest.json`. They verify current licenses and
file inventories for MORPHO original, wind blade, impact events, and SmartDATA.
The verified MORPHO download is reproducible with:

```powershell
.venv\Scripts\python.exe scripts\download_morpho_dataset.py
```

The downloader checks the pinned official inventory, license, byte bounds,
publisher MD5 and local SHA-256 before accepting data. License and provenance
checks do not certify sensor authenticity, apparatus calibration or benchmark
performance. Original publisher files remain unchanged.
