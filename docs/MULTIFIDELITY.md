# Multi-fidelity digital twin

All digital-twin implementations follow `ForwardModel.predict(experiment, latent_state)` and expose level, cost, supported band/material, uncertainty, and identity metadata.

| Level | Current implementation | Intended use |
|---|---|---|
| 0 | Analytical delay/log-gain/phase signature | Broad posterior, fast screening |
| 1 | Physics-inspired waveform/signature simulator | Close hypotheses and normal live planning |
| 2 | Optional CPU MLP ensemble and registry | Offline-trained feature prediction when domain/trust allow |
| 3 | NPZ/CSV/WAV counterfactual bank | Replayed measured data or imported solver results |

`MultiFidelityController` uses structural concentration, rivalry, frequency support, model trust, and discrepancy. Low trust can force the physics level or abstention rather than silently using a surrogate. The selected level and rationale appear in every recommendation and ledger entry.

The online discrepancy model stores residual targets keyed by frequency, path length, TX/RX geometry, and session. Ridge correction produces a corrected prediction and uncertainty; recent standardized residual RMS maps to model trust. The UI exposes simulation, last measurement residual, correction, residual after correction, cache statistics, and trust through the ARGUS Brain/model endpoint.

Forward queries are deterministically keyed by model identity, latent state, experiment, and nuisance state and stored in bounded LRU caches. Cache hit/miss/eviction counts are auditable. The current level-1 model remains a reduced wave model, not FEM, and level-2 is optional: the system remains functional without a checkpoint.

