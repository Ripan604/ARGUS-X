# Frozen measured guided-wave path-replay protocol

8 October 2026. Written before calculating the selected banks' damage indices
or evaluating path policies. This is a source-controlled prospective analysis
protocol, not an external preregistration or a new physical acquisition.

## Data and evaluation units

Use the complete 18-bank, protocol-index subset of OGW dataset 2 described in
OPEN_GUIDED_WAVES_SOURCE_AUDIT.md. The native apparatus uses 40 kHz, five-cycle
excitation, 10 MHz sampling and 66 actually recorded unordered transducer paths
on one 500 by 500 mm CFRP plate. The four published positions are removable
surface-mounted reference scatterers. They are not manufactured internal defects.

Healthy thermal cycle 1 supplies the reference waveform at nominal 20/40/60 C.
Healthy cycle 2 is reserved for test and never supplies a fitted noise level,
threshold or calibration. Hold out a whole reference position, with every
temperature of that position kept out of training. Thus there are four damage
position folds. Paths and temperatures are dependent measurements on one plate.

Analyse two fixed operating contexts separately: use the healthy baseline at
the same nominal chamber setpoint, or use the 20 C baseline at every test
temperature. Matching chamber setpoints does not imply equal surface temperature.
The first is a condition-matched baseline study; it is not unseen-temperature
generalization. The second exposes temperature confounding.

## Observations and declared model

Use the entire recorded catch window, de-mean each waveform and compute
`DI = 1 - abs(Pearson(reference, catch))`. Do not align a waveform using hidden
damage position or select a successful frequency/window after evaluation.
Invalid or zero-energy paths consume the requested opportunity and are reported.

The spatial feature is the established RAPID elliptical kernel:

```text
ratio(z,path) = (distance(source,z)+distance(z,receiver)) / path_length
K = max(0, (beta-ratio)/(beta-1)), beta = 1.05
```

Fix a 50 by 50 grid of 10 mm cell centres over the entire plate. Fit one
amplitude coefficient bounded to [0,1] to `DI ~= amplitude*K` using only the other
three reference positions and all three training temperatures. Use the pooled
training residual RMS, with a fixed 0.02 floor, as the Gaussian observation
standard deviation. Do not change beta, grid, floor or observation definition
to match the held-out labels. This scalar spatial observation model does not
identify a physical defect mechanism or a material wave speed.

Start with 0.5 prior mass on a healthy hypothesis of mean DI zero and 0.5 evenly
distributed over location cells. Update normalized log weights using the declared
Gaussian likelihood after each revealed path. Conditional path independence and
the elliptical mean model are approximate; their posterior weights are not
certified probabilities. The fixed 0.5 damage-mass threshold is a study decision
rule, whose errors on independent healthy cycle 2 must be reported. Exact ties
within 1e-12 abstain rather than asserting that the initial prior is a detection.
Unsupported complete-bank schemas fail the bank before any policy; all such
failures remain in the study report and invalidate a completed-comparison claim.

## Equal-budget policy comparison

All sequential policies use the same fitted model and inference. They may access
training observations and reference waveforms, but only the selected damaged/test
path may be revealed. Never rank paths from unused held-out waveform features.
The recorded bank is queried without inventing missing or reciprocal responses.

1. Cyclic: canonical ascending recorded-pair order.
2. Geometry spread: longest path first, then maximal minimum kernel cosine
   distance from already selected paths. This uses geometry only.
3. Training static: rank by DI variance over development positions/temperatures.
4. Seeded random: 16 fixed random permutations per case, seed 20261008.
5. Adaptive disagreement: maximize posterior-weighted variance of predicted DI
   over the remaining paths. This is a predictive-disagreement proxy, not exact
   mutual information or the core controller's scalar arrival-risk policy.

No path is reused. Budgets are 1,2,4,8,12,16,32 recorded paths. Each revealed path
costs one opportunity; physical actuator/movement costs are not inferred from
file size. The random order repetitions quantify policy variability, not new
physical tests. Include the same model with all 66 paths and classical full-bank
RAPID as cost-labelled full-bank references, not equal-budget competitors.

## Outputs and claims

Record each selected path, DI or rejection, model-state transition, MAP error,
90% conditional-location containment radius, damage weight and decision, query
count, runtime and numerical failure. Include every failed or poor case; do not
stop collecting because a location estimate looks correct. Report complete
error-versus-budget curves, 25/50/100 mm success and decision false positives
on healthy cycle 2. Aggregate random orders within each physical condition
before comparing policies. Retain per-position/temperature/context results.

No specimen-generalization interval will be formed from four positions on one
plate. There is no guarantee adaptive selection wins. The full-bank references
show whether sparse acquisition, the response model or both are limiting.
Preserve source/raw/protocol SHA-256 before and after the run and exact versions.

This is a new native-frequency offline evaluation branch using published
measured responses. It does not validate the 16 kHz apparatus, online actuator
control, the speed/timing reference selector, or a patent's novelty.

The RAPID construction is established prior work, for example
[Van Velsor, Gao and Rose (2007)](https://pure.psu.edu/en/publications/guided-wave-tomographic-imaging-of-defects-in-pipe-using-a-probab/)
and [the published algorithm description](https://pmc.ncbi.nlm.nih.gov/articles/PMC10707141/).
