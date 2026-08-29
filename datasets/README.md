# ARGUS datasets

`generated/` is intentionally empty in source control. Create a domain-randomized physics dataset with:

```bash
python scripts/generate_dataset.py --samples 2500
```

Each compressed NPZ contains simulator/experiment inputs and measured signal-feature targets for the optional learned forward-response surrogate. Generated data and user WAV files can contain sensitive physical measurements; review them before sharing.
