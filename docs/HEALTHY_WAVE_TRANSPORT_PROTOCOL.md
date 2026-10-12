# Healthy-only temperature and source-clock transport

Written 8 October 2026 before inspecting confirmation catch signals or damage indices. This is a new experimental native-frequency compensation module; existing studies, protocols and raw manifests remain unchanged.

## Preserved healthy-development failure and revised domain

The initial one-percent stretch policy qualified **zero of 66 receiver paths** across all healthy anchors. The healthy source alignments remained supported, but receiver fits frequently reached the stretch bound or had excessive residuals. That failure, its report, and the exact initial module/tests/protocol are archived under `output/release/fundamental_pilots/transport_v1/`, with SHA256 receipts. The original report remains historical evidence.

Before any new confirmation catches are used, the healthy-development revision widens the candidate stretch domain to **±5%** and the fixed coarse grid to **41 by 41**. This is an explicitly documented development choice from healthy data, not a claim that all thermal propagation is bounded by five percent. Residual, identifiability, source, receiver-delay and gain qualification limits are unchanged. A wider search is not permission to declare a poor fit supported.

Every fitted model owns an immutable `FitPolicy`; prediction uses that model's exact bounds. The model identity binds the complete policy, training-array hash and implementation-source SHA256. No module-global monkeypatch changes a fitted model. An explicit one-percent policy remains available for reproduction. Later experiments must record which policy they use; the failed policy cannot be overwritten or silently replaced in an earlier result.

## Established physical basis

Temperature changes elastic propagation and transducer response. Baseline signal stretch and optimal baseline selection are established methods; see [Croxford, Moll, Wilcox and Michaels (2010)](https://doi.org/10.1016/j.ultras.2009.11.002). Combining propagation stretch with phase-response compensation also has prior literature, including [Herdovics and Cegla's transducer phase-response work](https://doi.org/10.1177/1475921718759272). This implementation makes no claim that those methods or an affine time warp are new inventions.

The approximation is `healthy_receiver_T(t) ~= gain(T) * receiver_20((t - source_delay - receiver_delay(T))/scale(T))`. A scale above one lengthens propagation time. Source delay is estimated from the **recorded electrical pitch**, separately from receiver propagation. The approximation cannot represent arbitrary dispersion, mode conversion, temperature gradients or coupling hysteresis.

## Inputs and prohibition on test fitting

Use only the existing first healthy ascending-cycle anchors at nominal 20, 40 and 60 C, with their actual two-sensor surface temperatures. Inputs are three complete native catch/pitch banks, 13,108 samples per recorded path at 10 MHz. The measured study uses all 66 paths; synthetic contract tests may use fewer paths. No damage position, damage waveform, confirmation catch, second healthy cycle, new 30/50 C confirmation bank or 19 cooling calibration blocks may fit or tune transport parameters.

The source template and receiver template are the first healthy anchor. Immutable bytes-backed arrays prevent callers from modifying fitted templates or coefficients. The module has no dataset loader, RNG, truth argument, adaptive window selection or serialization of executable model objects.

## Fixed fitting and parameter domain

Record source-clock delay using signed FFT cross-correlation in a fixed first-250-microsecond pitch window, restricted to ±10 microseconds. Use a three-point peak refinement. Reject zero-energy/nonfinite pitch, a bound-hitting peak or aligned signed correlation below 0.80. These limits are fixed before confirmation and narrower than half a 40 kHz cycle; no damaged receiver participates in this alignment.

For each non-reference healthy anchor/path, align out its measured pitch delay, then fit receiver stretch, residual delay and positive gain against the healthy reference. The revised default uses a fixed 41-by-41 coarse grid followed by bounded least-squares refinement with at most 60 function evaluations. The optimization uses every fourth native sample, still well above the excitation Nyquist rate; prediction and damage-index calculation retain the full native window.

The revised default bounds are scale 0.95–1.05, receiver delay ±10 microseconds and gain 0.5–2.0. Gain is profiled analytically for each warp. Outside-template times receive zero baseline prediction; their count is disclosed. A dimensionless finite-difference Jacobian of normalized healthy residuals supplies a scale/delay identifiability diagnostic, with a fixed condition-number limit of 10,000. A normalized healthy fit RMS above 0.30, active parameter bounds, or insufficient source alignment marks a fit unsupported. The limits are conservative model-policy choices, not instrument specifications. Explicit policies may tighten these qualification limits; they cannot relax them to force a successful development score.

Interpolate the three healthy parameter anchors piecewise linearly in the mean actual surface temperature. Permit at most 3 C extrapolation outside those means, disclose it, and reject larger excursions. A new pitch waveform may supply only the selected path's source-clock alignment. It must not be acquired or analysed across future unselected paths to rank them.

## Independent development residual and downstream gate

Before the middle healthy anchor is incorporated into the final interpolation, predict it from the 20/60 C endpoint fits and its own recorded pitch. The **old damage index**, `1 - abs(Pearson(predicted_reference, observed_catch))`, remains unchanged and bounded in [0,1]. This middle-anchor prediction is a healthy-only development diagnostic.

Freeze each path's scale as `max(0.02, middle-anchor development damage index)`. This is a conservative residual normalization proxy from one held-out temperature, not an independently estimated noise standard deviation or calibrated probability. The 19 new complete healthy cooling blocks must not change it; those blocks are reserved for separately calibrating a complete adaptive trajectory gate. New confirmation catch signals remain untouched until all transport/gate source, tests and protocol are frozen.

The final model may use all three healthy anchors for interpolation. Its prediction API accepts only path index, actual surface temperature and that path's recorded pitch. Observed catch is accepted by a separate damage-index operation **after** the reference has been generated, and cannot change the warp or fitted model. Return the residual-normalization scale, corrected index, normalized RMS diagnostic, fit/source/temperature diagnostics and supported status. Unsupported observations consume the acquisition opportunity and remain rejected in downstream traces.

## Verification and limits

Tests cover recovery of injected healthy delay/stretch/gain, electrical source-delay sign, fixed pitch bounds, immutable templates, invalid numeric/native shapes, temperature extrapolation, residual-scale separation, and the fact that changing a test catch cannot change the predicted reference. No test asserts superiority on a fabricated damage label. No confirmation outcome changes a parameter or window.

This module compensates nuisance variation using measured healthy development data. It does not validate the physical specimen, source-clock hardware, a defect mechanism, cross-specimen generalization, exchangeability of thermal cycles, or a field probability. Its actual measured effectiveness must be reported from the subsequently frozen confirmation study, including rejection or failure.
