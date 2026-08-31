# External experimental data

External datasets are downloaded locally and excluded from Git. ARGUS supports these measured sources:

| Local directory | Dataset | License | Selected profile |
|---|---|---|---|
| `lmsd2021/` | [LMSD 2021](https://zenodo.org/records/11033677) | CC BY 4.0 | Complete 171 MB CFRP FRF set |
| `tud_gfrp_2026/` | [TU Darmstadt GFRP acoustic data](https://tudatalib.ulb.tu-darmstadt.de/items/33756af4-eb6d-4156-8708-a41cbed33e7b) | CC BY 4.0 | 2,568 unaugmented microphone taps; raw Soundbook export optional |
| `ae_impact_2024/` | [Bologna AE impact localization](https://zenodo.org/records/10875042) | CC BY 4.0 | Forty simulation MAT files and nine measured CSV files |

Each downloader writes `argus_manifest.json`, downloads through the official repository API, and checks the repository-published MD5 before accepting a file.

## LMSD 2021

- Dataset: <https://doi.org/10.48804/GDE9TW>
- Record: <https://zenodo.org/records/11033677>
- Data license: CC BY 4.0
- Plate: 600 × 600 × 4 mm CFRP
- Measurements: complex frequency-response functions from known hammer/accelerometer nodes
- Labels: known nodes containing point or elongated added masses

Download the metadata plus all NPZ measurements (about 171 MB):

```powershell
python scripts\download_lmsd_dataset.py --profile all
```

Convert the measured FRFs into the same 24-input/15-response-feature contract used by the ARGUS forward surrogate:

```powershell
python scripts\prepare_lmsd_dataset.py
```

This creates `datasets/generated/lmsd_forward.npz`. The added masses reproduce scattering but are not literal cavities or delaminations. Treat the adapted dataset as real-response transfer/validation data, not as proof that its labels are interchangeable with every ARGUS defect type. Preserve the DOI and CC BY 4.0 attribution in any derived publication or model card.

## Selected sim-to-real datasets

```powershell
python scripts\download_sim2real_datasets.py
python scripts\prepare_tud_gfrp_dataset.py
python scripts\fit_sim2real_models.py
python scripts\prepare_ae_impact_dataset.py
python scripts\benchmark_ae_sim2real.py
```

The default download deliberately uses the 50.9 MiB unaugmented TU waveform archive instead of duplicating all publisher-provided augmented train/test sets. Pass `--include-tud-raw` only when the 560 MiB unsplit Soundbook export is required. Do not commit external or derived data. Preserve each record URL, license, and authorship in publications and model cards.
