# Fundamental upgrade: reference-conditioned acquisition and decisions

**Updated:** 9 October 2026. Implemented and tested experimental code, with measured development and separate confirmation evidence; negative findings retained.

## What changed and why

Real guided-wave recordings showed that temperature, source timing and waveform drift can resemble structural change. The initial model also applied an approximate spatial response as if its uncertainty were well described. The new chain treats reference validity, nuisance correction, spatial inference and anomaly decisions as separate operations that must agree before an unsupported signal can become an engineering claim.

1. Fit a healthy reference transport using only known healthy waveform anchors and actual surface temperatures. Record a per-path residual scale and reject non-identifiable or inaccurate fits.

2. For a requested path, align source timing from its captured electrical pitch. Predict the receiver reference before looking at the receiver response; a possible damage signal cannot fit away its own discrepancy.

3. Filter the feasible path bank by healthy-reference qualification. Use per-path observation uncertainty in the experimental adaptive disagreement criterion.

4. Compare accumulated discrepancy with complete healthy executions of that same bound controller. Use one maximum per whole trajectory, rather than pretending paths/checkpoints are independent calibration samples.

5. Withhold unsupported decisions and request qualified references. An anomaly requires a genuinely later, diverse verification with matching model/reference identities. All dispositions remain requests for review; none authorizes physical actuation or a healthy structural release.

## Physics and mathematics at the supported scope

Temperature can change guided-wave timing, phase and amplitude; the dependence varies by material, mode and direction. The model approximates this effect with bounded affine time stretch, receiver delay and gain, conditioned on measured temperature. The recorded source pitch constrains source-clock drift independently of the receiver.

```text
predicted_reference(t) = gain(T) * healthy_template(
    (t - observed_source_delay - receiver_delay(T)) / stretch(T))
corrected_DI = 1 - abs(correlation(predicted_reference, receiver))
path_variance = training_spatial_residual_variance + healthy_path_scale^2
adaptive_proxy = predicted_response_variance / path_variance
trajectory_score = max_over_fixed_checkpoints(mean(selected_DI^2 / healthy_scale^2))
reference_p = (1 + count(calibration_trajectory_max >= current_prefix_score)) / (N+1)
```

