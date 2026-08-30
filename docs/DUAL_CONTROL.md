# Diagnostic–calibration dual control

Conventional active inspection assumes every acquisition should reduce defect uncertainty. That can amplify false confidence when the instrument, coupling, timing, pose, or propagation model is uncertain. ARGUS NEO treats calibration as a competing physical action.

At each loop, `AdaptiveDualControlManager` receives structural uncertainty, metrology contributions, model trust, OOD score, calibration count, and the best diagnostic value. It computes:

```text
V_cal = diminishing_return · [U_metrology · (0.70 + 0.30(1-trust)) + 0.35 OOD]
V_diag = diagnostic_separation · U_structural · trust
```

Decision-theoretic mode chooses calibration when `V_cal - V_diag` exceeds a configurable margin. Threshold mode is retained for experiments. Once the posterior is concentrated enough, a verification action challenges the leader before a confident stop.

Calibration types are direct path, coupling repeat, frequency sweep, phone-pose recalibration, and microphone-level check. A calibration response updates nuisance Gaussians but contributes a uniform structural likelihood: it cannot masquerade as defect evidence. Updated velocity, timing, and noise means are synchronized into the inference forward model, so calibration changes subsequent physical experiment predictions.

Every switch records the action type, dominant metrology term/share, values, margin, calibration type, uncertainties before/after, measurement quality, and next recommendation in SQLite and the evidence ledger. Calibration value diminishes with repeat count to prevent an endless calibration loop.

Limitations: velocity and timing remain partially confounded; factorized Gaussian updates understate correlation; commodity-sensor quality values are proxies. A target system should learn priors from healthy references and validate switching costs experimentally.

