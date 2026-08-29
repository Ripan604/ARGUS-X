# External experimental data

External datasets are downloaded locally and excluded from Git. ARGUS currently supports the **LMSD 2021 Dataset for Damage Identification in Plates** from KU Leuven:

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
