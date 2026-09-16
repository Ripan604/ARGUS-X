# ARGUS: nuisance-marginal arrival-time experiment design

## What was developed

The new **experimental** planner estimates how informative a candidate acoustic
arrival time would be about *regions of possible defect locations*, after
accounting for uncertain timing, wave velocity, source placement, and receiver
placement. It integrates into the existing acquisition/inference/control loop;
it is not a new trained neural network and does not require an API service.

This is an implemented research extension, not a claim that Bayesian design or
nuisance marginalization was invented here. It is disabled by default because
the paired evaluation does not establish reliable accuracy superiority.

To use it: open ARGUS, select **Nuisance-aware design (experimental)**, and start
a session. In **Reasoning**, inspect the arrival-time information in bits,
nuisance penalty, numerical quadrature check, and represented posterior mass.
In **Research**, inspect the recorded comparison, including losses and failures.
The API equivalent is `POST /sessions` with
`"enable_nuisance_aware_design": true`; the option survives session restoration.

## Why this is a substantive change

The established planner's information score is normalized posterior entropy
times a response-separation proxy and model trust. Its counterfactual signatures
can include delay and phase transformations of the same delay. Such signatures
are useful heuristics, but their weighted separation is not an information
quantity in bits. Moreover, the selected five spatial modes represent only
individual cells before their probabilities are renormalized.

The extension changes the design model, not the displayed confidence:

1. It assigns **every posterior cell** to the nearest representative in physical
   metres. The resulting spatial regions preserve all posterior mass.
2. It retains within-region spread in source-to-cell-to-receiver path length,
   rather than pretending that each region is a point with a certain delay.
3. It propagates the current nuisance posterior into arrival-time variance.
4. It integrates a Gaussian-mixture mutual information using deterministic
   Gauss-Hermite quadrature, with a numerical convergence diagnostic.
5. It supplies the resulting utility and mean-response separation to the
   existing constrained multiobjective planner. Waveform utility, cost,
   repetition penalties, calibration control and the baseline guard remain.

The planner never reads sealed simulator truth. Truth is used for synthetic
acquisition and, separately, for reporting localization error.

## Mathematical model

Let grid-cell position be x_i in metres, posterior mass p_i, candidate source s,
receiver r, and region R_k. Define the bistatic path length

`L_i = ||x_i - s|| + ||x_i - r||`.

Region weight is `w_k = sum_{i in R_k} p_i`, and the conditional weights are
`p_i / w_k`. All quantities below use these conditional weights. With timing
mean b and wave-speed mean v, the regional arrival mean is

`mu_k = b + E_k[L] / v`.

The approximate variance is the sum of five terms:

`sigma_k^2 = Var_k[L]/v^2 + sigma_measurement^2 + sigma_timing^2`

`             + E_k[L^2] sigma_velocity^2/v^4 + sigma_pose,k^2`.

The source and receiver pose terms use first-order distance gradients, scaled
by the physical width/height and the normalized-coordinate nuisance second
moments. At a coincident probe/cell, where the derivative is undefined, the
implementation substitutes a conservative squared-panel-diagonal sensitivity.
The source and receiver errors are assumed independent and isotropic in
normalized coordinates. The scalar pose bias has no direction, so its square
is included in the second moment; this is a modelling assumption.

The measurement floor is `1.5e-8 + (3 / sample_rate)^2 / 3` seconds squared:
the existing forward-model floor plus an approximate matched-filter sampling
neighbourhood. It is **not** learned sensor calibration, a waveform-specific
timing bound, or a measured instrument specification.

The observation model is `Y | K=k ~ Normal(mu_k, sigma_k^2)`. The utility is

`I(K;Y | experiment) = sum_k w_k integral f_k(y) log2[f_k(y)/sum_j w_j f_j(y)] dy`.

This targets the **coarsened regional variable K**, not exact cell location,
damage type, severity, or the complete waveform. A Gaussian moment match is
also not the exact original mixture of all cell/nuisance responses. Therefore
the mathematical information identity does not make the whole forward model
exact or establish posterior coverage.

