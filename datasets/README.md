# ARGUS datasets

`generated/` is intentionally empty in source control. Create a domain-randomized physics dataset with:

```bash
python scripts/generate_dataset.py --samples 2500
```

Each compressed NPZ contains simulator/experiment inputs and measured signal-feature targets for the optional learned forward-response surrogate. Generated data and user WAV files can contain sensitive physical measurements; review them before sharing.

For real measurements, ARGUS includes a checksum-verifying downloader and adapter for the CC BY 4.0 KU Leuven LMSD plate dataset:

```bash
python scripts/download_lmsd_dataset.py --profile all
python scripts/prepare_lmsd_dataset.py
```

See [the real-data guide](../docs/REAL_DATA_GUIDE.md) for suitability, leakage-safe splits, other public sources, and a complete ARGUS-specific laboratory collection protocol.
