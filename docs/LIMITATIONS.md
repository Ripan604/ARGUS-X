# Limitations

ARGUS NEO is a research and decision-support demonstrator, not a certified safety-critical NDE device.

- Primary quantitative evidence is simulated. The reduced wave model is not FEM and has not been validated for a specific material, transducer, boundary condition, or damage mode.
- The structural posterior represents one dominant localized anomaly. Extent, severity, and type are lightweight moments, not fully coupled field variables; multiple defects are not modeled.
- Nuisance posteriors are factorized bounded Gaussians. Timing/velocity, gain/coupling, pose/path, and temperature/material dependencies are correlated in reality.
- The matched-filter likelihood and planner information value are deliberate real-time approximations. They can be misspecified and are not globally optimal Bayesian design.
- OOD operates on a compact signature and limited online reference set. It can miss mismatch or abstain on nominal data. Confidence is capped but not safety-calibrated.
- Commodity microphones/cameras/IMUs are audio-range demo sensors. Browser processing, clocks, automatic gain, mounting, and network timing are uncontrolled.
- Synthetic material profiles are illustrative and explicitly unsourced. They must not be quoted as exact aluminum/CFRP properties.
- The local LAN API has no user authentication or TLS. It must remain on a trusted network.
- SQLite jobs use one thread. A process restart marks an interrupted job failed; it does not resume arbitrary computation, although bank generation itself is chunked/resumable.
- Research bundles are integrity-checked but not signed. Patentability, freedom to operate, inventorship, grant probability, and commercial value require professional and market review.

Highest-value next evidence is paired healthy/defective physical data with independently measured geometry and timing, a preregistered blind test, calibration on out-of-domain specimens, and comparison with established NDE/reference methods.