These are bounded local models and established statistical ideas, not newly discovered physical laws or a field-calibrated defect probability. Time stretching and phase compensation are discussed by [Croxford et al.](https://doi.org/10.1016/j.ultras.2009.11.002) and [Herdovics and Cegla](https://doi.org/10.1177/1475921718759272). Reference ranks relate to established [conformal prediction](https://jmlr.org/papers/v9/shafer08a.html). The candidate technical subject is their specific ordered interaction with clock-described acquisition and reference-qualified control; novelty remains unestablished.

## Healthy-only development result and qualification limits

The first 1% stretch-domain fit qualified zero of 66 paths. Its source, tests, protocol and failure report were archived exactly. The measured healthy development data showed that this domain was insufficient. A bounded 5% development revision retained every source-correlation, fit-error and identifiability threshold, and qualified 20 paths.

The mean leave-middle-temperature-out healthy discrepancy changed from 0.270896 to 0.063102, a 76.7% reduction. The diagnostic mean includes all 66 paths, including unqualified fits. It is not damage-localization accuracy. The independent healthy noise interpretation is also not established: the path scale is a development residual proxy.

Only 20 paths qualify across all three temperature anchors. Before opening any new confirmation results, the control horizon was fixed at 16, the largest declared checkpoint supported by that feasible set. All compared variants use the same 20-path bank; unsupported paths are not executed simply to fill a 32-path budget.

## Actual measured development comparison

The experiment reanalyses previously seen OGW recordings. It holds out entire reference positions from spatial fitting, but it remains an exploratory development comparison on one plate. Three old healthy second-cycle banks serve only as partial development calibration; their later descriptive results are not independent healthy test performance.

| 16-path adaptive variant | Conditional location error (mm) | Gate outcome |
|---|---|---|
| Raw global response | 159.45 | Unsupported |
| Healthy transport / global noise | 171.92 | Unsupported |
| Healthy transport / path-specific noise | 170.03 | Unsupported |

The compensated branches worsen localization relative to the raw response control. This negative finding is retained. Better healthy reference prediction does not establish that the spatial scatterer model is correct. The new compensated model remains experimental and is not enabled in production physical sessions.

The retained study contains 1,296 trajectories, including random-order repetitions and reused condition/model combinations. There is still one specimen and four reference positions, not that many independent physical trials. All source hashes remained unchanged during the final run. Controller identity/fresh-verification fixes were validated and rerun without changing predictive parameters.

## The gate refuses a claim the data cannot support

At the fixed 5% level, 19 complete healthy blocks are needed even to obtain a minimum rank of 0.05. Three available development blocks give minimum rank 0.25. All current gate outputs therefore withhold supported anomaly decisions; reuse of a calibration artifact as test is separately rejected. Zero supported alerts here means insufficient evidence, not perfect detection or a healthy panel.

The maxima account for all declared checkpoint looks under an exchangeability assumption. Cooling and warming conditions are not proven exchangeable, and temperature blocks on one plate are dependent. No field 95% false-alarm certificate or specimen-generalization guarantee is claimed.

## Separate confirmation has now been acquired and scored

The public source initially returned HTTP 403; those failed receipts and blocked scoring record remain preserved. Normal bounded public retries subsequently acquired all 29 original banks, totalling 403,070,304 bytes: 19 healthy cooling calibration blocks and ten distinct warming confirmation banks at nominal 30/50 C. All original selected-bank CRC32 and SHA-256 values were checked; the old 61 protected source/data files remained unchanged. No prior recordings, generated signals or model-weight files replaced the new captures.

The confirmation command checked exact roles, temperatures, cycles, original member identities, duplicates and original/development overlap before loading waveforms. The fitting references, qualified path set, coefficients, controller, horizon, scales, alpha and score were fixed before confirmation responses were opened. The run completed 864 trajectories and 216 controller/model calibrations, each reusing the same 19 physical healthy blocks; there were zero failed opportunities and all source hashes remained unchanged. These counts do not create 864 independent physical tests.

| 16-path adaptive variant | New conditional location error (mm) | Any-prefix supported damage alerts |
|---|---|---|
| Raw global response | 161.20 | 0 / 8 damage conditions |
| Healthy transport / global noise | 206.49 | 0 / 8 damage conditions |
| Healthy transport / path-specific noise | 215.39 | 0 / 8 damage conditions |

The separate confirmation repeats the negative localization finding. Each adaptive variant produced no supported alert in any of the eight mass/temperature conditions and no false alert on the two unique healthy confirmation banks. The healthy banks are evaluated under four held-position models. Zero healthy alerts alongside zero damage detections means the gate was insensitive, not a successful detector or a healthy-release certificate.

Seeded random orders with the two transported models yielded ten early alerts among 128 damage/order trajectories and none among 128 healthy/order trajectories; the raw random control produced none. These are repeated policy orders over the same eight damage conditions and two healthy banks, not ten independent physical detections. Final-budget-only reporting would miss those earlier alerts, so the retained report records any-prefix and earliest supported budget.

The calibration blocks are from one specimen and a cooling sweep; tests are warming conditions. Their exchangeability remains unverified. The completed acquisition does not establish a 5% field false-alarm guarantee, broader location accuracy or patent novelty. The compensated and reference-gated modes remain experimental, outside production physical acquisition. Better physical response modelling and independent specimen validation are still required.

## Implementation, verification and reproduction

The current full backend and acquisition tests passed 662 cases with one deliberate legacy-pickle skip. Frontend tests, type checking, lint and production build also passed. No probe was flashed or physically actuated for these experiments.

| Mechanism | Implementation |
|---|---|
| Immutable healthy-only warp / source alignment | backend/app/evaluation/healthy_wave_transport.py |
| Bound complete-trajectory calibration / coarse-rank refusal | backend/app/evaluation/trajectory_reference_gate.py |
| Request reference / fresh diverse verification / review | backend/app/control/reference_conditioned.py |
| Measured development or guarded confirmation | scripts/validate_reference_conditioned_replay.py |
| Separate acquisition preserving old measurements | scripts/download_ogw_confirmation.py |

```powershell
.venv\Scripts\python.exe scripts\download_ogw_confirmation.py
.venv\Scripts\python.exe scripts\fit_healthy_reference_development.py
.venv\Scripts\python.exe scripts\validate_reference_conditioned_replay.py --stage development
.venv\Scripts\python.exe scripts\validate_reference_conditioned_replay.py --stage confirmation
```

Existing evidence files are deliberately protected against overwrite. Preserve earlier outputs under a distinct dated name before intentionally repeating a study. The completed original confirmation receipt and all scored trajectories are retained. The local Research page retains the measured-data task summaries; the new fundamental experiments are documented here and in their protocols, without automatic physical activation.

## What this strengthens for technical and patent review

The implementation now makes the nuisance assumption testable, separates test response from reference fitting, limits actions to qualified references, calibrates the actual adaptive trajectory unit, binds control decisions to exact identities, and prevents stale verification or inadequate calibration from authorizing a claim. The disclosure retains the failures and acquisition gaps. These are concrete engineering improvements; patent novelty, inventive step, human inventorship and ownership still require review.

A suitable review statement is: "We measured where the model fails, improved healthy metrology and decision qualification, and tested fixed settings on separate measurements. Localization and damage sensitivity still failed, so those modes remain experimental. The next proof requires a better physical response model and a blind apparatus campaign."
