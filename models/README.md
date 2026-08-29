# ARGUS model artifacts

ARGUS runs with its interpretable physics likelihood when no checkpoint is present. `python scripts/train_model.py` creates an optional `forward_surrogate.pt` plus transparent training metadata. The 58 KB reference checkpoint and JSON metrics are intentionally small enough to share; other generated checkpoints remain excluded from Git.

`lmsd_surrogate.json` records the scenario-held-out experiment on the downloaded KU Leuven data. Its mean held-out feature R² is approximately zero despite a low aggregate Smooth L1 loss, demonstrating why six physical damage configurations are useful for pipeline validation but insufficient for a deployable response model. The generated weights remain local and ignored.
