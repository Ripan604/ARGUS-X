# Scientific model

ARGUS NEO is a local research prototype for sequential experiment design. Its primary evidence path is a seeded, physics-inspired simulator. It is not a finite-element solver, a calibrated NDE instrument, or a structural-safety decision system.

## State and observation model

The live approximation separates structural state `Z`, nuisance/metrology state `η`, and model discrepancy `δ`:

```text
p(Z, η, δ | D) ≈ p_grid(Z | D, η, δ) q_factorized(η | D) q_online(δ | residual history)
```

`Z` contains a single dominant defect location grid plus approximate radius, severity, and type moments. `η` contains bounded Gaussian propagation velocity, attenuation, timing offset, source/receiver coupling, gain, noise, pose errors, and a temperature proxy. `δ` is a frequency/path/geometry-conditioned online ridge residual model. This factorization is a CPU-usable approximation, not an exact joint MCMC posterior.

For experiment `e`, the simulator combines a delayed attenuated direct path, a defect-scattered bistatic path, defect-dependent polarity, damped ringing, drift, and seeded noise. The diagnostic likelihood subtracts the direct-path baseline, correlates the residual with the excitation, and samples correlation energy at each cell's predicted delay:

```text
L(z; y,e) ∝ exp(τ(SNR) · scaled_matched_filter(y,e,z))
p_next(z) ∝ p(z) · L(z; y,e)^w_quality
```

The evidence exponent is derived from signal, coupling, placement, repeatability, and clipping proxies. Rejected data has weight zero. This prevents silence, corrupted packets, and repeated low-quality measurements from creating unlimited confidence.

## Uncertainty quantities

- Structural uncertainty combines normalized entropy, 90% highest-posterior-density area, competing-mode ambiguity, and severity relative spread.
- Metrology uncertainty is a weighted normalized sum of nuisance standard deviations.
- Model uncertainty is residual-model predictive uncertainty.
- OOD score is a conservative combination of robust residual distance, conformal nonconformity when enough calibration samples exist, ensemble disagreement, and acquisition-quality penalty.
- Decision confidence is structural confidence multiplied by model trust and capped by OOD state.

These quantities have defined computations but are not probabilities of safety. Simulation-based calibration reports empirical coverage, reliability bins, ECE, and posterior-rank histograms rather than relabeling a heuristic score as certified confidence.

## Counterfactual planning

For every feasible experiment, the planner predicts response distributions under the top structural hypotheses while propagating nuisance variance. It computes Gaussian Jensen–Shannon approximation, Bhattacharyya distance, symmetric KL, predictive variance separation, and worst-pair separation. Objectives are information gain, Bayes-risk reduction, worst-case ambiguity, measurement compression, or a configurable multiobjective score.

Short-horizon planning is bounded beam reranking for `H=1..3`; it is not a solved POMDP. Multi-fidelity selection uses a cheap analytical signature or the physics signature model, and defines extension points for a learned surrogate and imported response banks.

## Scientific invariants

Automated tests verify posterior normalization, evidence tempering, calibration uncertainty reduction, OOD confidence caps, amplitude bounds, constraint enforcement, truth sealing, paired benchmark seeds, migrations, hash-chain integrity, bundle import/export, and WebSocket protocols. Benchmark results always retain failed, abstained, and overconfident runs.

