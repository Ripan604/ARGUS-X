# Healthy-only qualification of packet imaging paths

12 October 2026. Separate exploratory development following the preserved
[first wave-packet study](WAVE_PACKET_IMAGING_PROTOCOL.md). The original eighteen
OGW banks, their first imaging results and later warming confirmation have
already been inspected. This variant is not untouched confirmation. It reads
only the original `open_guided_waves/` subset and the retained first result;
no confirmation bank is read. The first driver, protocol and result remain
unchanged. Their six frozen code/protocol sources are retained under
`output/research_sources/wave_packet_imaging_2026_10_12_v1/`.

## Why qualify reference paths

The first experiment fitted an effective propagation model on healthy packet
inliers but then imaged every recorded path. It did not require a path to agree
with the fitted packet delay or have stable healthy reference amplitude.
Subsequent healthy-only inspection found path 60, recorded pair [8,9] (T9-T10),
had 20-60 kHz filtered receiver norms of 10.21266, 0.0327399 and 9.85255 at
20, 40 and 60 C. Its raw standard deviations were 0.08942, 0.0009533 and
0.08624. The 40 C reference is approximately 0.0032 of its adjacent healthy
amplitudes. This is a possible acquisition/coupling anomaly; no particular
physical cause has been established. Dividing by this tiny reference norm
can amplify a residual image substantially.

The new branch requires both measured healthy packet agreement and a broad
healthy-reference energy consistency check. The rule is motivated by healthy
data and first-study failures, so its outcomes are descriptive development.
It is not permissible to claim a newly independent trial by adding this gate.
An energy gate is an acquisition safeguard, not a patented physical principle.

## Frozen qualification

The native clock, source correlation, 20-60 kHz filter, first substantial packet
rule, speed domain, delay bound, robust isotropic/twofold directional fit and
all qualification constants of the first study remain fixed. Four of six
healthy models were unsupported; the model bounds are not relaxed. No new test
source alignment, gain fit, receiver warp or damage-derived propagation fit is
introduced. Current code additionally rejects signed-integer amplitude overflow;
the original measured waveforms are floating point and their numerics are
unchanged. The source snapshot preserves the prior implementation exactly.

Stack healthy cycle 1 receiver and pitch histories at 20, 40 and 60 C. For each
recorded path j, compute filtered, demeaned norms `C_kj` and `P_kj` for the three
healthy anchors. Define source-normalized receiver level `L_kj=C_kj/P_kj` and
`M_j=median_k L_kj`. For the chosen baseline k, an imaging path is eligible only
when:

```text
the chosen healthy packet calibration is supported
j is in its final healthy packet-fit inlier set
0.1 <= L_kj/M_j <= 10
all compared healthy norms are finite and usable
```

The module's qualification evidence records energy ratios, packet eligibility
and final accepted/rejected indices. The broad tenfold bounds are frozen here;
they are not optimized by damage localization results. The median is formed
only from healthy cycle 1, never from healthy cycle 2 or damaged banks. Nominal
temperature chooses the baseline in the matched context; it does not fit a
test-response-dependent coefficient. At least twelve eligible recorded paths
must remain for reference qualification to be supported. A healthy fit or
reference qualification failure supplies no packet location. Good amplitude consistency cannot certify
a physical mode, scattered-wave model, or correct damage inference.

The inlier intersection matters independently of the amplitude rule. Path 60
is short and was already excluded from packet-speed calibration; it is therefore
ineligible even if it passes an energy check at another temperature. This study
tests the combined qualification rule and does not attribute any result solely
to the energy gate. A separate frozen ablation would be needed for attribution.

## Common opportunities and paired comparisons

Use the original 50 x 50 grid, published sensor geometry and fixed geometry-only
path order. Replay the same 16, 32 and 66 recorded opportunities for raw RAPID,
qualified isotropic packet imaging and qualified directional packet imaging.
Each method consumes the entire common prefix. A packet method skips an
ineligible path's image contribution but still consumes that opportunity.
Record `queried_path_indices`, successful `used_path_indices`,
`qualification_rejected_path_indices` and numerical `processing_failures`
separately. Rejected reference paths must not be counted as avoided physical
measurements or savings. No replacement path is acquired to hide rejection.

The image sum still uses source-correlated residual envelopes at the fitted
transmitter-cell-receiver delay. It uses only the healthy electrical source
template; test source timing/gain remain unaligned and can contribute to
residuals. This is an established delay-and-sum approximation with multimode,
dispersion, crosstalk and edge-reflection limits documented in the first
protocol. Narrow packet peaks and directional slowness do not certify a mode.

Retain both condition-matched and fixed-20 contexts, all twelve damaged banks
and all three healthy cycle 2 comparisons. The one specimen and four collinear
surface mass positions remain the physical evaluation units. Contexts, paths,
budgets and processing variants reuse those banks, so they do not create new
independent specimens. No sensitivity, false-positive rate, calibrated posterior
or field reliability is inferred from raw image maxima.

Only after a complete fixed replay apply the published mass position to score
peak-location error. For every supported qualified condition compare exactly
the same position, temperature, context and opportunity budget against both
raw RAPID and the first study's all-path packet image. Preserve improvements
and regressions. A supported four-case mean must not be compared to a
twelve-case all-temperature mean. Report eligibility coverage and successful
contributing path counts alongside errors. Unsupported or flat images provide
no meaningful location and retain a missing-estimate count.

Healthy maps and their peak-to-mean ratios remain raw descriptive images. An
unsupported healthy image is distinguished from a flat supported image. The
gate does not supply a damage/no-damage threshold. A qualified image can still
produce a sharp incorrect location or a peak in a healthy case.

## Integrity, outputs and reproduction

The original loader verifies member CRC32, SHA-256, bounded native HDF5 schema,
clock and source energy. Whole-archive MD5 remains unverified. Verify that the
retained first result is completed and that its six archived source hashes
match the hashes embedded in that result. Verify original measured data hashes
against the first study before pairing its descriptive controls. Do not execute
archived code. Raw RAPID must reproduce the retained first-study locations and
errors on every comparison; a mismatch invalidates study completion.

Record source/software/protocol and retained-result SHA-256 before and after,
all six healthy calibrations and qualifications, all 270 comparison rows, raw
images, used/rejected/failed path indices, paired errors and runtime. The new
result uses exclusive creation and never replaces old evidence:

```powershell
.venv\Scripts\python.exe scripts\validate_qualified_wave_packet_imaging.py
```

Output:
`research_results/qualified_wave_packet_imaging_development_2026_10_12.json`.
The script and protocol are separate files. This branch changes no production
inference and establishes neither hardware validation nor patent novelty.
Any favorable result still requires a frozen genuinely uninspected evaluation.
