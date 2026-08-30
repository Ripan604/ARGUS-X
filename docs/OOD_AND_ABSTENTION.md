# OOD detection and abstention

ARGUS separates model uncertainty, posterior uncertainty, OOD score, and decision confidence. The OOD layer uses two independent families:

1. a robust standardized residual distance, using median/MAD history once enough residuals exist;
2. ensemble disagreement plus conformal nonconformity against calibration scores. Conformal scoring is withheld until ten reference scores exist so a tiny discrete calibration set cannot create a spurious tail claim.

Acquisition quality adds a conservative penalty. The maximum method score is combined with that penalty and mapped to `NOMINAL`, `CAUTION`, `OUT_OF_DISTRIBUTION`, or `ABSTAIN`. The corresponding confidence caps are 1.0, 0.68, 0.38, and 0.20. An OOD/ABSTAIN stop never produces a high-confidence defect conclusion; it requests calibration, verification, or escalation to a reference method.

Fault injection covers clipping, missing samples, noise, dropout, bias, position error, coupling loss, bad timestamp metadata, and packet corruption. Finite-value, silence, plateau clipping, motion/placement, and signal-quality checks can reject or down-weight observations before Bayesian update.

Limitations: the residual embedding has four interpretable signature components and the default calibration corpus is small. OOD means “outside this model's empirical envelope,” not “the object is unsafe” and not proof that a defect exists.

