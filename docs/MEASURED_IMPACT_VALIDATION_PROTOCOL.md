# Measured Bologna source-localization reanalysis protocol

Prepared 8 October 2026 before the new comparison. This is a reanalysis of
previously downloaded data, not a newly unseen specimen or a preregistration.
The historical three-neighbour pipeline and results were already visible.

The primary source is [Zenodo 10875042](https://zenodo.org/records/10875042),
DOI 10.5281/zenodo.10875042, CC BY 4.0. Use only its nine measured CSVs; exclude
all numerical MAT files and all saved model binaries. Verify each published MD5
against the current official record and retain local SHA-256 digests.

Each actual file has columns s1,s2,s3 and 5000 rows at 2 MHz. Sensor positions are
(0.05,0.95), (0.05,0.05), (0.95,0.05) m on a 1 by 1 m aluminium plate.
The source is a 250 kHz three-cycle excitation at the filename-labelled position.
The record mentions repeated tests but supplies no separate repeat axis in the
actual CSV schema. Treat this as nine position records with simultaneous channels,
not 27 independent events or independently resolved repeats.

Hold out one complete source position at a time. All channels from that position
must remain in its test fold. Compare the train-position centroid, standardized
one-neighbour and three-neighbour regressors, and a simple physical TDoA model.
The learned-feature branches use all 36 numeric per-channel features from the
existing deterministic 100-400 kHz, 1600-sample post-trigger feature extractor;
the pretrigger count is 1500. Fit StandardScaler only on training positions.
Coordinates, paths, filenames and labels never enter the feature matrix.

The TDoA branch uses the 5% envelope-energy quantile for each channel. Fit inverse
effective speed and two relative sensor offsets from training geometry only,
with speed bounds 500-7000 m/s and offset bounds +/-1 ms. Search a fixed 5 mm
grid over the complete 1 by 1 m plate for the test observation. This is a
calibrated approximation, not measured material-speed certification. It may
fail under reflections, mode dispersion or a poor arrival picker.

Retain every prediction, physical error, fold calibration, numerical failure,
source hash and runtime. Report mean/median/RMSE and 20/50/100 mm success, plus
descriptive paired differences against the centroid. Do not add synthetic noise,
augment test samples, tune neighbours/band/window/speed to test outcomes, or
select a winning method after results. Do not form specimen-generalization
confidence intervals from nine positions on one plate.

This checks measured transient source localization, not persistent internal
defect localization, the adaptive controller, or the 16 kHz physical probe.
