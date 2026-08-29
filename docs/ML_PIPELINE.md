# ML and signal pipeline

## Default observation path

The reliable demo path is interpretable physics inference:

1. Generate the known direct response for the chosen source/receiver geometry from the object calibration.
2. Subtract it from the acquired response.
3. Matched-filter the residual with the emitted waveform.
4. For every defect cell, calculate `t = system_delay + (d(source, cell) + d(cell, receiver)) / wave_velocity`.
5. Sample the matched-filter response near that delay and turn the scores into a stabilized likelihood grid.
6. Apply `posterior ∝ prior × likelihood` and normalize.

This produces the elliptical evidence geometry expected from bistatic time of flight. New source/receiver placements intersect different ellipses, so evidence fuses spatially.

## Feature vector

ARGUS exposes RMS, peak, crest factor, zero-crossing rate, spectral centroid/bandwidth/rolloff/entropy, dominant frequency, three normalized band energies, envelope peak time, decay time, robust noise estimate, and SNR. These were chosen because they represent amplitude, timing, spectral redistribution, resonance, and noise without indiscriminately adding high-dimensional audio features.

## Learned forward surrogate

`scripts/generate_dataset.py` domain-randomizes panel dimensions, material velocity/attenuation/resonance, noise, defect position/size/severity/type, waveform, band, source/receiver geometry, and drive. `scripts/train_model.py` trains a compact PyTorch MLP to predict response features from the physical state and experiment. It uses seeded 70/15/15 splits, standardized inputs/targets, AdamW, Smooth L1 loss, early stopping, CPU/GPU selection, and checkpoint metadata.

The learned model is optional. The application deliberately falls back to physics inference when no checkpoint exists; a missing or weak neural model cannot break the demo.

The checkpoint metadata records held-out standardized MAE plus physical-unit MAE and R² for every response feature. Inspect `models/forward_surrogate.json`; do not summarize model quality from aggregate loss alone. The saved 3,000-sample seed-23 run has mean per-feature R² 0.409: SNR, RMS, and peak amplitude are predicted well, while dominant frequency and envelope timing expose clear improvement targets.

## Calibration and transfer limits

The simulator is not a finite-element solver. Real panels require measured reference responses, sensor coupling control, speed/attenuation calibration, and likely simulation-to-real fine-tuning. The current physical WAV path demonstrates the software contract but has not been validated as a safety-relevant NDT instrument.
