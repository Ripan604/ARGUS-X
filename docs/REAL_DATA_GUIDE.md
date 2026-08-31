# Real training data: acquired set and collection protocol

## What is already downloaded

ARGUS now has local, checksum-verified copies of [LMSD 2021](https://zenodo.org/records/11033677), the [TU Darmstadt GFRP acoustic dataset](https://tudatalib.ulb.tu-darmstadt.de/items/33756af4-eb6d-4156-8708-a41cbed33e7b), and the [Bologna paired impact-localization dataset](https://zenodo.org/records/10875042). All three selected records declare CC BY 4.0.

The new measured-data bridge and its results are documented in [SIM2REAL_REPORT.md](SIM2REAL_REPORT.md). The key outcomes are 0.775 complete-plate-held-out balanced accuracy on 2,568 real GFRP microphone taps and a leave-one-position-out impact-localization reduction from 0.175 m to 0.141 m after adding measured few-shot calibration. Neither result is presented as validation of the final laptop/mobile apparatus.

It contains:

- a 600 × 600 × 4 mm cross-ply CFRP plate;
- a 12 × 12 grid of 144 known physical coordinates;
- seven accelerometer/impact-hammer probing nodes;
- a healthy frequency-response baseline;
- five point-mass scenarios and one elongated added-mass scenario;
- complex FRFs with 8,192 bins from 0–1,600 Hz;
- known added-mass nodes as spatial labels.

The external files occupy about 171 MB under `datasets/external/lmsd2021/` and are intentionally Git-ignored. `scripts/prepare_lmsd_dataset.py` converts all 6 scenarios × 7 sources × 7 receivers into 294 finite examples following the existing ARGUS 24-input/15-response-feature surrogate contract. The derived file is `datasets/generated/lmsd_forward.npz`.

The adapter represents an added mass as a `dense_inclusion`, converts each measured FRF into a 0.12-second impulse response, extracts the standard ARGUS signal features, normalizes source/receiver and defect coordinates, and preserves DOI/license/scenario provenance in metadata.

## What the experimental set can and cannot do

Use it now for:

- validating the signal and feature pipeline on measured structural responses;
- checking whether simulated feature ranges cover a real CFRP plate;
- pretraining or fine-tuning a response emulator for dense-inclusion-like scattering;
- testing source/receiver geometry code on real multistatic data;
- demonstrating a licensed, reproducible sim-to-real path.

Do not treat it as sufficient proof of cavity/delamination localization. It has only six independent damage configurations, includes multiple masses in several scenarios, uses hammer/accelerometer FRFs rather than ARGUS's current chirps, and does not contain sequential adaptive runs. A scenario-held-out training experiment produced test Smooth L1 `0.1903` but mean per-feature R² only `0.001`; this is evidence that 294 correlated channels are not equivalent to 294 independent defects. Random channel-level splitting is prohibited because it would leak the same physical damage scenario into train and test.

## Reproduce the acquisition and adaptation

```powershell
python scripts\download_lmsd_dataset.py --profile all
python scripts\prepare_lmsd_dataset.py
python scripts\train_model.py --data datasets\generated\lmsd_forward.npz --output models\lmsd_surrogate.pt --epochs 120 --patience 15 --split-mode group
python scripts\download_sim2real_datasets.py
python scripts\prepare_tud_gfrp_dataset.py
python scripts\fit_sim2real_models.py
python scripts\prepare_ae_impact_dataset.py
python scripts\benchmark_ae_sim2real.py
```

The downloader queries the official Zenodo record, downloads only declared files, and verifies every published MD5. `--profile minimal` fetches the healthy baseline plus the single point-mass case; `--profile metadata` fetches only documentation/license files.

## Other useful public sources

| Dataset | Strength for ARGUS | Limitation |
|---|---|---|
| [Open Guided Waves datasets](https://openguidedwaves.de/downloads/) | CFRP plates, PZT networks, broad frequencies, artificial damage, environmental variants, well-known SHM benchmark | Large HDF5 collections and different ultrasonic sample rates require a dedicated adapter |
| [Long-term guided-wave SHM dataset](https://github.com/SmartDATA-Lab/Long_Term_Guided_Waves) | Approximately 6.4 million waves, environmental drift, 12 PZTs, introduced damage conditions | Very large; strongest for robustness/OOD studies, and first-arrival localization is difficult because of reflections |
| [Wind-turbine blade SHM dataset](https://zenodo.org/records/13692213) | Real fatigue progression, piezo responses, strain and temperature | 1.7 GB and better suited to damage progression/detection than arbitrary 2D defect localization |
| [CFRP stringer wavefield dataset](https://zenodo.org/records/5105861) | Full laser-vibrometer wavefields for healthy/local/large debond cases | Fixed actuator and few independent damage states; enormous total data volume |
| [Impact Events plate dataset](https://github.com/Smart-Objects/Impact-Events-Dataset) | Raw PZT time series, known impact coordinates, low-cost MCU acquisition | Localizes impacts rather than persistent hidden defects; CC BY-NC-SA restricts commercial use |

The best next external integration is Open Guided Waves dataset #1 because it has a 0.5 × 0.5 m CFRP plate, twelve transducers, artificial damage locations, and broad source/receiver/frequency measurements. Confirm the terms attached to the particular downloaded files and preserve their requested citation.

## How to collect data tailored to ARGUS

### Hardware

- Three nominally identical 600 × 400 mm panels for a pilot; use aluminium, acrylic, plywood, or CFRP according to the intended market.
- Eight repeatably mounted piezo discs or accelerometers around the perimeter.
- One instrumented exciter or speaker driven through a safe amplifier/MOSFET stage.
- Spring-loaded fixtures or torque-controlled mounts so coupling force is repeatable.
- A healthy reference panel and reversible defects first: bonded masses, magnets on opposite faces, removable damping patches, or known inserts.
- For true cavity/delamination evidence, manufacture specimens with measured inserts, flat-bottom holes, PTFE release films, or controlled impact damage and confirm truth using ultrasound, X-ray, or destructive sectioning where appropriate.

### Acquisition matrix

For the current 16 kHz ARGUS path, collect each response for 0.12–0.25 seconds using:

- chirps at 1.2–3.0, 2.2–4.4, and 3.4–6.2 kHz;
- all 56 ordered source/receiver pairs from eight transducers, excluding self-pairs;
- at least five repeats per configuration;
- healthy references before and after every damage-location block;
- randomized experiment order to prevent temperature or battery drift from becoming a label shortcut.

One defect state would produce `56 × 3 × 5 = 840` waveforms. Twenty known locations plus healthy references produce roughly 17,000 signals—small enough to manage but large enough for honest held-out testing. Save raw float32/PCM data; never save only hand-engineered features.

### Minimum labels and metadata

Each waveform should have:

```text
specimen_id, panel_width_mm, panel_height_mm, material, thickness_mm
defect_id, defect_type, center_x_mm, center_y_mm, radius_x_mm, radius_y_mm, severity
source_id, source_x_mm, source_y_mm
receiver_id, receiver_x_mm, receiver_y_mm
waveform, frequency_start_hz, frequency_end_hz, amplitude, duration_s, sample_rate
repeat_id, timestamp, temperature_c, humidity, coupling_force, remount_id
calibration_id, raw_signal_path, operator, notes, ground_truth_method
```

Record an explicit `healthy` state rather than inventing a fake defect coordinate. Keep calibration and acquisition code versions with the data.

### Split policy

- Development split: hold out entire defect locations.
- Stronger split: hold out entire specimens.
- Final blind test: a separate panel whose defect truth is hidden until predictions are frozen.
- Never split repeated waveforms or source/receiver channels from the same defect randomly across train and test.
- Report error-versus-measurement-budget, entropy calibration, 10/15/20 mm success, failure/abstention rate, and performance under remounting and temperature changes.

### Planner-specific requirement

Training an observation model only needs `(experiment, signal, truth)` rows. Evaluating an adaptive planner offline requires a counterfactual measurement bank: for every hidden defect state, record every candidate experiment the planner might choose. That lets random, grid, and ARGUS policies query the same physical response table without rerunning the specimen. After offline policy selection works, test the true online loop on blind panels.

## Recommended staged program

1. Use the downloaded LMSD data as a real multistatic response and adapter test.
2. Use the downloaded TU GFRP data for microphone-domain feature transport, real-reference OOD monitoring, and specimen-held-out detection.
3. Use the downloaded Bologna pair for simulation-transfer and measured few-shot localization studies.
4. Collect one healthy panel and ten reversible-defect positions using the exact ARGUS low-frequency laptop/mobile protocol.
5. Expand to three panels and at least twenty positions with specimen-held-out evaluation.
6. Add a selected Open Guided Waves subset for temperature/environmental diversity rather than downloading the full collection prematurely.
7. Only then collect destructive or expensive true cavity/delamination specimens and fine-tune/calibrate the posterior.
