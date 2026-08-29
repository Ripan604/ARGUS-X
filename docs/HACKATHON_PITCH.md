# ARGUS pitch brief

## One line

ARGUS is AI that decides what physical experiment to perform next.

## Problem

Inspection systems are usually passive: engineers choose probe locations, collect a batch, then AI classifies or reconstructs. Poor first measurements mean poor inference or expensive brute-force scans.

## Insight

Every measurement has a value *before it is taken*. A candidate source/receiver/frequency configuration is useful when plausible hidden defects predict meaningfully different responses under it.

## Product

ARGUS maintains a posterior heatmap, simulates counterfactual responses for leading hypotheses, recommends a cost-aware experiment, acquires a real or simulated waveform, recursively updates belief, and repeats until a measurable stop rule is reached.

## Technical moat to investigate

- sequential co-selection of source, receiver, band, waveform, amplitude, and duration;
- counterfactual response disagreement conditioned on the live posterior;
- joint information/cost/redundancy score with human-executable probe placement;
- modality-independent closed-loop physical interrogation with traceable explanations;
- camera homography that turns normalized experiments into physical placement guidance.

These are hypotheses for professional IP analysis, not patentability conclusions.

## Evidence in this repository

- reproducible physics-inspired signals;
- a Bayesian posterior that accumulates every measurement;
- an adaptive planner and random/grid baselines;
- actual 30-case paired benchmark JSON/CSV with trajectories and bootstrap intervals;
- 17 backend tests, zero frontend lint errors, a production build, and a live dual-service HTTP smoke test;
- WAV, microphone, serial, calibration, and ESP32 paths;
- a trained 58 KB PyTorch response surrogate with held-out per-feature metrics;
- an auditable top-five decision table.

## Numbers worth memorizing

- Deterministic easy demo: 8 experiments, 10.0 mm simulated error, 59.7% entropy reduction.
- Thirty-case medium benchmark: ARGUS entropy 0.419 versus 0.498 random and 0.621 grid.
- Success within 15 mm: 73.3% ARGUS versus 56.7% random and 60.0% grid.
- Paired entropy advantage confidence intervals exclude zero; localization-error intervals do not.

## Closing line

“ARGUS turns sensing from passive data collection into an intelligent conversation with the physical world: hypothesize, choose, excite, listen, and update.”
