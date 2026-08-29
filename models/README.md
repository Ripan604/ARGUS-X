# ARGUS model artifacts

ARGUS runs with its interpretable physics likelihood when no checkpoint is present. `python scripts/train_model.py` creates an optional `forward_surrogate.pt` plus transparent training metadata. The 58 KB reference checkpoint and JSON metrics are intentionally small enough to share; other generated checkpoints remain excluded from Git.