Quadrature uses 24 and 48 nodes, escalating to 96 when their difference exceeds
0.002 bits. Log-sum-exp avoids direct mixture underflow. Diagnostics expose the
raw estimate, numerical clamp to `[0, H(K)]`, node count and last-order
difference. The difference is a useful convergence check, **not a rigorous error
bound**. Tests compare the estimator with independent adaptive integration.

The old score field remains a dimensionless compatibility value:
`information_bits / max(log2(number_of_regions), 1) * model_trust`.
Only the separate `information_bits` field is shown as bits. The UI does not
relabel decision confidence as accuracy or change the posterior to look better.

## What the nuisance penalty means

The diagnostic compares information with the nuisance variance terms removed
against information with them included. The nonnegative penalty is
`max(0, nominal_information - nuisance_information)`; the signed change is
reported separately. Heteroscedastic variances themselves can distinguish
regions, so information is not guaranteed to decrease under arbitrary
region-dependent nuisance changes. The tests assert monotonicity only for
common additive noise, where that expectation is appropriate. This is not a
worst-case ambiguity-set guarantee.

## Relation to primary research

- Bartuska, Espath and Tempone develop Bayesian design with nuisance uncertainty
  using small-noise approximations. ARGUS instead uses a finite scalar
  arrival-time mixture with deterministic integration; the underlying principle
  of marginalizing nuisance parameters is established prior work.
  [Paper, 2022; revised preprint 2023](https://arxiv.org/abs/2112.06794).
- Go and Isaac study robust expected information gain over KL-divergence
  ambiguity sets. ARGUS does not implement their robustness criterion and
  should not claim their guarantees.
  [Paper, UAI 2022](https://arxiv.org/abs/2205.09914).
- Raorane et al. apply Bayesian optimal sensor placement to acoustic-emission
  localization with sensor clusters in isotropic plates, including experimental
  validation. Thus acoustic localization plus information-based placement is
  already prior art. ARGUS's narrower implementation concerns sequential
  source/receiver interrogation, live posterior compression, nuisance-aware
  scalar design, and inspectable numerical/evidence reporting.
  [Paper, MSSP 2024](https://doi.org/10.1016/j.ymssp.2024.111342).

The potentially distinctive object is the *specific integrated inspection
workflow and its engineering implementation*. The present work neither proves
that combination is legally novel nor demonstrates a technical advantage over
commercial inspection leaders. A method name, visual polish, or passing tests
cannot establish either claim.

## Evidence and decision

See [the frozen protocol and complete interpretation](RESEARCH_EVALUATION.md).
The 80 completed synthetic runs are 20 held-out seeds, two contexts, and two
methods, each with eight acquisitions and 24 shared candidate opportunities.
Mean localization error was 15.12 versus 15.10 mm nominally, and 180.14 versus
146.56 mm under combined mismatch/noise, for established versus experimental.
Both paired 95% bootstrap intervals include zero. Both methods failed the
30 mm threshold in 17/20 stress cases. No execution failure occurred.

Consequently, the extension remains opt-in. Its presently supported benefit is
a more explicit, auditable observation-level design calculation, not proven
better localization. Next experiments should focus on physical timing/noise
calibration, joint structure/nuisance likelihood validation, and specimen-held-
out testing. Further tuning must use development data and a new reserved test
set, not silently reuse this report's test seeds for an efficacy claim.

## Implementation and reproducibility

- Method: `backend/app/active_learning/nuisance_design.py`.
- Integration: `backend/app/active_learning/neo_planner.py`.
- Numerical, physical-coordinate and persistence tests:
  `backend/tests/test_nuisance_design.py`.
- Paired evaluation: `scripts/research_validation.py`.
- Raw evidence: `research_results/nuisance_design_validation.json`.
- Compact in-app publication: run `python scripts/publish_research_report.py`.
  Its test verifies exact equality with the raw summary and its SHA-256 hash.
- Spatial UI: `NarrativeTwin`, `SpatialWorld`, and geometry tests. Relief height
  is relative posterior probability, not physical defect depth. R90 uses the
  physical panel dimensions; moving excitation rings are illustrative.

No additional training, field acquisitions, hardware certification, or patent
filing was performed as part of this extension.
