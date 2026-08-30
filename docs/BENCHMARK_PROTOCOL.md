# Benchmark protocol

The benchmark answers: under structural and metrology uncertainty, how many measurements and how much motion do competing policies require under one declared reliability criterion?

Nine policies run against paired deterministic seeds: random, uniform grid, greedy coverage, legacy ARGUS, information gain, Bayes risk, dual control, receding horizon, and full ARGUS NEO. Each has the same panel, hidden scenario, maximum budget, simulator, and criterion:

```text
structural confidence ≥ 0.72
90% credible-region area ≤ 0.08
OOD state is neither OUT_OF_DISTRIBUTION nor ABSTAIN
at least two observations
```

Metrics include localization error, entropy, credible area, measurements, simulated acquisition time, movement, energy proxy, calibration error, false-confidence/abstention/success/criterion rates, compression ratio, and computation time. Acquisition time adds each step's movement once. Failures are retained.

Summary tables report mean, median, sample standard deviation, bootstrap 95% interval, and sample size. Full NEO is paired against random, uniform, and legacy ARGUS by seed; Wilcoxon and paired t-test p-values are reported only when at least two pairs exist. A p-value is not treated as effect size or evidence of real-world validity.

Commands:

```powershell
python scripts\neo_benchmark.py --cases 2 --max-experiments 5
python scripts\neo_benchmark.py --ablation --cases 2
python scripts\run_neo_demo.py measurement_compression --cases 4
```

Quick runs are pipeline checks, not publication-scale evidence. Increase cases before inference and report every seed/configuration.

