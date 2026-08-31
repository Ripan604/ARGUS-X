# ARGUS datasets

`generated/` is intentionally empty in source control. Create a domain-randomized physics dataset with:

```bash
python scripts/generate_dataset.py --samples 2500
```

Each compressed NPZ contains simulator/experiment inputs and measured signal-feature targets for the optional learned forward-response surrogate. Generated data and user WAV files can contain sensitive physical measurements; review them before sharing.

For real measurements, ARGUS includes checksum-verifying downloaders and adapters for three CC BY 4.0 plate datasets:

```bash
python scripts/download_lmsd_dataset.py --profile all
python scripts/prepare_lmsd_dataset.py
python scripts/download_sim2real_datasets.py
python scripts/prepare_tud_gfrp_dataset.py
python scripts/prepare_ae_impact_dataset.py
```

The TU Darmstadt adapter produces measured 16 kHz microphone features. The Bologna adapter preserves paired simulated/experimental 250 kHz impact-localization features. Derived NPZ files and downloaded waveforms stay local and Git-ignored. See [the sim-to-real report](../docs/SIM2REAL_REPORT.md) and [the real-data guide](../docs/REAL_DATA_GUIDE.md) for provenance, suitability, leakage-safe splits, metrics, and the remaining physical-validation gap.
