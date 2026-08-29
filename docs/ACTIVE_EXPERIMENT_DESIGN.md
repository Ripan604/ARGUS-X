# Adaptive Physical Experiment Planner

Let the current defect-location belief be `p(z | D)`. For candidate experiment `e`, ARGUS predicts a compact response signature for each of the top-K location hypotheses:

```text
s(z,e) = [time_of_flight, log_scatter_gain, sin(phase), cos(phase)]
```

Pairwise signature distances are converted into bounded Gaussian-overlap discrimination values. With normalized top-hypothesis weights `w`, the disagreement proxy is:

```text
D(e) = Σᵢ Σⱼ wᵢ wⱼ [1 − exp(−||sᵢ − sⱼ||² / 2)]
```

The expected information-gain proxy is `H(p) × represented_mass × D(e)`. This is not labeled as exact Bayesian optimal design: it is a fast, documented approximation that can score dozens of physical experiments interactively.

The final score is:

```text
score(e) = α EIG_proxy(e)
         + β hypothesis_disagreement(e)
         + κ uncertainty_coverage(e)
         − γ experiment_cost(e)
         − δ repetition_penalty(e)
```

Experiment cost combines excitation energy and movement from the previous source position. Repetition checks proximity in both source location and frequency. The UI exposes all component scores for the top five candidates.

The planner stops when confidence exceeds its threshold, normalized entropy falls below its threshold, or the experiment budget is exhausted. A user can still submit an explicitly specified measurement after automatic termination.

## Why counterfactual disagreement matters

Plain uncertainty sampling would probe wherever the heatmap is bright. ARGUS instead asks: *if region A were the defect, what would this experiment return; if region B were the defect, how different would the response be?* It chooses the physical intervention that makes those futures easiest to tell apart.
