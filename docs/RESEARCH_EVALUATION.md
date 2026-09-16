# Independent paired synthetic evaluation

## Protocol frozen before validation

This evaluates the nuisance-aware arrival-time acquisition design against the
legacy information proxy. It does not validate a physical inspection instrument.
The independent evaluation harness is `scripts/research_validation.py`.

- Pilot seeds: 31000–31005. Validation seeds: 41000–41019. Validation seeds are
  reserved for reporting, not planner tuning. Both contexts use all 20 seeds.
- Primary outcome: physical MAP localization error in mm after exactly eight
  acquisitions on the 0.60 × 0.40 m synthetic panel, medium preset. No early stop.
- Report mean, median, p90, success ≤20 mm, failure >30 mm, abstention, rejected
  acquisitions, calibration count, entropy and runtime. A reported high confidence
  with >30 mm error is counted separately as false confidence (threshold 0.70).
- The paired effect is legacy error minus nuisance-aware error. Positive favors
  the new method. Report every seed and 10,000 paired-seed bootstrap resamples
  (percentile 95% interval; bootstrap seed 90071), including losses and ties.
- Each measurement step shares 24 public candidates: eight perimeter experiments
  and sixteen independently sampled safe geometries/waveforms. Banks depend on
  seed and step, never hidden truth or a strategy posterior. This deliberately
  isolates candidate scoring from posterior-adaptive candidate generation.
- Production inference, dual control, constraints, and model diagnostics remain
  active. Both methods use the same deterministic calibration option generator.
  Calibration can differ as a consequence of earlier observations. Horizon is one.
- Nominal: assumed and acquisition material agree. Controlled mismatch/noise:
  acquisition velocity ×1.02, attenuation ×1.04, and noise ×2; inference starts
  with nominal material. This is a combined stress context, not separate causal
  estimates for each disturbance.
- Truth is generated independently of planner execution. Acquisition randomness
  is reset using `SeedSequence([seed, step, 202])` for each step; candidates use
  `SeedSequence([seed, 101])`. This prevents different calibration/diagnostic
  histories from shifting subsequent random-number streams. All diagnostic bank
  signals have the same duration. Different acquisition types may transform those
  innovations differently through the unchanged simulator.
- Configuration, Python/NumPy/SciPy versions, source SHA-256 fingerprints, command,
  complete action traces and sealed reporting truth are stored in each artifact.
  Execution errors remain explicit and are excluded only from completed-pair
  statistics; their counts must accompany any claim.

Run the frozen validation:

```powershell
python scripts/research_validation.py --cases 20 --seed 41000 --steps 8 --candidates 24
python -m pytest backend/tests/test_research_validation.py
```

## Existing benchmark audit

The checked-in `research_results/neo_benchmark_quick.json` contains only seeds
100 and 101 and five acquisitions per policy. Every policy used the entire
budget; none met its stopping criterion. This artifact therefore demonstrates
no measurement compression. Mean localization errors include uniform grid
15.95 mm, legacy existing ARGUS 22.10 mm, full NEO 21.70 mm, and the named
information-gain policy 69.00 mm. Two cases cannot establish superiority.

The old matrix uses different candidate counts for full NEO and other policies,
and its paired statistical comparisons concern measurement count rather than
localization error. Before this research change, the named information score was
normalized posterior entropy multiplied by a response-separation proxy. These
are useful engineering heuristics but do not establish posterior mutual
information or a calibrated information value.

## Limits of interpretation

The simulator includes a single synthetic defect, simple propagation and
scattering, Gaussian noise and drift. Held-out random seeds are not independent
field datasets or unknown material families. The fixed candidate bank is a
controlled ablation rather than the full production candidate-generation policy.
Eight-step fixed-budget results cannot support measurement-compression claims.
Information values from the proposed Gaussian arrival-time surrogate are model
quantities; localization, posterior calibration, and physical defect detection
must be assessed separately. Model-matched improvements would not demonstrate
general sim-to-real transfer.

## Results

### Legacy pilot, separate from held-out validation

`research_results/nuisance_design_pilot_legacy.json` records all twelve legacy
pilot runs (six seeds in each context). Every run completed eight acquisitions,
with no execution errors or rejected signals. The nominal mean/median/p90 were
65.83/18.23/165.97 mm; five of six cases were within 30 mm, while seed 31001
failed at 311.44 mm and abstained. Under combined mismatch/noise, mean/median/p90
were 142.31/127.26/241.93 mm; all six cases exceeded 30 mm. None of those stress
cases abstained, although none crossed the 0.70 confidence threshold either.

The pilot exposes large localization failures hidden by the two-case quick
demonstration. It provides no comparison with the proposed method, and no
parameters were selected against the reserved validation seeds.

### Held-out comparison, completed

`research_results/nuisance_design_validation.json` contains all 80 completed
runs. No execution failures or rejected measurements occurred. Recorded source
fingerprints were unchanged during the run. Each context has 20 complete pairs.

| Context | Method | Mean error mm | Median mm | P90 mm | Within 20 mm | Above 30 mm |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Nominal | Established proxy | 15.12 | 13.85 | 23.80 | 17/20 | 1/20 |
| Nominal | Nuisance-aware | 15.10 | 15.20 | 20.43 | 17/20 | 1/20 |
| Mismatch + noise | Established proxy | 180.14 | 191.93 | 285.29 | 1/20 | 17/20 |
| Mismatch + noise | Nuisance-aware | 146.56 | 126.36 | 275.54 | 3/20 | 17/20 |

The nominal paired mean advantage is 0.014 mm, 95% paired bootstrap interval
[-2.24, 2.94] mm: three wins, seven losses, ten ties. The stress-context mean
advantage is 33.58 mm, interval [-30.62, 95.83] mm: ten wins and ten losses.
Positive advantage means lower error with nuisance-aware design. **Both
intervals include zero; superiority is not established.** The lower stress
mean is descriptive, not evidence of reliable sim-to-real transfer.

Both methods exceeded 30 mm in 85% of stress cases. The proposed method's
worst stress error was 426.96 mm (seed 41011); its paired disadvantage there
was 220.46 mm. Reporting this failure is essential to interpreting the mean.
No run crossed the defined 0.70 false-confidence threshold, but that does not
mean failures were identified: stress abstention was 1/20 for the established
method and 0/20 for the extension. Thresholded false-confidence and abstention
are different measurements.

Mean eight-step computation time on this machine was 0.64 versus 0.94 seconds
nominally and 0.68 versus 1.01 seconds under stress. These timings are indicative
of this small fixed-bank experiment, not a portable throughput guarantee.

Decision: retain the established production default; expose the new method as
an explicit research opt-in. A more principled surrogate information calculation
is valuable for auditability, but the experiment does not show a reliable
localization improvement. The frozen artifact is preserved unchanged; future
modifications must use a new held-out set for confirmatory testing.

The Research view's compact report is generated from this exact artifact by
`scripts/publish_research_report.py`, with a source SHA-256 and equality test.
