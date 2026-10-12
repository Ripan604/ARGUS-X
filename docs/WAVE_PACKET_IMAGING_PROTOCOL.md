# Healthy-calibrated wave-packet imaging development protocol

12 October 2026. This is an exploratory replacement for the whole-record scalar
damage-index observation, tested on the original 18 measured OGW banks. The
original banks and the later warming confirmation have already been inspected
by previous work. Neither is untouched confirmation for this new method. This
experiment reads only `datasets/external/open_guided_waves/`; it does not read
`open_guided_waves_confirmation/`. Settings are fixed before the new method is
applied to damaged waveforms. This is an internal development protocol, not an
external preregistration or an independent replication.

## Why change the observation

The old `1-abs(Pearson(reference, observation))` compresses 1.3108 ms of measured
receiver history to one scalar. It then weights a narrow geometric ellipse
without using the timing of residual wave packets. The proposed experiment
keeps the time axis: a baseline-subtracted response is matched to the recorded
healthy excitation, enveloped, and sampled at the predicted transmitter-cell-
receiver delay. It tests whether recovering temporal information improves
conditional localization. It does not manufacture a damage/no-damage decision.

This is established delay-and-sum imaging adapted to the repository's bounded
native-bank replay. It is an engineering control and potential fundamental
improvement, not new patent mathematics. Primary examples include
[Salmanpour, Sharif Khodaei and Aliabadi, *Guided wave temperature correction
methods in structural health monitoring*](https://doi.org/10.1177/1045389X16651155),
which uses first-packet speed and a hardware delay, baseline residual envelopes
and elliptical travel times; and
[*Damage Localization on Composite Structures Based on the Delay-and-Sum
Algorithm Using Simulation and Experimental Methods*](https://pmc.ncbi.nlm.nih.gov/articles/PMC10181622/),
which explicitly addresses anisotropic propagation and residual-envelope
backprojection. Directional calibration, source correlation, Hilbert envelopes
and delay-and-sum must not be called inventions established here.

## Source facts and timing limits

The retained [primary OGW paper](https://doi.org/10.1038/s41597-019-0208-1) reports
a 500 x 500 x 2 mm quasi-isotropic CFRP plate with the layup
`[45/0/-45/90/-45/0/45/90]S`, twelve co-bonded piezoelectric discs, five-cycle
Hann-windowed excitation and reversible surface-mounted aluminium masses. All
four reference positions lie approximately on one straight line. Exact geometry
comes from the independently published tables and local `metadata/geometry.json`.
The 66 pairs are unordered recorded opportunities; reciprocal directions are
not duplicated. There is one specimen, not 18 independent specimens.

The selected HDF5 catch and pitch histories each have 13,108 samples at 10 MHz,
so the time step is 0.1 microseconds and the recorded window is 1.3108 ms.
Five cycles at 40 kHz last 125 microseconds; finite packet width limits spatial
resolution regardless of the much smaller ADC time step. In a healthy 20 C
record, the electrical source envelope peak is near 58.5 microseconds. Its
15-percent-envelope support is approximately 16.5-109.7 microseconds. These
healthy-only observations justify explicitly tracking source timing; they do
not establish a globally pure propagating mode.

The paper reports electrical crosstalk at the start of the record, interference
from multiple edge-reflected modes, and relatively stronger fundamental
antisymmetric response at lower frequencies. Its T4-T10 velocity of 1166 to
1133 m/s across 20-60 C is expressly a *phase* velocity derived by correlation.
It is not inserted as an independently known envelope group velocity here.
The fitted quantity is called effective packet slowness. No A0/S0 identity is
certified, and a packet can still be contaminated by a reflection.

The declared excitation array has 5,001 points, whereas the recorded pitch is
sampled on the receiver's 10 MHz clock. The generator-array count is not treated
as the receiver time axis. Calibration and imaging use the recorded pitch/catch
histories, whose approximately 40 kHz source spectrum agrees with their native
sampling declaration.

## Frozen models and processing

Let `h_j(t)` be the demeaned, band-limited healthy electrical source for recorded
path j. Let `b_j(t)` and `y_j(t)` be similarly processed healthy baseline and test
catch histories. The implementation uses a fixed 20-60 kHz band and an analytic
envelope of the source correlation. A bounded healthy-only first substantial
packet rule supplies direct-path delay `u_j`. The exact constants, qualification
checks, selected packet indices, residuals and coefficients are preserved by
`PacketCalibration.to_dict()` and the implementation SHA-256. They must not be
adjusted after viewing new damaged images.

For a nonzero segment of length d and angle theta, use the empirical reciprocal
slowness approximation, in microseconds per metre:

```text
s(theta) = s0 + sc*cos(2*theta) + ss*sin(2*theta)
u_j ~= delay + distance(TX_j,RX_j)*s(theta_j)
```

The isotropic control fixes `sc=ss=0`; the directional model fits those terms.
The common delay and propagation coefficients are fitted only to healthy cycle
1, separately for baseline 20, 40 and 60 C. Rank, packet-fit residuals, the number
of inliers, positive propagation time and the bounded speed domain determine
qualification. A failed calibration produces an explicit unsupported result;
it does not silently substitute a successful damage-derived calibration. The
angular model approximates propagation time; it is not a fitted elasticity
tensor, a dispersion curve or a complete anisotropic group-velocity surface.

Before any new damaged-waveform analysis, an initial healthy-only pilot that
allowed all short paths qualified all six models. This was rejected as a final
policy because short delays overlap source crosstalk and the five-cycle burst.
The revised rule excludes distances below 0.24 m from calibration and permits
packet picks only above `max(distance/2500 m/s, 62.5 microseconds)`. The first
local peak must reach half of the strongest local peak in the remaining
600-2500 m/s delay domain. Both isotropic and directional healthy fits retain
their intercept bound of +/-25 microseconds and one-cycle residual bound of
25 microseconds. Qualification requires at least 33 inliers (half of all 66
recorded opportunities), identifiable geometry, bounded positive speed across
all angles and no parameter at its bound.

This conservative healthy-only pilot qualified directional 40 C (45 inliers,
10.34 microseconds inlier RMS) and isotropic 60 C (36 inliers, 10.78 microseconds
inlier RMS). Four of six models reached the declared delay bound and are
unqualified. These healthy-only findings are retained before damaged analysis;
qualification limits are not relaxed to force support. Short paths remain
available to each method's equal-budget imaging replay. The six fits reuse three
physical healthy banks and are not independent physical tests.

The residual source-correlation envelope is, schematically:

```text
e_j(u) = abs(Hilbert(correlate(y_j-b_j, h_j))(u))
tau_j(x) = delay
         + distance(TX_j,x)*s(angle(TX_j,x))
         + distance(x,RX_j)*s(angle(x,RX_j))
I_B(x) = sum_{j in first B fixed recorded paths} normalized_e_j(tau_j(x))
```

The source correlation cancels the shared electrical excitation centre when
expressed on its lag axis. The fitted common delay is included once per
transmitter-cell-receiver path. Reference source/receiver norms provide path
scales. Out-of-window values contribute zero. The exact filtering, correlation
normalization and bounds are recorded in the implementation and result hashes.
Test catches never supply a fitted propagation coefficient, a source shift,
baseline stretch or a gain chosen to minimize residuals. No test response or
damage label is used to fit calibration. Known nominal temperature chooses the
healthy reference only in the condition-matched context. Future test-path
features never influence the fixed geometry order.

The test's recorded source is checked by the existing native loader for schema
and nonzero energy, but this variant does not align its timing or gain to the
healthy source template. Electrical source drift can therefore contribute to
baseline residuals. Source-only alignment would be a separate future variant
with independently frozen settings, not an adjustment made to improve these
damaged images.

## Common opportunities, splits and scoring

Use the original source audit's verified 18-bank subset. Healthy cycle 1 supplies
all baselines, source templates and propagation calibration. Healthy cycle 2 at
20/40/60 C supplies the three healthy comparisons and is not fitted. Twelve
damaged banks cover four known reference mass positions and three temperatures.
There is no damage-label training, so no leave-one-position fitted model is
needed; nevertheless, these cases were seen previously and only support
exploratory descriptive results.

Use a fixed 50 x 50 grid of 10 mm cell centres across the entire plate. Compute
one geometry-only path permutation from the old RAPID spatial kernels: longest
path first, followed by maximal minimum kernel cosine distance. Use that same
permutation for every method and every physical case, at budgets 16, 32 and all
66 actual recorded paths. Each attempted path consumes one opportunity even if
processing fails. This is fixed replay, not adaptive selection or new physical
acquisition. Selection receives no test waveform or reference location.

Compare three raw images: old DI-weighted RAPID, isotropic packet backprojection
and directional packet backprojection. Two operating contexts are reported
separately: nominal-condition-matched healthy baseline, and 20 C baseline used
at every temperature. Condition matching does not imply equal measured surface
temperature. The fixed-20 control also keeps its healthy-20 packet calibration;
it is an exposed temperature-confounding comparison, not a compensation claim.

Reference truth is applied only after each complete fixed replay, for Euclidean
peak-location error. Report all per-position, temperature, context, method and
budget results, 25/50/100 mm successes, missing estimates and failed paths. A
flat image supplies no meaningful location and is excluded from conditional
mean error with its missing-case count retained. Aggregation must state whether
all twelve damaged conditions are usable. The two contexts reuse physical banks
and must not be counted as extra independent specimens. No confidence interval
for specimen generalization is inferred from these repeats.

When packet calibration qualifies only at some temperatures, compare packet
errors with RAPID on those exact same position/temperature/context/budget cases.
Report the number of eligible paired cases and their common-control mean error;
do not compare a four-case packet mean with RAPID's all-twelve-case mean. A
fixed-20 comparison with unsupported healthy-20 timing produces no packet
localization estimate and remains an explicit unsupported comparison.

Intensity, peak-to-mean ratio and healthy image maxima are descriptive raw
quantities. They are neither posterior probabilities nor a validated detector.
Healthy images may show peaks. Without an independent threshold protocol,
neither a false-positive rate nor a sensitivity is asserted. A sharper image
does not itself prove that damage was detected.

## Evidence outputs and reproduction

The script records six healthy calibration models, their qualification evidence,
270 budget/method/context rows, full raw images, path failures, selected paths,
source identities and source/software/protocol SHA-256 before and after the run.
The original loader checks member CRC32, SHA-256, bounded HDF5 schema, native
clock, source energy and published geometry. It retains actual chamber and two
surface temperatures. Whole-archive MD5 remains unverified because only bounded
original members were downloaded. Existing results are never overwritten.

```powershell
.venv\Scripts\python.exe scripts\validate_wave_packet_imaging.py
```

The result is
`research_results/wave_packet_imaging_development_2026_10_12.json`. A result may
finish with unqualified packet calibrations; those remain failures and cannot
support a complete successful method comparison. This branch does not change
production decisions, establish cross-specimen reliability, validate the audio
range ESP32 apparatus, or change a patent score by introducing established DAS.
Any supported improvement requires a later frozen evaluation on genuinely
uninspected measurements, ideally independently acquired specimens.
