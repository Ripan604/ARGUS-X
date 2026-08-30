# ARGUS-X problem disposition register

Generated from the complete master inventory. **1331 uniquely identified problems are accounted for.**

> A status of `implemented_and_tested` means a narrow executable software control exists. It does not imply physical validation, certification, safety approval, or patentability.

## Status summary

| Status | Count |
|---|---:|
| `acknowledged_and_bounded` | 177 |
| `implemented_and_tested` | 277 |
| `partially_mitigated` | 588 |
| `requires_literature_or_legal_review` | 45 |
| `requires_physical_validation` | 244 |

## Complete register

| ID | Section | Problem | Status | Evidence / boundary |
|---|---|---|---|---|
| A1 | PROBLEM DEFINITION | Problem is currently too narrowly framed as defect localization. Need to define whether the system must detect, localize, classify, quantify, track and assess structural damage. | `partially_mitigated` | backend/app/assurance/monitor.py; backend/app/decision/loss.py |
| A2 | PROBLEM DEFINITION | No explicit distinction between: - anomaly detection - damage detection - damage localization - damage classification - damage quantification - structural integrity assessment. | `implemented_and_tested` | backend/app/assurance/monitor.py; backend/app/decision/loss.py |
| A3 | PROBLEM DEFINITION | No-defect / healthy condition may not be explicitly modeled. | `implemented_and_tested` | backend/app/assurance/monitor.py; backend/app/decision/loss.py |
| A4 | PROBLEM DEFINITION | Unknown defect types may not be represented. | `partially_mitigated` | backend/app/assurance/monitor.py; backend/app/decision/loss.py |
| A5 | PROBLEM DEFINITION | Multiple simultaneous defects are not adequately represented. | `partially_mitigated` | backend/app/assurance/monitor.py; backend/app/decision/loss.py |
| A6 | PROBLEM DEFINITION | Defect geometry may be oversimplified to a point/location. | `partially_mitigated` | backend/app/assurance/monitor.py; backend/app/decision/loss.py |
| A7 | PROBLEM DEFINITION | Defects may have arbitrary shapes. | `partially_mitigated` | backend/app/assurance/monitor.py; backend/app/decision/loss.py |
| A8 | PROBLEM DEFINITION | Defect orientation may matter. | `partially_mitigated` | backend/app/assurance/monitor.py; backend/app/decision/loss.py |
| A9 | PROBLEM DEFINITION | Defect depth may matter. | `partially_mitigated` | backend/app/assurance/monitor.py; backend/app/decision/loss.py |
| A10 | PROBLEM DEFINITION | Defect through-thickness position may matter. | `partially_mitigated` | backend/app/assurance/monitor.py; backend/app/decision/loss.py |
| A11 | PROBLEM DEFINITION | Defect size may matter. | `partially_mitigated` | backend/app/assurance/monitor.py; backend/app/decision/loss.py |
| A12 | PROBLEM DEFINITION | Defect severity may matter. | `partially_mitigated` | backend/app/assurance/monitor.py; backend/app/decision/loss.py |
| A13 | PROBLEM DEFINITION | Defect evolution over time is not modeled. | `partially_mitigated` | backend/app/assurance/monitor.py; backend/app/decision/loss.py |
| A14 | PROBLEM DEFINITION | Progressive fatigue damage is not modeled. | `partially_mitigated` | backend/app/assurance/monitor.py; backend/app/decision/loss.py |
| A15 | PROBLEM DEFINITION | Damage initiation is not modeled. | `partially_mitigated` | backend/app/assurance/monitor.py; backend/app/decision/loss.py |
| A16 | PROBLEM DEFINITION | Damage propagation is not modeled. | `partially_mitigated` | backend/app/assurance/monitor.py; backend/app/decision/loss.py |
| A17 | PROBLEM DEFINITION | Repair state is not modeled. | `partially_mitigated` | backend/app/assurance/monitor.py; backend/app/decision/loss.py |
| A18 | PROBLEM DEFINITION | Previously detected damage history may not influence future inference. | `partially_mitigated` | backend/app/assurance/monitor.py; backend/app/decision/loss.py |
| A19 | PROBLEM DEFINITION | Structural load state may not be part of the latent state. | `partially_mitigated` | backend/app/assurance/monitor.py; backend/app/decision/loss.py |
| A20 | PROBLEM DEFINITION | Operating condition may not be part of the problem definition. | `partially_mitigated` | backend/app/assurance/monitor.py; backend/app/decision/loss.py |
| A21 | PROBLEM DEFINITION | Inspection objective may change by application. | `partially_mitigated` | backend/app/assurance/monitor.py; backend/app/decision/loss.py |
| A22 | PROBLEM DEFINITION | Detection objective and localization objective can conflict. | `partially_mitigated` | backend/app/assurance/monitor.py; backend/app/decision/loss.py |
| A23 | PROBLEM DEFINITION | Localization accuracy alone does not necessarily imply engineering usefulness. | `partially_mitigated` | backend/app/assurance/monitor.py; backend/app/decision/loss.py |
| A24 | PROBLEM DEFINITION | There is no explicit decision layer translating prediction into an engineering action. | `implemented_and_tested` | backend/app/assurance/monitor.py; backend/app/decision/loss.py |
| A25 | PROBLEM DEFINITION | No explicit definition of what constitutes a "safe" inspection result. | `partially_mitigated` | backend/app/assurance/monitor.py; backend/app/decision/loss.py |
| A26 | PROBLEM DEFINITION | No explicit definition of when human intervention is mandatory. | `implemented_and_tested` | backend/app/assurance/monitor.py; backend/app/decision/loss.py |
| A27 | PROBLEM DEFINITION | No explicit definition of acceptable false-negative rate. | `partially_mitigated` | backend/app/assurance/monitor.py; backend/app/decision/loss.py |
| A28 | PROBLEM DEFINITION | No explicit definition of acceptable false-positive rate. | `partially_mitigated` | backend/app/assurance/monitor.py; backend/app/decision/loss.py |
| A29 | PROBLEM DEFINITION | No explicit definition of inspection cost. | `implemented_and_tested` | backend/app/assurance/monitor.py; backend/app/decision/loss.py |
| A30 | PROBLEM DEFINITION | No explicit definition of safety risk. | `implemented_and_tested` | backend/app/assurance/monitor.py; backend/app/decision/loss.py |
| A31 | PROBLEM DEFINITION | No explicit definition of operational downtime. | `partially_mitigated` | backend/app/assurance/monitor.py; backend/app/decision/loss.py |
| A32 | PROBLEM DEFINITION | No explicit definition of acceptable inference latency. | `implemented_and_tested` | backend/app/assurance/monitor.py; backend/app/decision/loss.py |
| A33 | PROBLEM DEFINITION | No explicit definition of inspection coverage. | `partially_mitigated` | backend/app/assurance/monitor.py; backend/app/decision/loss.py |
| A34 | PROBLEM DEFINITION | No explicit definition of minimum detectable damage size. | `partially_mitigated` | backend/app/assurance/monitor.py; backend/app/decision/loss.py |
| A35 | PROBLEM DEFINITION | No explicit definition of probability of detection (POD). | `partially_mitigated` | backend/app/assurance/monitor.py; backend/app/decision/loss.py |
| B1 | PHYSICS MODEL PROBLEMS | Simplified wave propagation model. | `requires_physical_validation` | backend/app/simulation/physics.py; docs/SCIENTIFIC_MODEL.md; docs/LIMITATIONS.md |
| B2 | PHYSICS MODEL PROBLEMS | Constant wave velocity assumption can be unrealistic. | `requires_physical_validation` | backend/app/simulation/physics.py; docs/SCIENTIFIC_MODEL.md; docs/LIMITATIONS.md |
| B3 | PHYSICS MODEL PROBLEMS | Composite materials are anisotropic. | `requires_physical_validation` | backend/app/simulation/physics.py; docs/SCIENTIFIC_MODEL.md; docs/LIMITATIONS.md |
| B4 | PHYSICS MODEL PROBLEMS | Wave velocity can depend on propagation direction. | `requires_physical_validation` | backend/app/simulation/physics.py; docs/SCIENTIFIC_MODEL.md; docs/LIMITATIONS.md |
| B5 | PHYSICS MODEL PROBLEMS | Wave velocity can depend on material orientation. | `requires_physical_validation` | backend/app/simulation/physics.py; docs/SCIENTIFIC_MODEL.md; docs/LIMITATIONS.md |
| B6 | PHYSICS MODEL PROBLEMS | Wave velocity can depend on laminate layup. | `requires_physical_validation` | backend/app/simulation/physics.py; docs/SCIENTIFIC_MODEL.md; docs/LIMITATIONS.md |
| B7 | PHYSICS MODEL PROBLEMS | Wave velocity can depend on frequency. | `requires_physical_validation` | backend/app/simulation/physics.py; docs/SCIENTIFIC_MODEL.md; docs/LIMITATIONS.md |
| B8 | PHYSICS MODEL PROBLEMS | Dispersion may be insufficiently modeled. | `requires_physical_validation` | backend/app/simulation/physics.py; docs/SCIENTIFIC_MODEL.md; docs/LIMITATIONS.md |
| B9 | PHYSICS MODEL PROBLEMS | Multiple guided-wave modes may exist. | `requires_physical_validation` | backend/app/simulation/physics.py; docs/SCIENTIFIC_MODEL.md; docs/LIMITATIONS.md |
| B10 | PHYSICS MODEL PROBLEMS | Mode conversion may occur. | `requires_physical_validation` | backend/app/simulation/physics.py; docs/SCIENTIFIC_MODEL.md; docs/LIMITATIONS.md |
| B11 | PHYSICS MODEL PROBLEMS | Different modes may overlap in time/frequency. | `requires_physical_validation` | backend/app/simulation/physics.py; docs/SCIENTIFIC_MODEL.md; docs/LIMITATIONS.md |
| B12 | PHYSICS MODEL PROBLEMS | Group velocity and phase velocity differ. | `requires_physical_validation` | backend/app/simulation/physics.py; docs/SCIENTIFIC_MODEL.md; docs/LIMITATIONS.md |
| B13 | PHYSICS MODEL PROBLEMS | Boundary reflections may be more complex than modeled. | `requires_physical_validation` | backend/app/simulation/physics.py; docs/SCIENTIFIC_MODEL.md; docs/LIMITATIONS.md |
| B14 | PHYSICS MODEL PROBLEMS | Edge effects may be significant. | `requires_physical_validation` | backend/app/simulation/physics.py; docs/SCIENTIFIC_MODEL.md; docs/LIMITATIONS.md |
| B15 | PHYSICS MODEL PROBLEMS | Structural geometry may be more complex than a rectangular plate. | `requires_physical_validation` | backend/app/simulation/physics.py; docs/SCIENTIFIC_MODEL.md; docs/LIMITATIONS.md |
| B16 | PHYSICS MODEL PROBLEMS | Curvature may affect propagation. | `requires_physical_validation` | backend/app/simulation/physics.py; docs/SCIENTIFIC_MODEL.md; docs/LIMITATIONS.md |
| B17 | PHYSICS MODEL PROBLEMS | Stiffeners may affect propagation. | `requires_physical_validation` | backend/app/simulation/physics.py; docs/SCIENTIFIC_MODEL.md; docs/LIMITATIONS.md |
| B18 | PHYSICS MODEL PROBLEMS | Joints may affect propagation. | `requires_physical_validation` | backend/app/simulation/physics.py; docs/SCIENTIFIC_MODEL.md; docs/LIMITATIONS.md |
| B19 | PHYSICS MODEL PROBLEMS | Fasteners may affect propagation. | `requires_physical_validation` | backend/app/simulation/physics.py; docs/SCIENTIFIC_MODEL.md; docs/LIMITATIONS.md |
| B20 | PHYSICS MODEL PROBLEMS | Thickness variations may affect propagation. | `requires_physical_validation` | backend/app/simulation/physics.py; docs/SCIENTIFIC_MODEL.md; docs/LIMITATIONS.md |
| B21 | PHYSICS MODEL PROBLEMS | Ply interfaces can affect wave propagation. | `requires_physical_validation` | backend/app/simulation/physics.py; docs/SCIENTIFIC_MODEL.md; docs/LIMITATIONS.md |
| B22 | PHYSICS MODEL PROBLEMS | Delaminations can interact with multiple modes. | `requires_physical_validation` | backend/app/simulation/physics.py; docs/SCIENTIFIC_MODEL.md; docs/LIMITATIONS.md |
| B23 | PHYSICS MODEL PROBLEMS | Crack scattering may be direction-dependent. | `requires_physical_validation` | backend/app/simulation/physics.py; docs/SCIENTIFIC_MODEL.md; docs/LIMITATIONS.md |
| B24 | PHYSICS MODEL PROBLEMS | Damage scattering may not be isotropic. | `requires_physical_validation` | backend/app/simulation/physics.py; docs/SCIENTIFIC_MODEL.md; docs/LIMITATIONS.md |
| B25 | PHYSICS MODEL PROBLEMS | Scattering may depend on frequency. | `requires_physical_validation` | backend/app/simulation/physics.py; docs/SCIENTIFIC_MODEL.md; docs/LIMITATIONS.md |
| B26 | PHYSICS MODEL PROBLEMS | Reflection may depend on damage orientation. | `requires_physical_validation` | backend/app/simulation/physics.py; docs/SCIENTIFIC_MODEL.md; docs/LIMITATIONS.md |
| B27 | PHYSICS MODEL PROBLEMS | Transmission may depend on damage orientation. | `requires_physical_validation` | backend/app/simulation/physics.py; docs/SCIENTIFIC_MODEL.md; docs/LIMITATIONS.md |
| B28 | PHYSICS MODEL PROBLEMS | Structural damping may vary. | `requires_physical_validation` | backend/app/simulation/physics.py; docs/SCIENTIFIC_MODEL.md; docs/LIMITATIONS.md |
| B29 | PHYSICS MODEL PROBLEMS | Attenuation may be path-dependent. | `requires_physical_validation` | backend/app/simulation/physics.py; docs/SCIENTIFIC_MODEL.md; docs/LIMITATIONS.md |
| B30 | PHYSICS MODEL PROBLEMS | Material attenuation can be frequency-dependent. | `requires_physical_validation` | backend/app/simulation/physics.py; docs/SCIENTIFIC_MODEL.md; docs/LIMITATIONS.md |
| B31 | PHYSICS MODEL PROBLEMS | Temperature changes wave speed. | `requires_physical_validation` | backend/app/simulation/physics.py; docs/SCIENTIFIC_MODEL.md; docs/LIMITATIONS.md |
| B32 | PHYSICS MODEL PROBLEMS | Temperature changes attenuation. | `requires_physical_validation` | backend/app/simulation/physics.py; docs/SCIENTIFIC_MODEL.md; docs/LIMITATIONS.md |
| B33 | PHYSICS MODEL PROBLEMS | Temperature can change sensor behavior. | `requires_physical_validation` | backend/app/simulation/physics.py; docs/SCIENTIFIC_MODEL.md; docs/LIMITATIONS.md |
| B34 | PHYSICS MODEL PROBLEMS | Humidity may affect measurements. | `requires_physical_validation` | backend/app/simulation/physics.py; docs/SCIENTIFIC_MODEL.md; docs/LIMITATIONS.md |
| B35 | PHYSICS MODEL PROBLEMS | Environmental conditions can alter baseline signals. | `requires_physical_validation` | backend/app/simulation/physics.py; docs/SCIENTIFIC_MODEL.md; docs/LIMITATIONS.md |
| B36 | PHYSICS MODEL PROBLEMS | Mechanical loading changes the measured response. | `requires_physical_validation` | backend/app/simulation/physics.py; docs/SCIENTIFIC_MODEL.md; docs/LIMITATIONS.md |
| B37 | PHYSICS MODEL PROBLEMS | Stress state may affect wave propagation. | `requires_physical_validation` | backend/app/simulation/physics.py; docs/SCIENTIFIC_MODEL.md; docs/LIMITATIONS.md |
| B38 | PHYSICS MODEL PROBLEMS | Nonlinear damage effects may be absent. | `requires_physical_validation` | backend/app/simulation/physics.py; docs/SCIENTIFIC_MODEL.md; docs/LIMITATIONS.md |
| B39 | PHYSICS MODEL PROBLEMS | Contact nonlinearities may be absent. | `requires_physical_validation` | backend/app/simulation/physics.py; docs/SCIENTIFIC_MODEL.md; docs/LIMITATIONS.md |
| B40 | PHYSICS MODEL PROBLEMS | Boundary condition uncertainty may be ignored. | `requires_physical_validation` | backend/app/simulation/physics.py; docs/SCIENTIFIC_MODEL.md; docs/LIMITATIONS.md |
| B41 | PHYSICS MODEL PROBLEMS | Sensor mounting can alter local mechanics. | `requires_physical_validation` | backend/app/simulation/physics.py; docs/SCIENTIFIC_MODEL.md; docs/LIMITATIONS.md |
| B42 | PHYSICS MODEL PROBLEMS | Couplant properties can alter measurements. | `requires_physical_validation` | backend/app/simulation/physics.py; docs/SCIENTIFIC_MODEL.md; docs/LIMITATIONS.md |
| B43 | PHYSICS MODEL PROBLEMS | Sensor orientation can affect measurements. | `requires_physical_validation` | backend/app/simulation/physics.py; docs/SCIENTIFIC_MODEL.md; docs/LIMITATIONS.md |
| B44 | PHYSICS MODEL PROBLEMS | Exciter coupling can vary. | `requires_physical_validation` | backend/app/simulation/physics.py; docs/SCIENTIFIC_MODEL.md; docs/LIMITATIONS.md |
| B45 | PHYSICS MODEL PROBLEMS | Receiver coupling can vary. | `requires_physical_validation` | backend/app/simulation/physics.py; docs/SCIENTIFIC_MODEL.md; docs/LIMITATIONS.md |
| B46 | PHYSICS MODEL PROBLEMS | Hardware transfer functions may be ignored. | `requires_physical_validation` | backend/app/simulation/physics.py; docs/SCIENTIFIC_MODEL.md; docs/LIMITATIONS.md |
| B47 | PHYSICS MODEL PROBLEMS | Structural heterogeneity may be underestimated. | `requires_physical_validation` | backend/app/simulation/physics.py; docs/SCIENTIFIC_MODEL.md; docs/LIMITATIONS.md |
| B48 | PHYSICS MODEL PROBLEMS | Composite manufacturing variability may be ignored. | `requires_physical_validation` | backend/app/simulation/physics.py; docs/SCIENTIFIC_MODEL.md; docs/LIMITATIONS.md |
| B49 | PHYSICS MODEL PROBLEMS | Ply waviness may be ignored. | `requires_physical_validation` | backend/app/simulation/physics.py; docs/SCIENTIFIC_MODEL.md; docs/LIMITATIONS.md |
| B50 | PHYSICS MODEL PROBLEMS | Fiber volume variability may be ignored. | `requires_physical_validation` | backend/app/simulation/physics.py; docs/SCIENTIFIC_MODEL.md; docs/LIMITATIONS.md |
| B51 | PHYSICS MODEL PROBLEMS | Manufacturing defects may interact with artificial defects. | `requires_physical_validation` | backend/app/simulation/physics.py; docs/SCIENTIFIC_MODEL.md; docs/LIMITATIONS.md |
| B52 | PHYSICS MODEL PROBLEMS | Real defects are not guaranteed to match synthetic defect assumptions. | `requires_physical_validation` | backend/app/simulation/physics.py; docs/SCIENTIFIC_MODEL.md; docs/LIMITATIONS.md |
| B53 | PHYSICS MODEL PROBLEMS | Damage interaction effects may be absent. | `requires_physical_validation` | backend/app/simulation/physics.py; docs/SCIENTIFIC_MODEL.md; docs/LIMITATIONS.md |
| B54 | PHYSICS MODEL PROBLEMS | Multiple scattering may be absent. | `requires_physical_validation` | backend/app/simulation/physics.py; docs/SCIENTIFIC_MODEL.md; docs/LIMITATIONS.md |
| B55 | PHYSICS MODEL PROBLEMS | Reverberation/ringing may be oversimplified. | `requires_physical_validation` | backend/app/simulation/physics.py; docs/SCIENTIFIC_MODEL.md; docs/LIMITATIONS.md |
| B56 | PHYSICS MODEL PROBLEMS | Noise may not match field noise. | `requires_physical_validation` | backend/app/simulation/physics.py; docs/SCIENTIFIC_MODEL.md; docs/LIMITATIONS.md |
| B57 | PHYSICS MODEL PROBLEMS | Noise may be nonstationary. | `requires_physical_validation` | backend/app/simulation/physics.py; docs/SCIENTIFIC_MODEL.md; docs/LIMITATIONS.md |
| B58 | PHYSICS MODEL PROBLEMS | Noise may be correlated across sensors. | `requires_physical_validation` | backend/app/simulation/physics.py; docs/SCIENTIFIC_MODEL.md; docs/LIMITATIONS.md |
| B59 | PHYSICS MODEL PROBLEMS | Sensor noise may be heterogeneous. | `requires_physical_validation` | backend/app/simulation/physics.py; docs/SCIENTIFIC_MODEL.md; docs/LIMITATIONS.md |
| B60 | PHYSICS MODEL PROBLEMS | Electromagnetic interference may exist. | `requires_physical_validation` | backend/app/simulation/physics.py; docs/SCIENTIFIC_MODEL.md; docs/LIMITATIONS.md |
| B61 | PHYSICS MODEL PROBLEMS | Mechanical vibration may contaminate the signal. | `requires_physical_validation` | backend/app/simulation/physics.py; docs/SCIENTIFIC_MODEL.md; docs/LIMITATIONS.md |
| B62 | PHYSICS MODEL PROBLEMS | Ambient acoustic noise may contaminate the signal. | `requires_physical_validation` | backend/app/simulation/physics.py; docs/SCIENTIFIC_MODEL.md; docs/LIMITATIONS.md |
| B63 | PHYSICS MODEL PROBLEMS | External excitation may contaminate the signal. | `requires_physical_validation` | backend/app/simulation/physics.py; docs/SCIENTIFIC_MODEL.md; docs/LIMITATIONS.md |
| B64 | PHYSICS MODEL PROBLEMS | Real structures may have operational vibration. | `requires_physical_validation` | backend/app/simulation/physics.py; docs/SCIENTIFIC_MODEL.md; docs/LIMITATIONS.md |
| B65 | PHYSICS MODEL PROBLEMS | Temperature-dependent physics may not be modeled. | `requires_physical_validation` | backend/app/simulation/physics.py; docs/SCIENTIFIC_MODEL.md; docs/LIMITATIONS.md |
| B66 | PHYSICS MODEL PROBLEMS | Aging-dependent physics may not be modeled. | `requires_physical_validation` | backend/app/simulation/physics.py; docs/SCIENTIFIC_MODEL.md; docs/LIMITATIONS.md |
| B67 | PHYSICS MODEL PROBLEMS | Fatigue-dependent physics may not be modeled. | `requires_physical_validation` | backend/app/simulation/physics.py; docs/SCIENTIFIC_MODEL.md; docs/LIMITATIONS.md |
| B68 | PHYSICS MODEL PROBLEMS | Material degradation may alter baseline physics. | `requires_physical_validation` | backend/app/simulation/physics.py; docs/SCIENTIFIC_MODEL.md; docs/LIMITATIONS.md |
| B69 | PHYSICS MODEL PROBLEMS | Current simulator may not be a validated digital twin. | `requires_physical_validation` | backend/app/simulation/physics.py; docs/SCIENTIFIC_MODEL.md; docs/LIMITATIONS.md |
| B70 | PHYSICS MODEL PROBLEMS | Simulator parameter uncertainty may be underestimated. | `requires_physical_validation` | backend/app/simulation/physics.py; docs/SCIENTIFIC_MODEL.md; docs/LIMITATIONS.md |
| B71 | PHYSICS MODEL PROBLEMS | Simulator structural discrepancy may be underestimated. | `requires_physical_validation` | backend/app/simulation/physics.py; docs/SCIENTIFIC_MODEL.md; docs/LIMITATIONS.md |
| B72 | PHYSICS MODEL PROBLEMS | Simulator may generate overly easy synthetic examples. | `requires_physical_validation` | backend/app/simulation/physics.py; docs/SCIENTIFIC_MODEL.md; docs/LIMITATIONS.md |
| B73 | PHYSICS MODEL PROBLEMS | Neural surrogate may simply learn simulator artifacts. | `requires_physical_validation` | backend/app/simulation/physics.py; docs/SCIENTIFIC_MODEL.md; docs/LIMITATIONS.md |
| B74 | PHYSICS MODEL PROBLEMS | Simulator-to-real mismatch may dominate model performance. | `requires_physical_validation` | backend/app/simulation/physics.py; docs/SCIENTIFIC_MODEL.md; docs/LIMITATIONS.md |
| B75 | PHYSICS MODEL PROBLEMS | Physics model may not be updated continuously from real measurements. | `requires_physical_validation` | backend/app/simulation/physics.py; docs/SCIENTIFIC_MODEL.md; docs/LIMITATIONS.md |
| C1 | SIGNAL ACQUISITION PROBLEMS | Sensor positions may be uncertain. | `requires_physical_validation` | backend/app/inference/diagnostics.py; backend/app/services/session_manager.py |
| C2 | SIGNAL ACQUISITION PROBLEMS | Source positions may be uncertain. | `requires_physical_validation` | backend/app/inference/diagnostics.py; backend/app/services/session_manager.py |
| C3 | SIGNAL ACQUISITION PROBLEMS | Receiver positions may be uncertain. | `requires_physical_validation` | backend/app/inference/diagnostics.py; backend/app/services/session_manager.py |
| C4 | SIGNAL ACQUISITION PROBLEMS | Sensor orientation may be uncertain. | `requires_physical_validation` | backend/app/inference/diagnostics.py; backend/app/services/session_manager.py |
| C5 | SIGNAL ACQUISITION PROBLEMS | Sensor timing synchronization may be imperfect. | `requires_physical_validation` | backend/app/inference/diagnostics.py; backend/app/services/session_manager.py |
| C6 | SIGNAL ACQUISITION PROBLEMS | Sampling-clock drift may occur. | `requires_physical_validation` | backend/app/inference/diagnostics.py; backend/app/services/session_manager.py |
| C7 | SIGNAL ACQUISITION PROBLEMS | ADC quantization may affect signals. | `requires_physical_validation` | backend/app/inference/diagnostics.py; backend/app/services/session_manager.py |
| C8 | SIGNAL ACQUISITION PROBLEMS | ADC saturation may occur. | `requires_physical_validation` | backend/app/inference/diagnostics.py; backend/app/services/session_manager.py |
| C9 | SIGNAL ACQUISITION PROBLEMS | Clipping may occur. | `requires_physical_validation` | backend/app/inference/diagnostics.py; backend/app/services/session_manager.py |
| C10 | SIGNAL ACQUISITION PROBLEMS | Dynamic range may be insufficient. | `requires_physical_validation` | backend/app/inference/diagnostics.py; backend/app/services/session_manager.py |
| C11 | SIGNAL ACQUISITION PROBLEMS | Analog front-end noise may occur. | `requires_physical_validation` | backend/app/inference/diagnostics.py; backend/app/services/session_manager.py |
| C12 | SIGNAL ACQUISITION PROBLEMS | Amplifier gain may vary. | `requires_physical_validation` | backend/app/inference/diagnostics.py; backend/app/services/session_manager.py |
| C13 | SIGNAL ACQUISITION PROBLEMS | Exciter amplitude may vary. | `requires_physical_validation` | backend/app/inference/diagnostics.py; backend/app/services/session_manager.py |
| C14 | SIGNAL ACQUISITION PROBLEMS | Exciter frequency response may vary. | `requires_physical_validation` | backend/app/inference/diagnostics.py; backend/app/services/session_manager.py |
| C15 | SIGNAL ACQUISITION PROBLEMS | Sensor sensitivity may vary. | `requires_physical_validation` | backend/app/inference/diagnostics.py; backend/app/services/session_manager.py |
| C16 | SIGNAL ACQUISITION PROBLEMS | Sensor-to-sensor manufacturing variation may exist. | `requires_physical_validation` | backend/app/inference/diagnostics.py; backend/app/services/session_manager.py |
| C17 | SIGNAL ACQUISITION PROBLEMS | Sensor degradation over time may occur. | `requires_physical_validation` | backend/app/inference/diagnostics.py; backend/app/services/session_manager.py |
| C18 | SIGNAL ACQUISITION PROBLEMS | Sensor detachment may occur. | `requires_physical_validation` | backend/app/inference/diagnostics.py; backend/app/services/session_manager.py |
| C19 | SIGNAL ACQUISITION PROBLEMS | Sensor partial detachment may occur. | `requires_physical_validation` | backend/app/inference/diagnostics.py; backend/app/services/session_manager.py |
| C20 | SIGNAL ACQUISITION PROBLEMS | Cable faults may occur. | `requires_physical_validation` | backend/app/inference/diagnostics.py; backend/app/services/session_manager.py |
| C21 | SIGNAL ACQUISITION PROBLEMS | Connector failures may occur. | `requires_physical_validation` | backend/app/inference/diagnostics.py; backend/app/services/session_manager.py |
| C22 | SIGNAL ACQUISITION PROBLEMS | Wireless packet loss may occur. | `requires_physical_validation` | backend/app/inference/diagnostics.py; backend/app/services/session_manager.py |
| C23 | SIGNAL ACQUISITION PROBLEMS | Communication latency may occur. | `requires_physical_validation` | backend/app/inference/diagnostics.py; backend/app/services/session_manager.py |
| C24 | SIGNAL ACQUISITION PROBLEMS | Sampling data may be incomplete. | `implemented_and_tested` | backend/app/inference/diagnostics.py; backend/app/services/session_manager.py |
| C25 | SIGNAL ACQUISITION PROBLEMS | Missing samples may occur. | `implemented_and_tested` | backend/app/inference/diagnostics.py; backend/app/services/session_manager.py |
| C26 | SIGNAL ACQUISITION PROBLEMS | Corrupted samples may occur. | `implemented_and_tested` | backend/app/inference/diagnostics.py; backend/app/services/session_manager.py |
| C27 | SIGNAL ACQUISITION PROBLEMS | Timestamp errors may occur. | `implemented_and_tested` | backend/app/inference/diagnostics.py; backend/app/services/session_manager.py |
| C28 | SIGNAL ACQUISITION PROBLEMS | Sensor saturation may go undetected. | `implemented_and_tested` | backend/app/inference/diagnostics.py; backend/app/services/session_manager.py |
| C29 | SIGNAL ACQUISITION PROBLEMS | Hardware temperature may change characteristics. | `requires_physical_validation` | backend/app/inference/diagnostics.py; backend/app/services/session_manager.py |
| C30 | SIGNAL ACQUISITION PROBLEMS | Battery voltage may affect acquisition quality. | `requires_physical_validation` | backend/app/inference/diagnostics.py; backend/app/services/session_manager.py |
| C31 | SIGNAL ACQUISITION PROBLEMS | Embedded processing may introduce quantization. | `requires_physical_validation` | backend/app/inference/diagnostics.py; backend/app/services/session_manager.py |
| C32 | SIGNAL ACQUISITION PROBLEMS | Embedded hardware may not meet sampling requirements. | `requires_physical_validation` | backend/app/inference/diagnostics.py; backend/app/services/session_manager.py |
| C33 | SIGNAL ACQUISITION PROBLEMS | Hardware may introduce deterministic artifacts. | `requires_physical_validation` | backend/app/inference/diagnostics.py; backend/app/services/session_manager.py |
| C34 | SIGNAL ACQUISITION PROBLEMS | Sensor mounting repeatability may be poor. | `requires_physical_validation` | backend/app/inference/diagnostics.py; backend/app/services/session_manager.py |
| C35 | SIGNAL ACQUISITION PROBLEMS | Probe repositioning may change signal characteristics. | `requires_physical_validation` | backend/app/inference/diagnostics.py; backend/app/services/session_manager.py |
| C36 | SIGNAL ACQUISITION PROBLEMS | Coupling pressure may vary. | `requires_physical_validation` | backend/app/inference/diagnostics.py; backend/app/services/session_manager.py |
| C37 | SIGNAL ACQUISITION PROBLEMS | Couplant thickness may vary. | `requires_physical_validation` | backend/app/inference/diagnostics.py; backend/app/services/session_manager.py |
| C38 | SIGNAL ACQUISITION PROBLEMS | Surface roughness may vary. | `requires_physical_validation` | backend/app/inference/diagnostics.py; backend/app/services/session_manager.py |
| C39 | SIGNAL ACQUISITION PROBLEMS | Sensor placement may not exactly match planner coordinates. | `requires_physical_validation` | backend/app/inference/diagnostics.py; backend/app/services/session_manager.py |
| C40 | SIGNAL ACQUISITION PROBLEMS | Physical actuator motion may not equal commanded motion. | `requires_physical_validation` | backend/app/inference/diagnostics.py; backend/app/services/session_manager.py |
| D1 | PREPROCESSING PROBLEMS | Filtering can remove useful damage information. | `partially_mitigated` | backend/app/signal/processing.py |
| D2 | PREPROCESSING PROBLEMS | Filtering can introduce phase distortion. | `partially_mitigated` | backend/app/signal/processing.py |
| D3 | PREPROCESSING PROBLEMS | Filtering parameters may be manually tuned. | `partially_mitigated` | backend/app/signal/processing.py |
| D4 | PREPROCESSING PROBLEMS | Baseline subtraction may be unreliable. | `partially_mitigated` | backend/app/signal/processing.py |
| D5 | PREPROCESSING PROBLEMS | Healthy baseline may be unavailable. | `partially_mitigated` | backend/app/signal/processing.py |
| D6 | PREPROCESSING PROBLEMS | Healthy baseline may change with environment. | `partially_mitigated` | backend/app/signal/processing.py |
| D7 | PREPROCESSING PROBLEMS | Baseline drift may be mistaken for damage. | `partially_mitigated` | backend/app/signal/processing.py |
| D8 | PREPROCESSING PROBLEMS | Damage may be mistaken for baseline variability. | `partially_mitigated` | backend/app/signal/processing.py |
| D9 | PREPROCESSING PROBLEMS | Normalization may leak information across datasets. | `partially_mitigated` | backend/app/signal/processing.py |
| D10 | PREPROCESSING PROBLEMS | Window selection may be arbitrary. | `partially_mitigated` | backend/app/signal/processing.py |
| D11 | PREPROCESSING PROBLEMS | Time alignment may be imperfect. | `partially_mitigated` | backend/app/signal/processing.py |
| D12 | PREPROCESSING PROBLEMS | Sensor synchronization errors may distort features. | `partially_mitigated` | backend/app/signal/processing.py |
| D13 | PREPROCESSING PROBLEMS | FFT resolution may be insufficient. | `partially_mitigated` | backend/app/signal/processing.py |
| D14 | PREPROCESSING PROBLEMS | Time-frequency representation choice may affect model output. | `partially_mitigated` | backend/app/signal/processing.py |
| D15 | PREPROCESSING PROBLEMS | Matched filtering may assume an excitation model that is imperfect. | `partially_mitigated` | backend/app/signal/processing.py |
| D16 | PREPROCESSING PROBLEMS | Correlation peaks may be ambiguous. | `partially_mitigated` | backend/app/signal/processing.py |
| D17 | PREPROCESSING PROBLEMS | Multiple reflections can create false peaks. | `partially_mitigated` | backend/app/signal/processing.py |
| D18 | PREPROCESSING PROBLEMS | Mode arrivals can create false peaks. | `partially_mitigated` | backend/app/signal/processing.py |
| D19 | PREPROCESSING PROBLEMS | Damage echoes can overlap. | `partially_mitigated` | backend/app/signal/processing.py |
| D20 | PREPROCESSING PROBLEMS | SNR estimation may be biased. | `partially_mitigated` | backend/app/signal/processing.py |
| D21 | PREPROCESSING PROBLEMS | Handcrafted feature extraction may discard information. | `partially_mitigated` | backend/app/signal/processing.py |
| D22 | PREPROCESSING PROBLEMS | Feature extraction may fail under distribution shift. | `partially_mitigated` | backend/app/signal/processing.py |
| D23 | PREPROCESSING PROBLEMS | Fixed preprocessing may be inappropriate for different materials. | `partially_mitigated` | backend/app/signal/processing.py |
| D24 | PREPROCESSING PROBLEMS | Fixed frequency bands may not transfer across structures. | `partially_mitigated` | backend/app/signal/processing.py |
| D25 | PREPROCESSING PROBLEMS | Window duration may not transfer across structures. | `partially_mitigated` | backend/app/signal/processing.py |
| E1 | FEATURE ENGINEERING PROBLEMS | Handcrafted features may be insufficient. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| E2 | FEATURE ENGINEERING PROBLEMS | Features may be correlated. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| E3 | FEATURE ENGINEERING PROBLEMS | Features may be redundant. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| E4 | FEATURE ENGINEERING PROBLEMS | Features may not capture waveform morphology. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| E5 | FEATURE ENGINEERING PROBLEMS | Features may not capture phase information. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| E6 | FEATURE ENGINEERING PROBLEMS | Features may not capture spatial dependencies. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| E7 | FEATURE ENGINEERING PROBLEMS | Features may not capture temporal dependencies. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| E8 | FEATURE ENGINEERING PROBLEMS | Features may not capture multi-mode interactions. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| E9 | FEATURE ENGINEERING PROBLEMS | Features may be sensitive to noise. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| E10 | FEATURE ENGINEERING PROBLEMS | Features may be sensitive to temperature. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| E11 | FEATURE ENGINEERING PROBLEMS | Features may be sensitive to coupling. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| E12 | FEATURE ENGINEERING PROBLEMS | Features may be sensitive to amplitude scaling. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| E13 | FEATURE ENGINEERING PROBLEMS | Features may not generalize to different structures. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| E14 | FEATURE ENGINEERING PROBLEMS | Feature selection may be manually chosen. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| E15 | FEATURE ENGINEERING PROBLEMS | No learned representation benchmark may exist. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| E16 | FEATURE ENGINEERING PROBLEMS | No self-supervised representation benchmark may exist. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| F1 | DATASET PROBLEMS | Training data may be too small. | `partially_mitigated` | scripts/generate_dataset.py; scripts/prepare_lmsd_dataset.py; docs/BENCHMARK_PROTOCOL.md |
| F2 | DATASET PROBLEMS | 30 simulation cases is not enough for strong deep-learning claims. | `partially_mitigated` | scripts/generate_dataset.py; scripts/prepare_lmsd_dataset.py; docs/BENCHMARK_PROTOCOL.md |
| F3 | DATASET PROBLEMS | Defect locations may be insufficiently diverse. | `partially_mitigated` | scripts/generate_dataset.py; scripts/prepare_lmsd_dataset.py; docs/BENCHMARK_PROTOCOL.md |
| F4 | DATASET PROBLEMS | Defect types may be insufficiently diverse. | `partially_mitigated` | scripts/generate_dataset.py; scripts/prepare_lmsd_dataset.py; docs/BENCHMARK_PROTOCOL.md |
| F5 | DATASET PROBLEMS | Defect sizes may be insufficiently diverse. | `partially_mitigated` | scripts/generate_dataset.py; scripts/prepare_lmsd_dataset.py; docs/BENCHMARK_PROTOCOL.md |
| F6 | DATASET PROBLEMS | Defect orientations may be insufficiently diverse. | `partially_mitigated` | scripts/generate_dataset.py; scripts/prepare_lmsd_dataset.py; docs/BENCHMARK_PROTOCOL.md |
| F7 | DATASET PROBLEMS | Material properties may be insufficiently diverse. | `partially_mitigated` | scripts/generate_dataset.py; scripts/prepare_lmsd_dataset.py; docs/BENCHMARK_PROTOCOL.md |
| F8 | DATASET PROBLEMS | Layups may be insufficiently diverse. | `partially_mitigated` | scripts/generate_dataset.py; scripts/prepare_lmsd_dataset.py; docs/BENCHMARK_PROTOCOL.md |
| F9 | DATASET PROBLEMS | Panel geometries may be insufficiently diverse. | `partially_mitigated` | scripts/generate_dataset.py; scripts/prepare_lmsd_dataset.py; docs/BENCHMARK_PROTOCOL.md |
| F10 | DATASET PROBLEMS | Boundary conditions may be insufficiently diverse. | `partially_mitigated` | scripts/generate_dataset.py; scripts/prepare_lmsd_dataset.py; docs/BENCHMARK_PROTOCOL.md |
| F11 | DATASET PROBLEMS | Noise conditions may be insufficiently diverse. | `partially_mitigated` | scripts/generate_dataset.py; scripts/prepare_lmsd_dataset.py; docs/BENCHMARK_PROTOCOL.md |
| F12 | DATASET PROBLEMS | Temperature conditions may be insufficiently diverse. | `partially_mitigated` | scripts/generate_dataset.py; scripts/prepare_lmsd_dataset.py; docs/BENCHMARK_PROTOCOL.md |
| F13 | DATASET PROBLEMS | Loading conditions may be insufficiently diverse. | `partially_mitigated` | scripts/generate_dataset.py; scripts/prepare_lmsd_dataset.py; docs/BENCHMARK_PROTOCOL.md |
| F14 | DATASET PROBLEMS | Manufacturing variability may be missing. | `partially_mitigated` | scripts/generate_dataset.py; scripts/prepare_lmsd_dataset.py; docs/BENCHMARK_PROTOCOL.md |
| F15 | DATASET PROBLEMS | Hardware variability may be missing. | `partially_mitigated` | scripts/generate_dataset.py; scripts/prepare_lmsd_dataset.py; docs/BENCHMARK_PROTOCOL.md |
| F16 | DATASET PROBLEMS | Sensor placement variability may be missing. | `partially_mitigated` | scripts/generate_dataset.py; scripts/prepare_lmsd_dataset.py; docs/BENCHMARK_PROTOCOL.md |
| F17 | DATASET PROBLEMS | Defect placement may be unrealistically clean. | `partially_mitigated` | scripts/generate_dataset.py; scripts/prepare_lmsd_dataset.py; docs/BENCHMARK_PROTOCOL.md |
| F18 | DATASET PROBLEMS | Dataset may contain synthetic artifacts. | `partially_mitigated` | scripts/generate_dataset.py; scripts/prepare_lmsd_dataset.py; docs/BENCHMARK_PROTOCOL.md |
| F19 | DATASET PROBLEMS | Train/test leakage may occur through repeated structures. | `partially_mitigated` | scripts/generate_dataset.py; scripts/prepare_lmsd_dataset.py; docs/BENCHMARK_PROTOCOL.md |
| F20 | DATASET PROBLEMS | Train/test leakage may occur through repeated defect geometry. | `partially_mitigated` | scripts/generate_dataset.py; scripts/prepare_lmsd_dataset.py; docs/BENCHMARK_PROTOCOL.md |
| F21 | DATASET PROBLEMS | Train/test leakage may occur through repeated sensors. | `partially_mitigated` | scripts/generate_dataset.py; scripts/prepare_lmsd_dataset.py; docs/BENCHMARK_PROTOCOL.md |
| F22 | DATASET PROBLEMS | Random train/test splitting may overestimate generalization. | `partially_mitigated` | scripts/generate_dataset.py; scripts/prepare_lmsd_dataset.py; docs/BENCHMARK_PROTOCOL.md |
| F23 | DATASET PROBLEMS | Structure-level splitting may be required. | `partially_mitigated` | scripts/generate_dataset.py; scripts/prepare_lmsd_dataset.py; docs/BENCHMARK_PROTOCOL.md |
| F24 | DATASET PROBLEMS | Defect-level splitting may be required. | `partially_mitigated` | scripts/generate_dataset.py; scripts/prepare_lmsd_dataset.py; docs/BENCHMARK_PROTOCOL.md |
| F25 | DATASET PROBLEMS | Environment-level splitting may be required. | `partially_mitigated` | scripts/generate_dataset.py; scripts/prepare_lmsd_dataset.py; docs/BENCHMARK_PROTOCOL.md |
| F26 | DATASET PROBLEMS | Material-level splitting may be required. | `partially_mitigated` | scripts/generate_dataset.py; scripts/prepare_lmsd_dataset.py; docs/BENCHMARK_PROTOCOL.md |
| F27 | DATASET PROBLEMS | Geometry-level splitting may be required. | `partially_mitigated` | scripts/generate_dataset.py; scripts/prepare_lmsd_dataset.py; docs/BENCHMARK_PROTOCOL.md |
| F28 | DATASET PROBLEMS | Frequency-level extrapolation should be tested. | `partially_mitigated` | scripts/generate_dataset.py; scripts/prepare_lmsd_dataset.py; docs/BENCHMARK_PROTOCOL.md |
| F29 | DATASET PROBLEMS | Unseen-location extrapolation should be tested. | `partially_mitigated` | scripts/generate_dataset.py; scripts/prepare_lmsd_dataset.py; docs/BENCHMARK_PROTOCOL.md |
| F30 | DATASET PROBLEMS | Unseen-defect-type generalization should be tested. | `partially_mitigated` | scripts/generate_dataset.py; scripts/prepare_lmsd_dataset.py; docs/BENCHMARK_PROTOCOL.md |
| F31 | DATASET PROBLEMS | Unseen-material generalization should be tested. | `partially_mitigated` | scripts/generate_dataset.py; scripts/prepare_lmsd_dataset.py; docs/BENCHMARK_PROTOCOL.md |
| F32 | DATASET PROBLEMS | Unseen-panel generalization should be tested. | `partially_mitigated` | scripts/generate_dataset.py; scripts/prepare_lmsd_dataset.py; docs/BENCHMARK_PROTOCOL.md |
| F33 | DATASET PROBLEMS | Unseen-temperature generalization should be tested. | `partially_mitigated` | scripts/generate_dataset.py; scripts/prepare_lmsd_dataset.py; docs/BENCHMARK_PROTOCOL.md |
| F34 | DATASET PROBLEMS | Long-term drift data may be missing. | `partially_mitigated` | scripts/generate_dataset.py; scripts/prepare_lmsd_dataset.py; docs/BENCHMARK_PROTOCOL.md |
| F35 | DATASET PROBLEMS | Real-world field data may be insufficient. | `partially_mitigated` | scripts/generate_dataset.py; scripts/prepare_lmsd_dataset.py; docs/BENCHMARK_PROTOCOL.md |
| F36 | DATASET PROBLEMS | Ground-truth labels may be noisy. | `partially_mitigated` | scripts/generate_dataset.py; scripts/prepare_lmsd_dataset.py; docs/BENCHMARK_PROTOCOL.md |
| F37 | DATASET PROBLEMS | Ground-truth defect boundaries may be uncertain. | `partially_mitigated` | scripts/generate_dataset.py; scripts/prepare_lmsd_dataset.py; docs/BENCHMARK_PROTOCOL.md |
| F38 | DATASET PROBLEMS | Real defect shape may not be precisely known. | `partially_mitigated` | scripts/generate_dataset.py; scripts/prepare_lmsd_dataset.py; docs/BENCHMARK_PROTOCOL.md |
| F39 | DATASET PROBLEMS | Class imbalance may occur. | `partially_mitigated` | scripts/generate_dataset.py; scripts/prepare_lmsd_dataset.py; docs/BENCHMARK_PROTOCOL.md |
| F40 | DATASET PROBLEMS | Healthy samples may dominate the dataset. | `partially_mitigated` | scripts/generate_dataset.py; scripts/prepare_lmsd_dataset.py; docs/BENCHMARK_PROTOCOL.md |
| F41 | DATASET PROBLEMS | Rare damage states may be underrepresented. | `partially_mitigated` | scripts/generate_dataset.py; scripts/prepare_lmsd_dataset.py; docs/BENCHMARK_PROTOCOL.md |
| F42 | DATASET PROBLEMS | Severe damage may be easier than subtle damage, causing optimistic metrics. | `partially_mitigated` | scripts/generate_dataset.py; scripts/prepare_lmsd_dataset.py; docs/BENCHMARK_PROTOCOL.md |
| F43 | DATASET PROBLEMS | Public datasets may use different acquisition systems. | `partially_mitigated` | scripts/generate_dataset.py; scripts/prepare_lmsd_dataset.py; docs/BENCHMARK_PROTOCOL.md |
| F44 | DATASET PROBLEMS | Different datasets may use different coordinate systems. | `partially_mitigated` | scripts/generate_dataset.py; scripts/prepare_lmsd_dataset.py; docs/BENCHMARK_PROTOCOL.md |
| F45 | DATASET PROBLEMS | Different datasets may have different sampling rates. | `partially_mitigated` | scripts/generate_dataset.py; scripts/prepare_lmsd_dataset.py; docs/BENCHMARK_PROTOCOL.md |
| F46 | DATASET PROBLEMS | Different datasets may have different sensor layouts. | `partially_mitigated` | scripts/generate_dataset.py; scripts/prepare_lmsd_dataset.py; docs/BENCHMARK_PROTOCOL.md |
| F47 | DATASET PROBLEMS | Different datasets may have different excitation schemes. | `partially_mitigated` | scripts/generate_dataset.py; scripts/prepare_lmsd_dataset.py; docs/BENCHMARK_PROTOCOL.md |
| F48 | DATASET PROBLEMS | Different datasets may have different material layups. | `partially_mitigated` | scripts/generate_dataset.py; scripts/prepare_lmsd_dataset.py; docs/BENCHMARK_PROTOCOL.md |
| F49 | DATASET PROBLEMS | Cross-dataset benchmark may be required. | `partially_mitigated` | scripts/generate_dataset.py; scripts/prepare_lmsd_dataset.py; docs/BENCHMARK_PROTOCOL.md |
| G1 | REAL-WORLD DATA PROBLEMS | Sim-to-real gap. | `requires_physical_validation` | backend/app/digital_twin/discrepancy.py; docs/MULTIFIDELITY.md |
| G2 | REAL-WORLD DATA PROBLEMS | Synthetic and real feature distributions may differ. | `requires_physical_validation` | backend/app/digital_twin/discrepancy.py; docs/MULTIFIDELITY.md |
| G3 | REAL-WORLD DATA PROBLEMS | Real waveforms may contain unmodeled artifacts. | `requires_physical_validation` | backend/app/digital_twin/discrepancy.py; docs/MULTIFIDELITY.md |
| G4 | REAL-WORLD DATA PROBLEMS | Real sensor transfer functions may differ. | `requires_physical_validation` | backend/app/digital_twin/discrepancy.py; docs/MULTIFIDELITY.md |
| G5 | REAL-WORLD DATA PROBLEMS | Real environmental variation may dominate damage signal. | `requires_physical_validation` | backend/app/digital_twin/discrepancy.py; docs/MULTIFIDELITY.md |
| G6 | REAL-WORLD DATA PROBLEMS | Real damage may differ from modeled damage. | `requires_physical_validation` | backend/app/digital_twin/discrepancy.py; docs/MULTIFIDELITY.md |
| G7 | REAL-WORLD DATA PROBLEMS | Public dataset performance may not transfer to your hardware. | `requires_physical_validation` | backend/app/digital_twin/discrepancy.py; docs/MULTIFIDELITY.md |
| G8 | REAL-WORLD DATA PROBLEMS | Your hardware data may not transfer to public datasets. | `requires_physical_validation` | backend/app/digital_twin/discrepancy.py; docs/MULTIFIDELITY.md |
| G9 | REAL-WORLD DATA PROBLEMS | Domain adaptation may be required. | `requires_physical_validation` | backend/app/digital_twin/discrepancy.py; docs/MULTIFIDELITY.md |
| G10 | REAL-WORLD DATA PROBLEMS | Domain adaptation itself can erase damage-sensitive information. | `requires_physical_validation` | backend/app/digital_twin/discrepancy.py; docs/MULTIFIDELITY.md |
| G11 | REAL-WORLD DATA PROBLEMS | Domain adaptation may cause negative transfer. | `requires_physical_validation` | backend/app/digital_twin/discrepancy.py; docs/MULTIFIDELITY.md |
| G12 | REAL-WORLD DATA PROBLEMS | No-label adaptation is difficult. | `requires_physical_validation` | backend/app/digital_twin/discrepancy.py; docs/MULTIFIDELITY.md |
| G13 | REAL-WORLD DATA PROBLEMS | Few-shot adaptation may still overfit. | `requires_physical_validation` | backend/app/digital_twin/discrepancy.py; docs/MULTIFIDELITY.md |
| G14 | REAL-WORLD DATA PROBLEMS | Cross-panel adaptation may fail. | `requires_physical_validation` | backend/app/digital_twin/discrepancy.py; docs/MULTIFIDELITY.md |
| G15 | REAL-WORLD DATA PROBLEMS | Cross-material adaptation may fail. | `requires_physical_validation` | backend/app/digital_twin/discrepancy.py; docs/MULTIFIDELITY.md |
| G16 | REAL-WORLD DATA PROBLEMS | Cross-layup adaptation may fail. | `requires_physical_validation` | backend/app/digital_twin/discrepancy.py; docs/MULTIFIDELITY.md |
| G17 | REAL-WORLD DATA PROBLEMS | Cross-hardware adaptation may fail. | `requires_physical_validation` | backend/app/digital_twin/discrepancy.py; docs/MULTIFIDELITY.md |
| G18 | REAL-WORLD DATA PROBLEMS | Cross-temperature adaptation may fail. | `requires_physical_validation` | backend/app/digital_twin/discrepancy.py; docs/MULTIFIDELITY.md |
| G19 | REAL-WORLD DATA PROBLEMS | Cross-frequency adaptation may fail. | `requires_physical_validation` | backend/app/digital_twin/discrepancy.py; docs/MULTIFIDELITY.md |
| G20 | REAL-WORLD DATA PROBLEMS | Time-varying domain drift may occur. | `requires_physical_validation` | backend/app/digital_twin/discrepancy.py; docs/MULTIFIDELITY.md |
| G21 | REAL-WORLD DATA PROBLEMS | Lifelong adaptation may be required. | `requires_physical_validation` | backend/app/digital_twin/discrepancy.py; docs/MULTIFIDELITY.md |
| G22 | REAL-WORLD DATA PROBLEMS | Online adaptation may destabilize the model. | `requires_physical_validation` | backend/app/digital_twin/discrepancy.py; docs/MULTIFIDELITY.md |
| G23 | REAL-WORLD DATA PROBLEMS | Catastrophic forgetting may occur during adaptation. | `requires_physical_validation` | backend/app/digital_twin/discrepancy.py; docs/MULTIFIDELITY.md |
| G24 | REAL-WORLD DATA PROBLEMS | Real-time calibration may be difficult. | `requires_physical_validation` | backend/app/digital_twin/discrepancy.py; docs/MULTIFIDELITY.md |
| H1 | MACHINE LEARNING MODEL PROBLEMS | Model architecture may be too simple. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| H2 | MACHINE LEARNING MODEL PROBLEMS | Model may overfit simulation data. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| H3 | MACHINE LEARNING MODEL PROBLEMS | Model may learn simulator shortcuts. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| H4 | MACHINE LEARNING MODEL PROBLEMS | Model may memorize sensor geometry. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| H5 | MACHINE LEARNING MODEL PROBLEMS | Model may memorize defect positions. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| H6 | MACHINE LEARNING MODEL PROBLEMS | Model may memorize noise patterns. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| H7 | MACHINE LEARNING MODEL PROBLEMS | Model may learn amplitude instead of damage. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| H8 | MACHINE LEARNING MODEL PROBLEMS | Model may rely on environmental artifacts. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| H9 | MACHINE LEARNING MODEL PROBLEMS | Model may not generalize spatially. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| H10 | MACHINE LEARNING MODEL PROBLEMS | Model may not generalize temporally. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| H11 | MACHINE LEARNING MODEL PROBLEMS | Model may not generalize across structures. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| H12 | MACHINE LEARNING MODEL PROBLEMS | Model may not generalize across materials. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| H13 | MACHINE LEARNING MODEL PROBLEMS | Model may not generalize across sensor layouts. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| H14 | MACHINE LEARNING MODEL PROBLEMS | Model may not generalize across acquisition systems. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| H15 | MACHINE LEARNING MODEL PROBLEMS | Model may not generalize to unseen defect types. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| H16 | MACHINE LEARNING MODEL PROBLEMS | Model may not generalize to unseen defect sizes. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| H17 | MACHINE LEARNING MODEL PROBLEMS | Model may not generalize to multiple defects. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| H18 | MACHINE LEARNING MODEL PROBLEMS | Model may not handle missing sensors. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| H19 | MACHINE LEARNING MODEL PROBLEMS | Model may not handle noisy channels. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| H20 | MACHINE LEARNING MODEL PROBLEMS | Model may not handle corrupted channels. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| H21 | MACHINE LEARNING MODEL PROBLEMS | Model may not handle sensor failures. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| H22 | MACHINE LEARNING MODEL PROBLEMS | Model may not handle unknown hardware. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| H23 | MACHINE LEARNING MODEL PROBLEMS | Model may not handle missing metadata. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| H24 | MACHINE LEARNING MODEL PROBLEMS | Model may not handle uncertain coordinates. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| H25 | MACHINE LEARNING MODEL PROBLEMS | Model may not represent spatial structure optimally. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| H26 | MACHINE LEARNING MODEL PROBLEMS | Model may not represent temporal structure optimally. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| H27 | MACHINE LEARNING MODEL PROBLEMS | Model may not represent frequency structure optimally. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| H28 | MACHINE LEARNING MODEL PROBLEMS | Model may not combine spatial, temporal and spectral information. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| H29 | MACHINE LEARNING MODEL PROBLEMS | Model may require too much labeled data. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| H30 | MACHINE LEARNING MODEL PROBLEMS | Model may be too computationally expensive. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| H31 | MACHINE LEARNING MODEL PROBLEMS | Model may be too large for edge deployment. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| H32 | MACHINE LEARNING MODEL PROBLEMS | Model may be too slow for active planning. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| H33 | MACHINE LEARNING MODEL PROBLEMS | Model latency may be underestimated. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| H34 | MACHINE LEARNING MODEL PROBLEMS | Training may be unstable. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| H35 | MACHINE LEARNING MODEL PROBLEMS | Hyperparameter tuning may overfit benchmark data. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| H36 | MACHINE LEARNING MODEL PROBLEMS | Architecture search may implicitly leak validation knowledge. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| I1 | PHYSICS-INFORMED ML PROBLEMS | Physics constraints may be only descriptive, not enforced. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| I2 | PHYSICS-INFORMED ML PROBLEMS | Physics features may be incorrectly specified. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| I3 | PHYSICS-INFORMED ML PROBLEMS | Wrong physical assumptions can bias the model. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| I4 | PHYSICS-INFORMED ML PROBLEMS | Physics loss weighting may be arbitrary. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| I5 | PHYSICS-INFORMED ML PROBLEMS | Physics loss may dominate data loss. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| I6 | PHYSICS-INFORMED ML PROBLEMS | Data loss may dominate physics loss. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| I7 | PHYSICS-INFORMED ML PROBLEMS | Physics model may be inaccurate. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| I8 | PHYSICS-INFORMED ML PROBLEMS | Model may satisfy a simplified physics model but fail reality. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| I9 | PHYSICS-INFORMED ML PROBLEMS | Physics constraints may reduce flexibility. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| I10 | PHYSICS-INFORMED ML PROBLEMS | Physics-informed model may be harder to train. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| I11 | PHYSICS-INFORMED ML PROBLEMS | Physics-informed model may require differentiable physics. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| I12 | PHYSICS-INFORMED ML PROBLEMS | Differentiable simulator may be computationally expensive. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| I13 | PHYSICS-INFORMED ML PROBLEMS | Physics constraints may need to vary by material. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| I14 | PHYSICS-INFORMED ML PROBLEMS | Directional anisotropy may need explicit representation. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| I15 | PHYSICS-INFORMED ML PROBLEMS | Frequency-dependent physics may need explicit representation. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| I16 | PHYSICS-INFORMED ML PROBLEMS | Multiple wave modes may need explicit representation. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| I17 | PHYSICS-INFORMED ML PROBLEMS | Mode conversion may need explicit representation. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| I18 | PHYSICS-INFORMED ML PROBLEMS | Boundary conditions may need to be represented. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| I19 | PHYSICS-INFORMED ML PROBLEMS | Physics consistency should be measured quantitatively, not just claimed. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| J1 | GRAPH / SPATIAL MODEL PROBLEMS | Sensor graph definition may be arbitrary. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| J2 | GRAPH / SPATIAL MODEL PROBLEMS | Fully connected graph may introduce irrelevant relationships. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| J3 | GRAPH / SPATIAL MODEL PROBLEMS | Distance-only graph may ignore wave propagation. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| J4 | GRAPH / SPATIAL MODEL PROBLEMS | Geometry-only graph may ignore anisotropy. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| J5 | GRAPH / SPATIAL MODEL PROBLEMS | Static graph may be inappropriate for changing frequencies. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| J6 | GRAPH / SPATIAL MODEL PROBLEMS | Edge weights may not represent physical coupling. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| J7 | GRAPH / SPATIAL MODEL PROBLEMS | Directionality may be lost. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| J8 | GRAPH / SPATIAL MODEL PROBLEMS | Sensor topology may change between deployments. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| J9 | GRAPH / SPATIAL MODEL PROBLEMS | Graph may not handle missing sensors. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| J10 | GRAPH / SPATIAL MODEL PROBLEMS | Graph may not handle new sensors. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| J11 | GRAPH / SPATIAL MODEL PROBLEMS | Graph may not handle irregular sensor layouts. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| J12 | GRAPH / SPATIAL MODEL PROBLEMS | Graph may not handle movable sensors. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| J13 | GRAPH / SPATIAL MODEL PROBLEMS | Graph may not represent candidate experiment paths. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| J14 | GRAPH / SPATIAL MODEL PROBLEMS | Graph may not represent defect nodes or latent fields. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| J15 | GRAPH / SPATIAL MODEL PROBLEMS | Graph model may merely reproduce prior GNN work. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| J16 | GRAPH / SPATIAL MODEL PROBLEMS | Graph novelty must therefore come from the actual closed-loop decision/inference contribution, not simply "we used a GNN." and domain-adaptive relational graph approaches. Therefore these components cannot safely be claimed as standalone novelty. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| K1 | MULTIMODAL LEARNING PROBLEMS | Multiple sensors may have incompatible sampling rates. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| K2 | MULTIMODAL LEARNING PROBLEMS | Multiple modalities may have different timestamps. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| K3 | MULTIMODAL LEARNING PROBLEMS | Modalities may have different noise properties. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| K4 | MULTIMODAL LEARNING PROBLEMS | Some modalities may be absent. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| K5 | MULTIMODAL LEARNING PROBLEMS | Some modalities may be unreliable. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| K6 | MULTIMODAL LEARNING PROBLEMS | Fusion may be dominated by one modality. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| K7 | MULTIMODAL LEARNING PROBLEMS | Early fusion may create huge dimensionality. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| K8 | MULTIMODAL LEARNING PROBLEMS | Late fusion may lose cross-modal interactions. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| K9 | MULTIMODAL LEARNING PROBLEMS | Cross-modal attention may overfit. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| K10 | MULTIMODAL LEARNING PROBLEMS | Modality failure needs graceful degradation. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| K11 | MULTIMODAL LEARNING PROBLEMS | Modality availability may change between structures. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| K12 | MULTIMODAL LEARNING PROBLEMS | Camera-based damage may only reveal surface evidence. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| K13 | MULTIMODAL LEARNING PROBLEMS | Acoustic data may reveal subsurface evidence. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| K14 | MULTIMODAL LEARNING PROBLEMS | Vision and acoustics may disagree. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| K15 | MULTIMODAL LEARNING PROBLEMS | System must decide how disagreement affects posterior belief. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| K16 | MULTIMODAL LEARNING PROBLEMS | Adding modalities may increase cost. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| K17 | MULTIMODAL LEARNING PROBLEMS | Planner must consider the cost of switching modalities. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| K18 | MULTIMODAL LEARNING PROBLEMS | Multimodal sensing alone is not novel. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| L1 | BASELINE / REFERENCE MODEL PROBLEMS | Random baseline may be too weak. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| L2 | BASELINE / REFERENCE MODEL PROBLEMS | Uniform-grid baseline may be too weak. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| L3 | BASELINE / REFERENCE MODEL PROBLEMS | Need uncertainty-driven baseline. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| L4 | BASELINE / REFERENCE MODEL PROBLEMS | Need greedy information-gain baseline. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| L5 | BASELINE / REFERENCE MODEL PROBLEMS | Need Bayesian experimental-design baseline. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| L6 | BASELINE / REFERENCE MODEL PROBLEMS | Need learned acquisition-policy baseline. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| L7 | BASELINE / REFERENCE MODEL PROBLEMS | Need non-physics neural baseline. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| L8 | BASELINE / REFERENCE MODEL PROBLEMS | Need physics-informed neural baseline. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| L9 | BASELINE / REFERENCE MODEL PROBLEMS | Need classical signal-processing baseline. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| L10 | BASELINE / REFERENCE MODEL PROBLEMS | Need potentially likelihood-free Bayesian baseline. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| L11 | BASELINE / REFERENCE MODEL PROBLEMS | Need cross-dataset baseline. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| L12 | BASELINE / REFERENCE MODEL PROBLEMS | Need sensor-failure baseline. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| L13 | BASELINE / REFERENCE MODEL PROBLEMS | Need fixed-budget benchmark. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| L14 | BASELINE / REFERENCE MODEL PROBLEMS | Need fixed-time benchmark. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| L15 | BASELINE / REFERENCE MODEL PROBLEMS | Need fixed-cost benchmark. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| L16 | BASELINE / REFERENCE MODEL PROBLEMS | Need fixed-number-of-measurements benchmark. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| L17 | BASELINE / REFERENCE MODEL PROBLEMS | Need fair computational-budget comparison. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| L18 | BASELINE / REFERENCE MODEL PROBLEMS | Need identical sensor/hardware assumptions across methods. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| L19 | BASELINE / REFERENCE MODEL PROBLEMS | Need identical train/test splits. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| L20 | BASELINE / REFERENCE MODEL PROBLEMS | Need statistical significance analysis. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| M1 | BAYESIAN INFERENCE PROBLEMS | Prior distribution may be unrealistic. | `partially_mitigated` | backend/app/inference; backend/tests/test_inference.py |
| M2 | BAYESIAN INFERENCE PROBLEMS | Uniform prior may not reflect real structures. | `partially_mitigated` | backend/app/inference; backend/tests/test_inference.py |
| M3 | BAYESIAN INFERENCE PROBLEMS | Prior may need application-specific information. | `partially_mitigated` | backend/app/inference; backend/tests/test_inference.py |
| M4 | BAYESIAN INFERENCE PROBLEMS | Prior uncertainty may be under-modeled. | `partially_mitigated` | backend/app/inference; backend/tests/test_inference.py |
| M5 | BAYESIAN INFERENCE PROBLEMS | Likelihood model may be misspecified. | `partially_mitigated` | backend/app/inference; backend/tests/test_inference.py |
| M6 | BAYESIAN INFERENCE PROBLEMS | Likelihood calibration may be poor. | `partially_mitigated` | backend/app/inference; backend/tests/test_inference.py |
| M7 | BAYESIAN INFERENCE PROBLEMS | Likelihood may not capture all physical variability. | `partially_mitigated` | backend/app/inference; backend/tests/test_inference.py |
| M8 | BAYESIAN INFERENCE PROBLEMS | Measurements may not be conditionally independent. | `partially_mitigated` | backend/app/inference; backend/tests/test_inference.py |
| M9 | BAYESIAN INFERENCE PROBLEMS | Sequential updates can compound model error. | `partially_mitigated` | backend/app/inference; backend/tests/test_inference.py |
| M10 | BAYESIAN INFERENCE PROBLEMS | Posterior can become overconfident. | `implemented_and_tested` | backend/app/inference; backend/tests/test_inference.py |
| M11 | BAYESIAN INFERENCE PROBLEMS | Posterior may collapse around the wrong hypothesis. | `partially_mitigated` | backend/app/inference; backend/tests/test_inference.py |
| M12 | BAYESIAN INFERENCE PROBLEMS | Model mismatch can produce false certainty. | `partially_mitigated` | backend/app/inference; backend/tests/test_inference.py |
| M13 | BAYESIAN INFERENCE PROBLEMS | Single measurement may dominate posterior. | `partially_mitigated` | backend/app/inference; backend/tests/test_inference.py |
| M14 | BAYESIAN INFERENCE PROBLEMS | Numerical underflow may affect likelihood calculations. | `implemented_and_tested` | backend/app/inference; backend/tests/test_inference.py |
| M15 | BAYESIAN INFERENCE PROBLEMS | Posterior resolution may be limited by grid resolution. | `partially_mitigated` | backend/app/inference; backend/tests/test_inference.py |
| M16 | BAYESIAN INFERENCE PROBLEMS | Grid discretization creates localization quantization. | `partially_mitigated` | backend/app/inference; backend/tests/test_inference.py |
| M17 | BAYESIAN INFERENCE PROBLEMS | Continuous defect coordinates may be needed. | `partially_mitigated` | backend/app/inference; backend/tests/test_inference.py |
| M18 | BAYESIAN INFERENCE PROBLEMS | Posterior may need to represent defect extent. | `partially_mitigated` | backend/app/inference; backend/tests/test_inference.py |
| M19 | BAYESIAN INFERENCE PROBLEMS | Posterior may need to represent multiple defects. | `implemented_and_tested` | backend/app/inference; backend/tests/test_inference.py |
| M20 | BAYESIAN INFERENCE PROBLEMS | Posterior should potentially represent defect type and severity jointly. | `partially_mitigated` | backend/app/inference; backend/tests/test_inference.py |
| M21 | BAYESIAN INFERENCE PROBLEMS | Exact posterior uncertainty may not be tractable. | `partially_mitigated` | backend/app/inference; backend/tests/test_inference.py |
| M22 | BAYESIAN INFERENCE PROBLEMS | Approximate Bayesian methods may be necessary. | `partially_mitigated` | backend/app/inference; backend/tests/test_inference.py |
| M23 | BAYESIAN INFERENCE PROBLEMS | Likelihood-free inference could be explored. | `partially_mitigated` | backend/app/inference; backend/tests/test_inference.py |
| M24 | BAYESIAN INFERENCE PROBLEMS | Bayesian computation cost may grow with candidate count. identification, meaning a handcrafted explicit likelihood is not the only available direction. | `partially_mitigated` | backend/app/inference; backend/tests/test_inference.py |
| N1 | UNCERTAINTY QUANTIFICATION PROBLEMS | Current confidence is heuristic. | `partially_mitigated` | backend/app/inference/calibration.py; scripts/neo_calibration.py |
| N2 | UNCERTAINTY QUANTIFICATION PROBLEMS | Confidence may not be statistically calibrated. | `partially_mitigated` | backend/app/inference/calibration.py; scripts/neo_calibration.py |
| N3 | UNCERTAINTY QUANTIFICATION PROBLEMS | Confidence may not correspond to empirical correctness. | `partially_mitigated` | backend/app/inference/calibration.py; scripts/neo_calibration.py |
| N4 | UNCERTAINTY QUANTIFICATION PROBLEMS | Model uncertainty may be missing. | `partially_mitigated` | backend/app/inference/calibration.py; scripts/neo_calibration.py |
| N5 | UNCERTAINTY QUANTIFICATION PROBLEMS | Data uncertainty may be missing. | `partially_mitigated` | backend/app/inference/calibration.py; scripts/neo_calibration.py |
| N6 | UNCERTAINTY QUANTIFICATION PROBLEMS | Physics-model uncertainty may be missing. | `partially_mitigated` | backend/app/inference/calibration.py; scripts/neo_calibration.py |
| N7 | UNCERTAINTY QUANTIFICATION PROBLEMS | Sensor uncertainty may be missing. | `partially_mitigated` | backend/app/inference/calibration.py; scripts/neo_calibration.py |
| N8 | UNCERTAINTY QUANTIFICATION PROBLEMS | Domain uncertainty may be missing. | `partially_mitigated` | backend/app/inference/calibration.py; scripts/neo_calibration.py |
| N9 | UNCERTAINTY QUANTIFICATION PROBLEMS | Posterior uncertainty may be incorrectly interpreted as model confidence. | `partially_mitigated` | backend/app/inference/calibration.py; scripts/neo_calibration.py |
| N10 | UNCERTAINTY QUANTIFICATION PROBLEMS | Need confidence calibration. | `implemented_and_tested` | backend/app/inference/calibration.py; scripts/neo_calibration.py |
| N11 | UNCERTAINTY QUANTIFICATION PROBLEMS | Need reliability diagrams. | `partially_mitigated` | backend/app/inference/calibration.py; scripts/neo_calibration.py |
| N12 | UNCERTAINTY QUANTIFICATION PROBLEMS | Need expected calibration error. | `partially_mitigated` | backend/app/inference/calibration.py; scripts/neo_calibration.py |
| N13 | UNCERTAINTY QUANTIFICATION PROBLEMS | Need calibration under distribution shift. | `partially_mitigated` | backend/app/inference/calibration.py; scripts/neo_calibration.py |
| N14 | UNCERTAINTY QUANTIFICATION PROBLEMS | Need uncertainty under sensor failure. | `partially_mitigated` | backend/app/inference/calibration.py; scripts/neo_calibration.py |
| N15 | UNCERTAINTY QUANTIFICATION PROBLEMS | Need uncertainty under noise increase. | `partially_mitigated` | backend/app/inference/calibration.py; scripts/neo_calibration.py |
| N16 | UNCERTAINTY QUANTIFICATION PROBLEMS | Need uncertainty under unseen defect types. | `partially_mitigated` | backend/app/inference/calibration.py; scripts/neo_calibration.py |
| N17 | UNCERTAINTY QUANTIFICATION PROBLEMS | Need uncertainty under unseen structures. | `partially_mitigated` | backend/app/inference/calibration.py; scripts/neo_calibration.py |
| N18 | UNCERTAINTY QUANTIFICATION PROBLEMS | Need confidence intervals for localization. | `implemented_and_tested` | backend/app/inference/calibration.py; scripts/neo_calibration.py |
| N19 | UNCERTAINTY QUANTIFICATION PROBLEMS | Need prediction regions rather than only point predictions. | `implemented_and_tested` | backend/app/inference/calibration.py; scripts/neo_calibration.py |
| N20 | UNCERTAINTY QUANTIFICATION PROBLEMS | Need coverage guarantees where possible. | `partially_mitigated` | backend/app/inference/calibration.py; scripts/neo_calibration.py |
| N21 | UNCERTAINTY QUANTIFICATION PROBLEMS | Need sharpness analysis. | `partially_mitigated` | backend/app/inference/calibration.py; scripts/neo_calibration.py |
| N22 | UNCERTAINTY QUANTIFICATION PROBLEMS | Need calibration after domain adaptation. | `partially_mitigated` | backend/app/inference/calibration.py; scripts/neo_calibration.py |
| O1 | OUT-OF-DISTRIBUTION / UNKNOWN DAMAGE PROBLEMS | Model may confidently predict a class it has never seen. | `partially_mitigated` | backend/app/ood/detection.py; docs/OOD_AND_ABSTENTION.md |
| O2 | OUT-OF-DISTRIBUTION / UNKNOWN DAMAGE PROBLEMS | Unknown defect types may be forced into known classes. | `partially_mitigated` | backend/app/ood/detection.py; docs/OOD_AND_ABSTENTION.md |
| O3 | OUT-OF-DISTRIBUTION / UNKNOWN DAMAGE PROBLEMS | Unknown materials may be classified incorrectly. | `partially_mitigated` | backend/app/ood/detection.py; docs/OOD_AND_ABSTENTION.md |
| O4 | OUT-OF-DISTRIBUTION / UNKNOWN DAMAGE PROBLEMS | Unknown structures may produce false confidence. | `partially_mitigated` | backend/app/ood/detection.py; docs/OOD_AND_ABSTENTION.md |
| O5 | OUT-OF-DISTRIBUTION / UNKNOWN DAMAGE PROBLEMS | Sensor faults may look like damage. | `partially_mitigated` | backend/app/ood/detection.py; docs/OOD_AND_ABSTENTION.md |
| O6 | OUT-OF-DISTRIBUTION / UNKNOWN DAMAGE PROBLEMS | Environmental changes may look like damage. | `partially_mitigated` | backend/app/ood/detection.py; docs/OOD_AND_ABSTENTION.md |
| O7 | OUT-OF-DISTRIBUTION / UNKNOWN DAMAGE PROBLEMS | System currently needs an explicit abstention strategy. | `implemented_and_tested` | backend/app/ood/detection.py; docs/OOD_AND_ABSTENTION.md |
| O8 | OUT-OF-DISTRIBUTION / UNKNOWN DAMAGE PROBLEMS | Need OOD detection. | `implemented_and_tested` | backend/app/ood/detection.py; docs/OOD_AND_ABSTENTION.md |
| O9 | OUT-OF-DISTRIBUTION / UNKNOWN DAMAGE PROBLEMS | Need anomaly scoring. | `implemented_and_tested` | backend/app/ood/detection.py; docs/OOD_AND_ABSTENTION.md |
| O10 | OUT-OF-DISTRIBUTION / UNKNOWN DAMAGE PROBLEMS | Need reject-option classification. | `implemented_and_tested` | backend/app/ood/detection.py; docs/OOD_AND_ABSTENTION.md |
| O11 | OUT-OF-DISTRIBUTION / UNKNOWN DAMAGE PROBLEMS | Need "insufficient evidence" output. | `implemented_and_tested` | backend/app/ood/detection.py; docs/OOD_AND_ABSTENTION.md |
| O12 | OUT-OF-DISTRIBUTION / UNKNOWN DAMAGE PROBLEMS | Need "request another measurement" output. | `implemented_and_tested` | backend/app/ood/detection.py; docs/OOD_AND_ABSTENTION.md |
| O13 | OUT-OF-DISTRIBUTION / UNKNOWN DAMAGE PROBLEMS | Need "human inspection required" output. | `implemented_and_tested` | backend/app/ood/detection.py; docs/OOD_AND_ABSTENTION.md |
| O14 | OUT-OF-DISTRIBUTION / UNKNOWN DAMAGE PROBLEMS | OOD threshold needs calibration. | `partially_mitigated` | backend/app/ood/detection.py; docs/OOD_AND_ABSTENTION.md |
| O15 | OUT-OF-DISTRIBUTION / UNKNOWN DAMAGE PROBLEMS | OOD detector itself may fail under domain shift. | `partially_mitigated` | backend/app/ood/detection.py; docs/OOD_AND_ABSTENTION.md |
| P1 | ACTIVE SENSING / EXPERIMENT DESIGN PROBLEMS | Candidate experiment space may be enormous. | `partially_mitigated` | backend/app/active_learning/neo_planner.py; backend/app/safety/constraints.py |
| P2 | ACTIVE SENSING / EXPERIMENT DESIGN PROBLEMS | Candidate evaluation may be computationally expensive. | `partially_mitigated` | backend/app/active_learning/neo_planner.py; backend/app/safety/constraints.py |
| P3 | ACTIVE SENSING / EXPERIMENT DESIGN PROBLEMS | Current score contains manually selected weights. | `partially_mitigated` | backend/app/active_learning/neo_planner.py; backend/app/safety/constraints.py |
| P4 | ACTIVE SENSING / EXPERIMENT DESIGN PROBLEMS | Manual weights may not generalize across applications. | `partially_mitigated` | backend/app/active_learning/neo_planner.py; backend/app/safety/constraints.py |
| P5 | ACTIVE SENSING / EXPERIMENT DESIGN PROBLEMS | Information gain may not equal engineering value. | `partially_mitigated` | backend/app/active_learning/neo_planner.py; backend/app/safety/constraints.py |
| P6 | ACTIVE SENSING / EXPERIMENT DESIGN PROBLEMS | Entropy reduction may not equal defect-detection value. | `partially_mitigated` | backend/app/active_learning/neo_planner.py; backend/app/safety/constraints.py |
| P7 | ACTIVE SENSING / EXPERIMENT DESIGN PROBLEMS | An experiment can reduce entropy but fail to improve localization. | `partially_mitigated` | backend/app/active_learning/neo_planner.py; backend/app/safety/constraints.py |
| P8 | ACTIVE SENSING / EXPERIMENT DESIGN PROBLEMS | Information gain may favor already highly probable hypotheses. | `partially_mitigated` | backend/app/active_learning/neo_planner.py; backend/app/safety/constraints.py |
| P9 | ACTIVE SENSING / EXPERIMENT DESIGN PROBLEMS | Rare but critical hypotheses may be ignored. | `partially_mitigated` | backend/app/active_learning/neo_planner.py; backend/app/safety/constraints.py |
| P10 | ACTIVE SENSING / EXPERIMENT DESIGN PROBLEMS | Worst-case risk may matter more than expected information. | `partially_mitigated` | backend/app/active_learning/neo_planner.py; backend/app/safety/constraints.py |
| P11 | ACTIVE SENSING / EXPERIMENT DESIGN PROBLEMS | Bayesian expected utility may be more appropriate in safety-critical use. | `partially_mitigated` | backend/app/active_learning/neo_planner.py; backend/app/safety/constraints.py |
| P12 | ACTIVE SENSING / EXPERIMENT DESIGN PROBLEMS | Physical cost may be incompletely modeled. | `implemented_and_tested` | backend/app/active_learning/neo_planner.py; backend/app/safety/constraints.py |
| P13 | ACTIVE SENSING / EXPERIMENT DESIGN PROBLEMS | Travel distance may be incomplete. | `implemented_and_tested` | backend/app/active_learning/neo_planner.py; backend/app/safety/constraints.py |
| P14 | ACTIVE SENSING / EXPERIMENT DESIGN PROBLEMS | Energy cost may be incomplete. | `implemented_and_tested` | backend/app/active_learning/neo_planner.py; backend/app/safety/constraints.py |
| P15 | ACTIVE SENSING / EXPERIMENT DESIGN PROBLEMS | Measurement time may be incomplete. | `implemented_and_tested` | backend/app/active_learning/neo_planner.py; backend/app/safety/constraints.py |
| P16 | ACTIVE SENSING / EXPERIMENT DESIGN PROBLEMS | Sensor switching cost may be incomplete. | `partially_mitigated` | backend/app/active_learning/neo_planner.py; backend/app/safety/constraints.py |
| P17 | ACTIVE SENSING / EXPERIMENT DESIGN PROBLEMS | Operator interaction cost may be ignored. | `partially_mitigated` | backend/app/active_learning/neo_planner.py; backend/app/safety/constraints.py |
| P18 | ACTIVE SENSING / EXPERIMENT DESIGN PROBLEMS | Safety risk may be ignored. | `partially_mitigated` | backend/app/active_learning/neo_planner.py; backend/app/safety/constraints.py |
| P19 | ACTIVE SENSING / EXPERIMENT DESIGN PROBLEMS | Access constraints may be ignored. | `partially_mitigated` | backend/app/active_learning/neo_planner.py; backend/app/safety/constraints.py |
| P20 | ACTIVE SENSING / EXPERIMENT DESIGN PROBLEMS | Obstructions may be ignored. | `partially_mitigated` | backend/app/active_learning/neo_planner.py; backend/app/safety/constraints.py |
| P21 | ACTIVE SENSING / EXPERIMENT DESIGN PROBLEMS | Sensor reachability may be ignored. | `partially_mitigated` | backend/app/active_learning/neo_planner.py; backend/app/safety/constraints.py |
| P22 | ACTIVE SENSING / EXPERIMENT DESIGN PROBLEMS | Physical collision constraints may be ignored. | `partially_mitigated` | backend/app/active_learning/neo_planner.py; backend/app/safety/constraints.py |
| P23 | ACTIVE SENSING / EXPERIMENT DESIGN PROBLEMS | Candidate experiments may not be feasible physically. | `implemented_and_tested` | backend/app/active_learning/neo_planner.py; backend/app/safety/constraints.py |
| P24 | ACTIVE SENSING / EXPERIMENT DESIGN PROBLEMS | Probe path planning may be separated from experiment planning. | `partially_mitigated` | backend/app/active_learning/neo_planner.py; backend/app/safety/constraints.py |
| P25 | ACTIVE SENSING / EXPERIMENT DESIGN PROBLEMS | Planner may select geometrically informative but physically impossible actions. | `implemented_and_tested` | backend/app/active_learning/neo_planner.py; backend/app/safety/constraints.py |
| P26 | ACTIVE SENSING / EXPERIMENT DESIGN PROBLEMS | Redundancy penalty may be too simplistic. | `implemented_and_tested` | backend/app/active_learning/neo_planner.py; backend/app/safety/constraints.py |
| P27 | ACTIVE SENSING / EXPERIMENT DESIGN PROBLEMS | Two different experiments may still be statistically redundant. | `partially_mitigated` | backend/app/active_learning/neo_planner.py; backend/app/safety/constraints.py |
| P28 | ACTIVE SENSING / EXPERIMENT DESIGN PROBLEMS | Sequence dependence may be important. | `partially_mitigated` | backend/app/active_learning/neo_planner.py; backend/app/safety/constraints.py |
| P29 | ACTIVE SENSING / EXPERIMENT DESIGN PROBLEMS | Greedy one-step planning may be suboptimal. | `partially_mitigated` | backend/app/active_learning/neo_planner.py; backend/app/safety/constraints.py |
| P30 | ACTIVE SENSING / EXPERIMENT DESIGN PROBLEMS | Multi-step planning may improve performance. | `partially_mitigated` | backend/app/active_learning/neo_planner.py; backend/app/safety/constraints.py |
| P31 | ACTIVE SENSING / EXPERIMENT DESIGN PROBLEMS | Long-horizon planning can explode combinatorially. | `partially_mitigated` | backend/app/active_learning/neo_planner.py; backend/app/safety/constraints.py |
| P32 | ACTIVE SENSING / EXPERIMENT DESIGN PROBLEMS | Planner should potentially use receding-horizon optimization. | `implemented_and_tested` | backend/app/active_learning/neo_planner.py; backend/app/safety/constraints.py |
| P33 | ACTIVE SENSING / EXPERIMENT DESIGN PROBLEMS | Planner could model experiment selection as a POMDP. | `partially_mitigated` | backend/app/active_learning/neo_planner.py; backend/app/safety/constraints.py |
| P34 | ACTIVE SENSING / EXPERIMENT DESIGN PROBLEMS | Planner could use Bayesian optimization. | `partially_mitigated` | backend/app/active_learning/neo_planner.py; backend/app/safety/constraints.py |
| P35 | ACTIVE SENSING / EXPERIMENT DESIGN PROBLEMS | Planner could use contextual bandits. | `partially_mitigated` | backend/app/active_learning/neo_planner.py; backend/app/safety/constraints.py |
| P36 | ACTIVE SENSING / EXPERIMENT DESIGN PROBLEMS | Planner could use reinforcement learning. | `partially_mitigated` | backend/app/active_learning/neo_planner.py; backend/app/safety/constraints.py |
| P37 | ACTIVE SENSING / EXPERIMENT DESIGN PROBLEMS | RL may introduce sample inefficiency. | `partially_mitigated` | backend/app/active_learning/neo_planner.py; backend/app/safety/constraints.py |
| P38 | ACTIVE SENSING / EXPERIMENT DESIGN PROBLEMS | RL may exploit simulator loopholes. | `partially_mitigated` | backend/app/active_learning/neo_planner.py; backend/app/safety/constraints.py |
| P39 | ACTIVE SENSING / EXPERIMENT DESIGN PROBLEMS | RL policy may fail under real-world distribution shift. | `partially_mitigated` | backend/app/active_learning/neo_planner.py; backend/app/safety/constraints.py |
| P40 | ACTIVE SENSING / EXPERIMENT DESIGN PROBLEMS | Learned planners can become opaque. | `partially_mitigated` | backend/app/active_learning/neo_planner.py; backend/app/safety/constraints.py |
| P41 | ACTIVE SENSING / EXPERIMENT DESIGN PROBLEMS | Planner needs safety constraints. | `implemented_and_tested` | backend/app/active_learning/neo_planner.py; backend/app/safety/constraints.py |
| P42 | ACTIVE SENSING / EXPERIMENT DESIGN PROBLEMS | Planner needs hard feasibility constraints. | `implemented_and_tested` | backend/app/active_learning/neo_planner.py; backend/app/safety/constraints.py |
| P43 | ACTIVE SENSING / EXPERIMENT DESIGN PROBLEMS | Planner needs action uncertainty. | `partially_mitigated` | backend/app/active_learning/neo_planner.py; backend/app/safety/constraints.py |
| P44 | ACTIVE SENSING / EXPERIMENT DESIGN PROBLEMS | Planner needs sensor reliability information. | `implemented_and_tested` | backend/app/active_learning/neo_planner.py; backend/app/safety/constraints.py |
| P45 | ACTIVE SENSING / EXPERIMENT DESIGN PROBLEMS | Planner should possibly choose sensing modality as an action. | `implemented_and_tested` | backend/app/active_learning/neo_planner.py; backend/app/safety/constraints.py |
| P46 | ACTIVE SENSING / EXPERIMENT DESIGN PROBLEMS | Planner should possibly choose frequency as an action. | `implemented_and_tested` | backend/app/active_learning/neo_planner.py; backend/app/safety/constraints.py |
| P47 | ACTIVE SENSING / EXPERIMENT DESIGN PROBLEMS | Planner should possibly choose waveform as an action. | `implemented_and_tested` | backend/app/active_learning/neo_planner.py; backend/app/safety/constraints.py |
| P48 | ACTIVE SENSING / EXPERIMENT DESIGN PROBLEMS | Planner should possibly choose amplitude as an action. | `implemented_and_tested` | backend/app/active_learning/neo_planner.py; backend/app/safety/constraints.py |
| P49 | ACTIVE SENSING / EXPERIMENT DESIGN PROBLEMS | Planner should possibly choose source/receiver positions jointly. | `implemented_and_tested` | backend/app/active_learning/neo_planner.py; backend/app/safety/constraints.py |
| P50 | ACTIVE SENSING / EXPERIMENT DESIGN PROBLEMS | Planner should account for uncertainty in physical execution. | `partially_mitigated` | backend/app/active_learning/neo_planner.py; backend/app/safety/constraints.py |
| Q1 | DECISION-THEORETIC PROBLEMS | Information gain is not the same as decision value. | `partially_mitigated` | backend/app/decision/loss.py |
| Q2 | DECISION-THEORETIC PROBLEMS | Localization error is not the same as engineering loss. | `partially_mitigated` | backend/app/decision/loss.py |
| Q3 | DECISION-THEORETIC PROBLEMS | False negative and false positive costs are different. | `implemented_and_tested` | backend/app/decision/loss.py |
| Q4 | DECISION-THEORETIC PROBLEMS | Missing a critical defect may be much more costly than over-inspection. | `implemented_and_tested` | backend/app/decision/loss.py |
| Q5 | DECISION-THEORETIC PROBLEMS | Inspection decisions can depend on structural criticality. | `partially_mitigated` | backend/app/decision/loss.py |
| Q6 | DECISION-THEORETIC PROBLEMS | Damage severity should affect decision thresholds. | `partially_mitigated` | backend/app/decision/loss.py |
| Q7 | DECISION-THEORETIC PROBLEMS | Risk should influence experiment selection. | `implemented_and_tested` | backend/app/decision/loss.py |
| Q8 | DECISION-THEORETIC PROBLEMS | Maintenance cost should potentially influence action selection. | `partially_mitigated` | backend/app/decision/loss.py |
| Q9 | DECISION-THEORETIC PROBLEMS | Downtime should influence action selection. | `partially_mitigated` | backend/app/decision/loss.py |
| Q10 | DECISION-THEORETIC PROBLEMS | Safety consequence should influence action selection. | `partially_mitigated` | backend/app/decision/loss.py |
| Q11 | DECISION-THEORETIC PROBLEMS | Need explicit Bayes-risk formulation. | `implemented_and_tested` | backend/app/decision/loss.py |
| Q12 | DECISION-THEORETIC PROBLEMS | Need application-dependent cost matrix. | `implemented_and_tested` | backend/app/decision/loss.py |
| Q13 | DECISION-THEORETIC PROBLEMS | Need distinction between information-optimal and risk-optimal inspection. Optimal Bayesian sensor/experiment design for guided-wave SHM has existed for years, including Bayes-risk formulations; therefore simply claiming "Bayesian active sensor selection" as novel would be unsafe. | `implemented_and_tested` | backend/app/decision/loss.py |
| R1 | STOPPING-CONDITION PROBLEMS | Fixed confidence threshold may be poorly calibrated. | `partially_mitigated` | backend/app/decision/stopping.py |
| R2 | STOPPING-CONDITION PROBLEMS | Fixed entropy threshold may not imply useful localization. | `partially_mitigated` | backend/app/decision/stopping.py |
| R3 | STOPPING-CONDITION PROBLEMS | Some defects may require more measurements. | `partially_mitigated` | backend/app/decision/stopping.py |
| R4 | STOPPING-CONDITION PROBLEMS | Some defects may never reach threshold. | `partially_mitigated` | backend/app/decision/stopping.py |
| R5 | STOPPING-CONDITION PROBLEMS | Planner may stop too early. | `partially_mitigated` | backend/app/decision/stopping.py |
| R6 | STOPPING-CONDITION PROBLEMS | Planner may inspect too long. | `partially_mitigated` | backend/app/decision/stopping.py |
| R7 | STOPPING-CONDITION PROBLEMS | Confidence may rise due to model bias, not evidence. | `partially_mitigated` | backend/app/decision/stopping.py |
| R8 | STOPPING-CONDITION PROBLEMS | Entropy may decline while posterior is wrong. | `partially_mitigated` | backend/app/decision/stopping.py |
| R9 | STOPPING-CONDITION PROBLEMS | Stop condition should potentially depend on application risk. | `implemented_and_tested` | backend/app/decision/stopping.py |
| R10 | STOPPING-CONDITION PROBLEMS | Stop condition should potentially depend on defect severity. | `partially_mitigated` | backend/app/decision/stopping.py |
| R11 | STOPPING-CONDITION PROBLEMS | Stop condition should potentially depend on OOD status. | `implemented_and_tested` | backend/app/decision/stopping.py |
| R12 | STOPPING-CONDITION PROBLEMS | Stop condition should potentially depend on hardware reliability. | `implemented_and_tested` | backend/app/decision/stopping.py |
| R13 | STOPPING-CONDITION PROBLEMS | Need measurement-budget stopping. | `implemented_and_tested` | backend/app/decision/stopping.py |
| R14 | STOPPING-CONDITION PROBLEMS | Need time-budget stopping. | `implemented_and_tested` | backend/app/decision/stopping.py |
| R15 | STOPPING-CONDITION PROBLEMS | Need energy-budget stopping. | `partially_mitigated` | backend/app/decision/stopping.py |
| R16 | STOPPING-CONDITION PROBLEMS | Need risk-budget stopping. | `partially_mitigated` | backend/app/decision/stopping.py |
| S1 | MULTI-DEFECT PROBLEMS | Single dominant defect assumption is restrictive. | `partially_mitigated` | backend/app/inference/structural_posterior.py; backend/app/assurance/monitor.py |
| S2 | MULTI-DEFECT PROBLEMS | Multiple defects produce overlapping wave responses. | `partially_mitigated` | backend/app/inference/structural_posterior.py; backend/app/assurance/monitor.py |
| S3 | MULTI-DEFECT PROBLEMS | Scattering from defects can interact. | `partially_mitigated` | backend/app/inference/structural_posterior.py; backend/app/assurance/monitor.py |
| S4 | MULTI-DEFECT PROBLEMS | Closely spaced defects may be unresolved. | `partially_mitigated` | backend/app/inference/structural_posterior.py; backend/app/assurance/monitor.py |
| S5 | MULTI-DEFECT PROBLEMS | Posterior can become multimodal. | `partially_mitigated` | backend/app/inference/structural_posterior.py; backend/app/assurance/monitor.py |
| S6 | MULTI-DEFECT PROBLEMS | Single Gaussian-like uncertainty assumptions may fail. | `partially_mitigated` | backend/app/inference/structural_posterior.py; backend/app/assurance/monitor.py |
| S7 | MULTI-DEFECT PROBLEMS | Defect count may be unknown. | `partially_mitigated` | backend/app/inference/structural_posterior.py; backend/app/assurance/monitor.py |
| S8 | MULTI-DEFECT PROBLEMS | Need joint inference of defect count. | `partially_mitigated` | backend/app/inference/structural_posterior.py; backend/app/assurance/monitor.py |
| S9 | MULTI-DEFECT PROBLEMS | Need instance separation. | `partially_mitigated` | backend/app/inference/structural_posterior.py; backend/app/assurance/monitor.py |
| S10 | MULTI-DEFECT PROBLEMS | Need defect association across measurements. | `partially_mitigated` | backend/app/inference/structural_posterior.py; backend/app/assurance/monitor.py |
| S11 | MULTI-DEFECT PROBLEMS | New measurements may reveal additional defects. | `partially_mitigated` | backend/app/inference/structural_posterior.py; backend/app/assurance/monitor.py |
| S12 | MULTI-DEFECT PROBLEMS | Existing defect estimates may need to be revised. | `partially_mitigated` | backend/app/inference/structural_posterior.py; backend/app/assurance/monitor.py |
| S13 | MULTI-DEFECT PROBLEMS | Planner must decide whether to refine known defects or search globally. | `partially_mitigated` | backend/app/inference/structural_posterior.py; backend/app/assurance/monitor.py |
| S14 | MULTI-DEFECT PROBLEMS | Planner must trade exploitation vs exploration. | `partially_mitigated` | backend/app/inference/structural_posterior.py; backend/app/assurance/monitor.py |
| S15 | MULTI-DEFECT PROBLEMS | Multi-defect uncertainty needs structured representation. | `partially_mitigated` | backend/app/inference/structural_posterior.py; backend/app/assurance/monitor.py |
| T1 | DEFECT CHARACTERIZATION PROBLEMS | Location alone is insufficient. | `partially_mitigated` | backend/app/inference/structural_posterior.py |
| T2 | DEFECT CHARACTERIZATION PROBLEMS | Need defect size. | `partially_mitigated` | backend/app/inference/structural_posterior.py |
| T3 | DEFECT CHARACTERIZATION PROBLEMS | Need defect shape. | `partially_mitigated` | backend/app/inference/structural_posterior.py |
| T4 | DEFECT CHARACTERIZATION PROBLEMS | Need defect orientation. | `partially_mitigated` | backend/app/inference/structural_posterior.py |
| T5 | DEFECT CHARACTERIZATION PROBLEMS | Need defect depth. | `partially_mitigated` | backend/app/inference/structural_posterior.py |
| T6 | DEFECT CHARACTERIZATION PROBLEMS | Need defect type. | `partially_mitigated` | backend/app/inference/structural_posterior.py |
| T7 | DEFECT CHARACTERIZATION PROBLEMS | Need severity. | `partially_mitigated` | backend/app/inference/structural_posterior.py |
| T8 | DEFECT CHARACTERIZATION PROBLEMS | Need potentially crack length. | `partially_mitigated` | backend/app/inference/structural_posterior.py |
| T9 | DEFECT CHARACTERIZATION PROBLEMS | Need delamination area. | `partially_mitigated` | backend/app/inference/structural_posterior.py |
| T10 | DEFECT CHARACTERIZATION PROBLEMS | Need void volume or equivalent parameter. | `partially_mitigated` | backend/app/inference/structural_posterior.py |
| T11 | DEFECT CHARACTERIZATION PROBLEMS | Need confidence interval for each quantity. | `partially_mitigated` | backend/app/inference/structural_posterior.py |
| T12 | DEFECT CHARACTERIZATION PROBLEMS | Different defect types can have similar wave signatures. | `partially_mitigated` | backend/app/inference/structural_posterior.py |
| T13 | DEFECT CHARACTERIZATION PROBLEMS | Same defect type can produce different signatures. | `partially_mitigated` | backend/app/inference/structural_posterior.py |
| T14 | DEFECT CHARACTERIZATION PROBLEMS | Severity labels may be subjective. | `partially_mitigated` | backend/app/inference/structural_posterior.py |
| T15 | DEFECT CHARACTERIZATION PROBLEMS | Defect dimensions may have ground-truth uncertainty. | `partially_mitigated` | backend/app/inference/structural_posterior.py |
| T16 | DEFECT CHARACTERIZATION PROBLEMS | Characterization may require additional measurement modalities. | `partially_mitigated` | backend/app/inference/structural_posterior.py |
| U1 | DOMAIN GENERALIZATION PROBLEMS | New panel geometry. | `requires_physical_validation` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| U2 | DOMAIN GENERALIZATION PROBLEMS | New material. | `requires_physical_validation` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| U3 | DOMAIN GENERALIZATION PROBLEMS | New laminate. | `requires_physical_validation` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| U4 | DOMAIN GENERALIZATION PROBLEMS | New sensor positions. | `requires_physical_validation` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| U5 | DOMAIN GENERALIZATION PROBLEMS | New sensor count. | `requires_physical_validation` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| U6 | DOMAIN GENERALIZATION PROBLEMS | New hardware. | `requires_physical_validation` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| U7 | DOMAIN GENERALIZATION PROBLEMS | New amplifier. | `requires_physical_validation` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| U8 | DOMAIN GENERALIZATION PROBLEMS | New excitation source. | `requires_physical_validation` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| U9 | DOMAIN GENERALIZATION PROBLEMS | New sampling frequency. | `requires_physical_validation` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| U10 | DOMAIN GENERALIZATION PROBLEMS | New environmental conditions. | `requires_physical_validation` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| U11 | DOMAIN GENERALIZATION PROBLEMS | New structural loading. | `requires_physical_validation` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| U12 | DOMAIN GENERALIZATION PROBLEMS | New defect type. | `requires_physical_validation` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| U13 | DOMAIN GENERALIZATION PROBLEMS | New defect size. | `requires_physical_validation` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| U14 | DOMAIN GENERALIZATION PROBLEMS | New defect orientation. | `requires_physical_validation` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| U15 | DOMAIN GENERALIZATION PROBLEMS | New surface condition. | `requires_physical_validation` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| U16 | DOMAIN GENERALIZATION PROBLEMS | New manufacturing process. | `requires_physical_validation` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| U17 | DOMAIN GENERALIZATION PROBLEMS | New operator. | `requires_physical_validation` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| U18 | DOMAIN GENERALIZATION PROBLEMS | New mounting procedure. | `requires_physical_validation` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| U19 | DOMAIN GENERALIZATION PROBLEMS | Cross-domain benchmark is required. | `requires_physical_validation` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| U20 | DOMAIN GENERALIZATION PROBLEMS | Domain adaptation should be measured, not assumed. material, temperature and domain discrepancy as major SHM barriers. | `requires_physical_validation` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| V1 | BASELINE-DEPENDENCE PROBLEMS | Healthy baseline may be required. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| V2 | BASELINE-DEPENDENCE PROBLEMS | Healthy baseline may become stale. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| V3 | BASELINE-DEPENDENCE PROBLEMS | Structural aging changes baseline. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| V4 | BASELINE-DEPENDENCE PROBLEMS | Temperature changes baseline. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| V5 | BASELINE-DEPENDENCE PROBLEMS | Sensor degradation changes baseline. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| V6 | BASELINE-DEPENDENCE PROBLEMS | Installation shifts change baseline. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| V7 | BASELINE-DEPENDENCE PROBLEMS | Removing baseline dependence would improve deployment. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| V8 | BASELINE-DEPENDENCE PROBLEMS | Need baseline-free mode. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| V9 | BASELINE-DEPENDENCE PROBLEMS | Baseline-free mode must not simply become less sensitive. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| V10 | BASELINE-DEPENDENCE PROBLEMS | Baseline-free performance must be separately benchmarked. detection, so this feature itself is not sufficient novelty. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| W1 | ENVIRONMENTAL ROBUSTNESS PROBLEMS | Temperature. | `requires_physical_validation` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| W2 | ENVIRONMENTAL ROBUSTNESS PROBLEMS | Humidity. | `requires_physical_validation` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| W3 | ENVIRONMENTAL ROBUSTNESS PROBLEMS | Rain. | `requires_physical_validation` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| W4 | ENVIRONMENTAL ROBUSTNESS PROBLEMS | Snow. | `requires_physical_validation` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| W5 | ENVIRONMENTAL ROBUSTNESS PROBLEMS | Wind. | `requires_physical_validation` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| W6 | ENVIRONMENTAL ROBUSTNESS PROBLEMS | Ambient vibration. | `requires_physical_validation` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| W7 | ENVIRONMENTAL ROBUSTNESS PROBLEMS | Operational loading. | `requires_physical_validation` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| W8 | ENVIRONMENTAL ROBUSTNESS PROBLEMS | Long-term drift. | `requires_physical_validation` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| W9 | ENVIRONMENTAL ROBUSTNESS PROBLEMS | Day/night effects. | `requires_physical_validation` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| W10 | ENVIRONMENTAL ROBUSTNESS PROBLEMS | Sensor temperature. | `requires_physical_validation` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| W11 | ENVIRONMENTAL ROBUSTNESS PROBLEMS | Material temperature. | `requires_physical_validation` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| W12 | ENVIRONMENTAL ROBUSTNESS PROBLEMS | Thermal gradients. | `requires_physical_validation` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| W13 | ENVIRONMENTAL ROBUSTNESS PROBLEMS | Moisture ingress. | `requires_physical_validation` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| W14 | ENVIRONMENTAL ROBUSTNESS PROBLEMS | Environmental changes may resemble damage. | `requires_physical_validation` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| W15 | ENVIRONMENTAL ROBUSTNESS PROBLEMS | Damage may be masked by environmental variation. | `requires_physical_validation` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| W16 | ENVIRONMENTAL ROBUSTNESS PROBLEMS | Need environmental conditioning or compensation. Long-duration public guided-wave SHM data now exists specifically under uncontrolled/dynamic conditions, including temperature, rain, snow and sensor/installation drift, making this a realistic benchmark rather than a theoretical concern. | `requires_physical_validation` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| X1 | SENSOR FAULT / RELIABILITY PROBLEMS | Dead sensor. | `partially_mitigated` | backend/app/assurance/monitor.py; backend/app/research/faults.py |
| X2 | SENSOR FAULT / RELIABILITY PROBLEMS | Intermittent sensor. | `partially_mitigated` | backend/app/assurance/monitor.py; backend/app/research/faults.py |
| X3 | SENSOR FAULT / RELIABILITY PROBLEMS | Drifted sensor. | `partially_mitigated` | backend/app/assurance/monitor.py; backend/app/research/faults.py |
| X4 | SENSOR FAULT / RELIABILITY PROBLEMS | Noisy sensor. | `partially_mitigated` | backend/app/assurance/monitor.py; backend/app/research/faults.py |
| X5 | SENSOR FAULT / RELIABILITY PROBLEMS | Misaligned sensor. | `partially_mitigated` | backend/app/assurance/monitor.py; backend/app/research/faults.py |
| X6 | SENSOR FAULT / RELIABILITY PROBLEMS | Detached sensor. | `partially_mitigated` | backend/app/assurance/monitor.py; backend/app/research/faults.py |
| X7 | SENSOR FAULT / RELIABILITY PROBLEMS | Saturated sensor. | `implemented_and_tested` | backend/app/assurance/monitor.py; backend/app/research/faults.py |
| X8 | SENSOR FAULT / RELIABILITY PROBLEMS | Missing data. | `implemented_and_tested` | backend/app/assurance/monitor.py; backend/app/research/faults.py |
| X9 | SENSOR FAULT / RELIABILITY PROBLEMS | Corrupted data. | `implemented_and_tested` | backend/app/assurance/monitor.py; backend/app/research/faults.py |
| X10 | SENSOR FAULT / RELIABILITY PROBLEMS | False sensor reading. | `partially_mitigated` | backend/app/assurance/monitor.py; backend/app/research/faults.py |
| X11 | SENSOR FAULT / RELIABILITY PROBLEMS | Sensor reliability must be estimated. | `implemented_and_tested` | backend/app/assurance/monitor.py; backend/app/research/faults.py |
| X12 | SENSOR FAULT / RELIABILITY PROBLEMS | Sensor reliability should affect posterior weighting. | `implemented_and_tested` | backend/app/assurance/monitor.py; backend/app/research/faults.py |
| X13 | SENSOR FAULT / RELIABILITY PROBLEMS | Sensor reliability should affect experiment planning. | `implemented_and_tested` | backend/app/assurance/monitor.py; backend/app/research/faults.py |
| X14 | SENSOR FAULT / RELIABILITY PROBLEMS | Planner should avoid unreliable channels. | `implemented_and_tested` | backend/app/assurance/monitor.py; backend/app/research/faults.py |
| X15 | SENSOR FAULT / RELIABILITY PROBLEMS | Planner should exploit redundant sensors. | `partially_mitigated` | backend/app/assurance/monitor.py; backend/app/research/faults.py |
| X16 | SENSOR FAULT / RELIABILITY PROBLEMS | Need automatic sensor-fault detection. | `implemented_and_tested` | backend/app/assurance/monitor.py; backend/app/research/faults.py |
| X17 | SENSOR FAULT / RELIABILITY PROBLEMS | Need fault isolation. | `implemented_and_tested` | backend/app/assurance/monitor.py; backend/app/research/faults.py |
| X18 | SENSOR FAULT / RELIABILITY PROBLEMS | Need graceful degradation. | `implemented_and_tested` | backend/app/assurance/monitor.py; backend/app/research/faults.py |
| X19 | SENSOR FAULT / RELIABILITY PROBLEMS | Need sensor-recovery strategy. | `partially_mitigated` | backend/app/assurance/monitor.py; backend/app/research/faults.py |
| X20 | SENSOR FAULT / RELIABILITY PROBLEMS | Need automatic recalibration strategy. Current research is explicitly studying sensing digital twins that distinguish structural damage from sensing degradation and estimate probabilistic sensor reliability, so this is a valuable direction but not a blank research area. | `partially_mitigated` | backend/app/assurance/monitor.py; backend/app/research/faults.py |
| Y1 | COMPUTATIONAL PROBLEMS | Candidate experiment explosion. | `partially_mitigated` | backend/app/digital_twin/multifidelity.py; backend/app/evaluation/neo_benchmark.py |
| Y2 | COMPUTATIONAL PROBLEMS | Neural inference cost. | `partially_mitigated` | backend/app/digital_twin/multifidelity.py; backend/app/evaluation/neo_benchmark.py |
| Y3 | COMPUTATIONAL PROBLEMS | Simulator cost. | `partially_mitigated` | backend/app/digital_twin/multifidelity.py; backend/app/evaluation/neo_benchmark.py |
| Y4 | COMPUTATIONAL PROBLEMS | High-fidelity FEM cost. | `partially_mitigated` | backend/app/digital_twin/multifidelity.py; backend/app/evaluation/neo_benchmark.py |
| Y5 | COMPUTATIONAL PROBLEMS | Bayesian posterior update cost. | `partially_mitigated` | backend/app/digital_twin/multifidelity.py; backend/app/evaluation/neo_benchmark.py |
| Y6 | COMPUTATIONAL PROBLEMS | Hyperparameter optimization cost. | `partially_mitigated` | backend/app/digital_twin/multifidelity.py; backend/app/evaluation/neo_benchmark.py |
| Y7 | COMPUTATIONAL PROBLEMS | Large waveform memory requirements. | `partially_mitigated` | backend/app/digital_twin/multifidelity.py; backend/app/evaluation/neo_benchmark.py |
| Y8 | COMPUTATIONAL PROBLEMS | Real-time spectrogram generation cost. | `partially_mitigated` | backend/app/digital_twin/multifidelity.py; backend/app/evaluation/neo_benchmark.py |
| Y9 | COMPUTATIONAL PROBLEMS | Edge-device resource constraints. | `partially_mitigated` | backend/app/digital_twin/multifidelity.py; backend/app/evaluation/neo_benchmark.py |
| Y10 | COMPUTATIONAL PROBLEMS | GPU dependency. | `partially_mitigated` | backend/app/digital_twin/multifidelity.py; backend/app/evaluation/neo_benchmark.py |
| Y11 | COMPUTATIONAL PROBLEMS | CPU fallback. | `implemented_and_tested` | backend/app/digital_twin/multifidelity.py; backend/app/evaluation/neo_benchmark.py |
| Y12 | COMPUTATIONAL PROBLEMS | Cold-start latency. | `partially_mitigated` | backend/app/digital_twin/multifidelity.py; backend/app/evaluation/neo_benchmark.py |
| Y13 | COMPUTATIONAL PROBLEMS | Communication latency. | `partially_mitigated` | backend/app/digital_twin/multifidelity.py; backend/app/evaluation/neo_benchmark.py |
| Y14 | COMPUTATIONAL PROBLEMS | Hardware acquisition latency. | `partially_mitigated` | backend/app/digital_twin/multifidelity.py; backend/app/evaluation/neo_benchmark.py |
| Y15 | COMPUTATIONAL PROBLEMS | End-to-end latency should be measured. | `implemented_and_tested` | backend/app/digital_twin/multifidelity.py; backend/app/evaluation/neo_benchmark.py |
| Y16 | COMPUTATIONAL PROBLEMS | Throughput should be measured. | `implemented_and_tested` | backend/app/digital_twin/multifidelity.py; backend/app/evaluation/neo_benchmark.py |
| Y17 | COMPUTATIONAL PROBLEMS | Memory use should be measured. | `partially_mitigated` | backend/app/digital_twin/multifidelity.py; backend/app/evaluation/neo_benchmark.py |
| Y18 | COMPUTATIONAL PROBLEMS | Power use should be measured. | `partially_mitigated` | backend/app/digital_twin/multifidelity.py; backend/app/evaluation/neo_benchmark.py |
| Y19 | COMPUTATIONAL PROBLEMS | Candidate pruning strategy may be required. | `implemented_and_tested` | backend/app/digital_twin/multifidelity.py; backend/app/evaluation/neo_benchmark.py |
| Y20 | COMPUTATIONAL PROBLEMS | Surrogate model may be required. | `implemented_and_tested` | backend/app/digital_twin/multifidelity.py; backend/app/evaluation/neo_benchmark.py |
| Y21 | COMPUTATIONAL PROBLEMS | Reduced-order physics may be required. | `partially_mitigated` | backend/app/digital_twin/multifidelity.py; backend/app/evaluation/neo_benchmark.py |
| Y22 | COMPUTATIONAL PROBLEMS | Approximate inference may be required. | `partially_mitigated` | backend/app/digital_twin/multifidelity.py; backend/app/evaluation/neo_benchmark.py |
| Y23 | COMPUTATIONAL PROBLEMS | Quantization may be required for edge deployment. | `partially_mitigated` | backend/app/digital_twin/multifidelity.py; backend/app/evaluation/neo_benchmark.py |
| Y24 | COMPUTATIONAL PROBLEMS | Model compression may be required. | `partially_mitigated` | backend/app/digital_twin/multifidelity.py; backend/app/evaluation/neo_benchmark.py |
| Z1 | SIMULATOR / DIGITAL-TWIN PROBLEMS | Simulator may not match real physics. | `partially_mitigated` | backend/app/digital_twin; backend/app/inference/nuisance_posterior.py |
| Z2 | SIMULATOR / DIGITAL-TWIN PROBLEMS | Simulator parameters may be inaccurate. | `partially_mitigated` | backend/app/digital_twin; backend/app/inference/nuisance_posterior.py |
| Z3 | SIMULATOR / DIGITAL-TWIN PROBLEMS | Simulator parameters may be fixed rather than learned. | `partially_mitigated` | backend/app/digital_twin; backend/app/inference/nuisance_posterior.py |
| Z4 | SIMULATOR / DIGITAL-TWIN PROBLEMS | Simulator may not update from measured data. | `partially_mitigated` | backend/app/digital_twin; backend/app/inference/nuisance_posterior.py |
| Z5 | SIMULATOR / DIGITAL-TWIN PROBLEMS | Simulator may not represent structural aging. | `partially_mitigated` | backend/app/digital_twin; backend/app/inference/nuisance_posterior.py |
| Z6 | SIMULATOR / DIGITAL-TWIN PROBLEMS | Simulator may not represent environmental state. | `partially_mitigated` | backend/app/digital_twin; backend/app/inference/nuisance_posterior.py |
| Z7 | SIMULATOR / DIGITAL-TWIN PROBLEMS | Simulator may not represent sensor state. | `partially_mitigated` | backend/app/digital_twin; backend/app/inference/nuisance_posterior.py |
| Z8 | SIMULATOR / DIGITAL-TWIN PROBLEMS | Simulator may not represent manufacturing variability. | `partially_mitigated` | backend/app/digital_twin; backend/app/inference/nuisance_posterior.py |
| Z9 | SIMULATOR / DIGITAL-TWIN PROBLEMS | Simulator may not represent defect diversity. | `partially_mitigated` | backend/app/digital_twin; backend/app/inference/nuisance_posterior.py |
| Z10 | SIMULATOR / DIGITAL-TWIN PROBLEMS | Simulator may be too slow. | `partially_mitigated` | backend/app/digital_twin; backend/app/inference/nuisance_posterior.py |
| Z11 | SIMULATOR / DIGITAL-TWIN PROBLEMS | Neural surrogate may introduce surrogate error. | `implemented_and_tested` | backend/app/digital_twin; backend/app/inference/nuisance_posterior.py |
| Z12 | SIMULATOR / DIGITAL-TWIN PROBLEMS | Surrogate uncertainty may be ignored. | `implemented_and_tested` | backend/app/digital_twin; backend/app/inference/nuisance_posterior.py |
| Z13 | SIMULATOR / DIGITAL-TWIN PROBLEMS | Surrogate extrapolation may fail. | `partially_mitigated` | backend/app/digital_twin; backend/app/inference/nuisance_posterior.py |
| Z14 | SIMULATOR / DIGITAL-TWIN PROBLEMS | Active planner may exploit surrogate artifacts. | `partially_mitigated` | backend/app/digital_twin; backend/app/inference/nuisance_posterior.py |
| Z15 | SIMULATOR / DIGITAL-TWIN PROBLEMS | Physics/surrogate disagreement should be monitored. | `implemented_and_tested` | backend/app/digital_twin; backend/app/inference/nuisance_posterior.py |
| Z16 | SIMULATOR / DIGITAL-TWIN PROBLEMS | Need simulator validation against measured waveforms. | `partially_mitigated` | backend/app/digital_twin; backend/app/inference/nuisance_posterior.py |
| Z17 | SIMULATOR / DIGITAL-TWIN PROBLEMS | Need parameter-identification stage. | `partially_mitigated` | backend/app/digital_twin; backend/app/inference/nuisance_posterior.py |
| Z18 | SIMULATOR / DIGITAL-TWIN PROBLEMS | Need uncertainty bounds for simulator parameters. | `implemented_and_tested` | backend/app/digital_twin; backend/app/inference/nuisance_posterior.py |
| Z19 | SIMULATOR / DIGITAL-TWIN PROBLEMS | Need model discrepancy term. | `implemented_and_tested` | backend/app/digital_twin; backend/app/inference/nuisance_posterior.py |
| Z20 | SIMULATOR / DIGITAL-TWIN PROBLEMS | Need calibration against real measurements. | `implemented_and_tested` | backend/app/digital_twin; backend/app/inference/nuisance_posterior.py |
| Z21 | SIMULATOR / DIGITAL-TWIN PROBLEMS | Need digital twin updating. | `partially_mitigated` | backend/app/digital_twin; backend/app/inference/nuisance_posterior.py |
| Z22 | SIMULATOR / DIGITAL-TWIN PROBLEMS | Need versioned digital twin parameters. | `implemented_and_tested` | backend/app/digital_twin; backend/app/inference/nuisance_posterior.py |
| Z23 | SIMULATOR / DIGITAL-TWIN PROBLEMS | Need twin health monitoring. Current literature is already moving toward digital twins that update for temperature, noise and changing transducer behavior, so your digital twin should be more than a fixed simulator. | `partially_mitigated` | backend/app/digital_twin; backend/app/inference/nuisance_posterior.py |
| AA1 | TRAINING PROTOCOL PROBLEMS | Random splits can leak structure-specific information. | `implemented_and_tested` | docs/REPRODUCIBILITY.md; backend/app/evaluation; research_results |
| AA2 | TRAINING PROTOCOL PROBLEMS | Hyperparameters can leak validation information. | `partially_mitigated` | docs/REPRODUCIBILITY.md; backend/app/evaluation; research_results |
| AA3 | TRAINING PROTOCOL PROBLEMS | Synthetic data augmentation may be unrealistic. | `partially_mitigated` | docs/REPRODUCIBILITY.md; backend/app/evaluation; research_results |
| AA4 | TRAINING PROTOCOL PROBLEMS | Noise augmentation may be simplistic. | `partially_mitigated` | docs/REPRODUCIBILITY.md; backend/app/evaluation; research_results |
| AA5 | TRAINING PROTOCOL PROBLEMS | Frequency augmentation may be unrealistic. | `partially_mitigated` | docs/REPRODUCIBILITY.md; backend/app/evaluation; research_results |
| AA6 | TRAINING PROTOCOL PROBLEMS | Sensor dropout augmentation may be unrealistic. | `partially_mitigated` | docs/REPRODUCIBILITY.md; backend/app/evaluation; research_results |
| AA7 | TRAINING PROTOCOL PROBLEMS | Domain-adaptation training can be unstable. | `partially_mitigated` | docs/REPRODUCIBILITY.md; backend/app/evaluation; research_results |
| AA8 | TRAINING PROTOCOL PROBLEMS | Physics-loss training can be unstable. | `partially_mitigated` | docs/REPRODUCIBILITY.md; backend/app/evaluation; research_results |
| AA9 | TRAINING PROTOCOL PROBLEMS | Multi-task training may create competing gradients. | `partially_mitigated` | docs/REPRODUCIBILITY.md; backend/app/evaluation; research_results |
| AA10 | TRAINING PROTOCOL PROBLEMS | Model selection may be biased toward one benchmark. | `partially_mitigated` | docs/REPRODUCIBILITY.md; backend/app/evaluation; research_results |
| AA11 | TRAINING PROTOCOL PROBLEMS | Need repeated runs with multiple random seeds. | `implemented_and_tested` | docs/REPRODUCIBILITY.md; backend/app/evaluation; research_results |
| AA12 | TRAINING PROTOCOL PROBLEMS | Need confidence intervals. | `implemented_and_tested` | docs/REPRODUCIBILITY.md; backend/app/evaluation; research_results |
| AA13 | TRAINING PROTOCOL PROBLEMS | Need ablation studies. | `implemented_and_tested` | docs/REPRODUCIBILITY.md; backend/app/evaluation; research_results |
| AA14 | TRAINING PROTOCOL PROBLEMS | Need statistical tests. | `partially_mitigated` | docs/REPRODUCIBILITY.md; backend/app/evaluation; research_results |
| AA15 | TRAINING PROTOCOL PROBLEMS | Need reproducible training configurations. | `implemented_and_tested` | docs/REPRODUCIBILITY.md; backend/app/evaluation; research_results |
| AA16 | TRAINING PROTOCOL PROBLEMS | Need fixed benchmark protocol. | `implemented_and_tested` | docs/REPRODUCIBILITY.md; backend/app/evaluation; research_results |
| AA17 | TRAINING PROTOCOL PROBLEMS | Need checkpoint/version tracking. | `implemented_and_tested` | docs/REPRODUCIBILITY.md; backend/app/evaluation; research_results |
| AA18 | TRAINING PROTOCOL PROBLEMS | Need experiment tracking. | `implemented_and_tested` | docs/REPRODUCIBILITY.md; backend/app/evaluation; research_results |
| AA19 | TRAINING PROTOCOL PROBLEMS | Need data versioning. | `implemented_and_tested` | docs/REPRODUCIBILITY.md; backend/app/evaluation; research_results |
| AA20 | TRAINING PROTOCOL PROBLEMS | Need leakage testing. | `implemented_and_tested` | docs/REPRODUCIBILITY.md; backend/app/evaluation; research_results |
| AB1 | SELF-SUPERVISED LEARNING PROBLEMS | Need large unlabeled signal corpus. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AB2 | SELF-SUPERVISED LEARNING PROBLEMS | Pretext task must preserve damage-relevant information. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AB3 | SELF-SUPERVISED LEARNING PROBLEMS | Reconstruction may learn irrelevant signal details. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AB4 | SELF-SUPERVISED LEARNING PROBLEMS | Contrastive learning augmentations may remove damage information. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AB5 | SELF-SUPERVISED LEARNING PROBLEMS | Representation may be insensitive to subtle defects. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AB6 | SELF-SUPERVISED LEARNING PROBLEMS | Self-supervised objective may bias toward healthy signals. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AB7 | SELF-SUPERVISED LEARNING PROBLEMS | Downstream fine-tuning may remain data-limited. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AB8 | SELF-SUPERVISED LEARNING PROBLEMS | Cross-domain self-supervision may still fail. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AB9 | SELF-SUPERVISED LEARNING PROBLEMS | Need comparison against supervised training. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AB10 | SELF-SUPERVISED LEARNING PROBLEMS | Need ablation of pretraining strategy. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AC1 | DOMAIN ADAPTATION PROBLEMS | Source and target distributions differ. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AC2 | DOMAIN ADAPTATION PROBLEMS | Feature alignment may align damage and non-damage features incorrectly. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AC3 | DOMAIN ADAPTATION PROBLEMS | Adversarial adaptation may destabilize training. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AC4 | DOMAIN ADAPTATION PROBLEMS | Negative transfer can occur. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AC5 | DOMAIN ADAPTATION PROBLEMS | Target domain may have no labels. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AC6 | DOMAIN ADAPTATION PROBLEMS | Target domain may have few labels. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AC7 | DOMAIN ADAPTATION PROBLEMS | Target domain may contain unknown classes. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AC8 | DOMAIN ADAPTATION PROBLEMS | Target domain may evolve over time. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AC9 | DOMAIN ADAPTATION PROBLEMS | Adaptation can cause catastrophic forgetting. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AC10 | DOMAIN ADAPTATION PROBLEMS | Need target-domain validation without leakage. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AC11 | DOMAIN ADAPTATION PROBLEMS | Need cross-panel test. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AC12 | DOMAIN ADAPTATION PROBLEMS | Need cross-material test. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AC13 | DOMAIN ADAPTATION PROBLEMS | Need cross-temperature test. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AC14 | DOMAIN ADAPTATION PROBLEMS | Need cross-hardware test. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AC15 | DOMAIN ADAPTATION PROBLEMS | Need adaptation cost measurement. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AC16 | DOMAIN ADAPTATION PROBLEMS | Need adaptation time measurement. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AD1 | ACTIVE-LEARNING / EXPLORATION PROBLEMS | Need to distinguish exploration from exploitation. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AD2 | ACTIVE-LEARNING / EXPLORATION PROBLEMS | Pure exploitation can miss unknown defects. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AD3 | ACTIVE-LEARNING / EXPLORATION PROBLEMS | Pure exploration wastes measurements. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AD4 | ACTIVE-LEARNING / EXPLORATION PROBLEMS | Rare defects may require exploration. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AD5 | ACTIVE-LEARNING / EXPLORATION PROBLEMS | Critical regions may require higher priority. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AD6 | ACTIVE-LEARNING / EXPLORATION PROBLEMS | Planner may become trapped in local belief maxima. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AD7 | ACTIVE-LEARNING / EXPLORATION PROBLEMS | Posterior collapse can prevent discovering alternative hypotheses. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AD8 | ACTIVE-LEARNING / EXPLORATION PROBLEMS | Need diversity in experiments. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AD9 | ACTIVE-LEARNING / EXPLORATION PROBLEMS | Need uncertainty-aware exploration. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AD10 | ACTIVE-LEARNING / EXPLORATION PROBLEMS | Need worst-case exploration. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AD11 | ACTIVE-LEARNING / EXPLORATION PROBLEMS | Need budget-aware exploration. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AD12 | ACTIVE-LEARNING / EXPLORATION PROBLEMS | Need active labeling if human feedback becomes available. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AE1 | REINFORCEMENT LEARNING PROBLEMS | State representation. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AE2 | REINFORCEMENT LEARNING PROBLEMS | Action representation. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AE3 | REINFORCEMENT LEARNING PROBLEMS | Reward design. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AE4 | REINFORCEMENT LEARNING PROBLEMS | Sparse rewards. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AE5 | REINFORCEMENT LEARNING PROBLEMS | Reward hacking. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AE6 | REINFORCEMENT LEARNING PROBLEMS | Simulator exploitation. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AE7 | REINFORCEMENT LEARNING PROBLEMS | Sample inefficiency. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AE8 | REINFORCEMENT LEARNING PROBLEMS | Training instability. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AE9 | REINFORCEMENT LEARNING PROBLEMS | Distribution shift. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AE10 | REINFORCEMENT LEARNING PROBLEMS | Unsafe policies. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AE11 | REINFORCEMENT LEARNING PROBLEMS | Sim-to-real transfer. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AE12 | REINFORCEMENT LEARNING PROBLEMS | Need policy constraints. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AE13 | REINFORCEMENT LEARNING PROBLEMS | Need fallback planner. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AE14 | REINFORCEMENT LEARNING PROBLEMS | RL may not outperform a strong greedy Bayesian planner. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AE15 | REINFORCEMENT LEARNING PROBLEMS | RL adds complexity without guaranteed scientific value. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AF1 | ROBUSTNESS PROBLEMS | Increased Gaussian noise. | `implemented_and_tested` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AF2 | ROBUSTNESS PROBLEMS | Colored noise. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AF3 | ROBUSTNESS PROBLEMS | Nonstationary noise. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AF4 | ROBUSTNESS PROBLEMS | Impulsive noise. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AF5 | ROBUSTNESS PROBLEMS | Sensor dropout. | `implemented_and_tested` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AF6 | ROBUSTNESS PROBLEMS | Sensor permutation. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AF7 | ROBUSTNESS PROBLEMS | Sensor misplacement. | `implemented_and_tested` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AF8 | ROBUSTNESS PROBLEMS | Timing offset. | `implemented_and_tested` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AF9 | ROBUSTNESS PROBLEMS | Amplitude scaling. | `implemented_and_tested` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AF10 | ROBUSTNESS PROBLEMS | Frequency shift. | `implemented_and_tested` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AF11 | ROBUSTNESS PROBLEMS | Unknown temperature. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AF12 | ROBUSTNESS PROBLEMS | Unknown material property. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AF13 | ROBUSTNESS PROBLEMS | Unknown defect type. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AF14 | ROBUSTNESS PROBLEMS | Missing metadata. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AF15 | ROBUSTNESS PROBLEMS | Wrong metadata. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AF16 | ROBUSTNESS PROBLEMS | Structural geometry change. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AF17 | ROBUSTNESS PROBLEMS | Boundary condition change. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AF18 | ROBUSTNESS PROBLEMS | Hardware change. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AF19 | ROBUSTNESS PROBLEMS | Environmental change. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AF20 | ROBUSTNESS PROBLEMS | Distribution shift. | `implemented_and_tested` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AG1 | ADVERSARIAL / SECURITY / INTEGRITY PROBLEMS | Deliberately corrupted sensor readings. | `partially_mitigated` | backend/app/evidence/ledger.py; backend/app/services/session_manager.py |
| AG2 | ADVERSARIAL / SECURITY / INTEGRITY PROBLEMS | Malicious data injection. | `partially_mitigated` | backend/app/evidence/ledger.py; backend/app/services/session_manager.py |
| AG3 | ADVERSARIAL / SECURITY / INTEGRITY PROBLEMS | Timestamp tampering. | `partially_mitigated` | backend/app/evidence/ledger.py; backend/app/services/session_manager.py |
| AG4 | ADVERSARIAL / SECURITY / INTEGRITY PROBLEMS | Sensor spoofing. | `partially_mitigated` | backend/app/evidence/ledger.py; backend/app/services/session_manager.py |
| AG5 | ADVERSARIAL / SECURITY / INTEGRITY PROBLEMS | Communication tampering. | `partially_mitigated` | backend/app/evidence/ledger.py; backend/app/services/session_manager.py |
| AG6 | ADVERSARIAL / SECURITY / INTEGRITY PROBLEMS | Model input manipulation. | `partially_mitigated` | backend/app/evidence/ledger.py; backend/app/services/session_manager.py |
| AG7 | ADVERSARIAL / SECURITY / INTEGRITY PROBLEMS | False telemetry. | `partially_mitigated` | backend/app/evidence/ledger.py; backend/app/services/session_manager.py |
| AG8 | ADVERSARIAL / SECURITY / INTEGRITY PROBLEMS | Compromised edge device. | `partially_mitigated` | backend/app/evidence/ledger.py; backend/app/services/session_manager.py |
| AG9 | ADVERSARIAL / SECURITY / INTEGRITY PROBLEMS | Need authenticated communication if deployed remotely. | `partially_mitigated` | backend/app/evidence/ledger.py; backend/app/services/session_manager.py |
| AG10 | ADVERSARIAL / SECURITY / INTEGRITY PROBLEMS | Need data-integrity checks. | `implemented_and_tested` | backend/app/evidence/ledger.py; backend/app/services/session_manager.py |
| AG11 | ADVERSARIAL / SECURITY / INTEGRITY PROBLEMS | Need anomaly detection on telemetry. | `partially_mitigated` | backend/app/evidence/ledger.py; backend/app/services/session_manager.py |
| AH1 | INTERPRETABILITY PROBLEMS | Neural model may be a black box. | `partially_mitigated` | backend/app/active_learning/neo_planner.py; frontend/components/EvidenceLedger.tsx |
| AH2 | INTERPRETABILITY PROBLEMS | Prediction explanation may not reflect actual model reasoning. | `partially_mitigated` | backend/app/active_learning/neo_planner.py; frontend/components/EvidenceLedger.tsx |
| AH3 | INTERPRETABILITY PROBLEMS | Saliency may be unreliable. | `partially_mitigated` | backend/app/active_learning/neo_planner.py; frontend/components/EvidenceLedger.tsx |
| AH4 | INTERPRETABILITY PROBLEMS | Attention maps are not automatically explanations. | `partially_mitigated` | backend/app/active_learning/neo_planner.py; frontend/components/EvidenceLedger.tsx |
| AH5 | INTERPRETABILITY PROBLEMS | Need physics-grounded explanation. | `implemented_and_tested` | backend/app/active_learning/neo_planner.py; frontend/components/EvidenceLedger.tsx |
| AH6 | INTERPRETABILITY PROBLEMS | Need evidence for each defect hypothesis. | `implemented_and_tested` | backend/app/active_learning/neo_planner.py; frontend/components/EvidenceLedger.tsx |
| AH7 | INTERPRETABILITY PROBLEMS | Need evidence for next-experiment choice. | `implemented_and_tested` | backend/app/active_learning/neo_planner.py; frontend/components/EvidenceLedger.tsx |
| AH8 | INTERPRETABILITY PROBLEMS | Need uncertainty explanation. | `implemented_and_tested` | backend/app/active_learning/neo_planner.py; frontend/components/EvidenceLedger.tsx |
| AH9 | INTERPRETABILITY PROBLEMS | Need reason for abstention. | `implemented_and_tested` | backend/app/active_learning/neo_planner.py; frontend/components/EvidenceLedger.tsx |
| AH10 | INTERPRETABILITY PROBLEMS | Need reason for sensor rejection. | `implemented_and_tested` | backend/app/active_learning/neo_planner.py; frontend/components/EvidenceLedger.tsx |
| AH11 | INTERPRETABILITY PROBLEMS | Need traceability to raw measurements. | `implemented_and_tested` | backend/app/active_learning/neo_planner.py; frontend/components/EvidenceLedger.tsx |
| AH12 | INTERPRETABILITY PROBLEMS | Need inspection-history traceability. | `implemented_and_tested` | backend/app/active_learning/neo_planner.py; frontend/components/EvidenceLedger.tsx |
| AI1 | EXPERIMENT-TRACEABILITY PROBLEMS | Every measurement should have a unique ID. | `implemented_and_tested` | backend/app/evidence/ledger.py; backend/app/database/repository.py |
| AI2 | EXPERIMENT-TRACEABILITY PROBLEMS | Every measurement should store timestamp. | `implemented_and_tested` | backend/app/evidence/ledger.py; backend/app/database/repository.py |
| AI3 | EXPERIMENT-TRACEABILITY PROBLEMS | Store source position. | `implemented_and_tested` | backend/app/evidence/ledger.py; backend/app/database/repository.py |
| AI4 | EXPERIMENT-TRACEABILITY PROBLEMS | Store receiver position. | `implemented_and_tested` | backend/app/evidence/ledger.py; backend/app/database/repository.py |
| AI5 | EXPERIMENT-TRACEABILITY PROBLEMS | Store frequency. | `implemented_and_tested` | backend/app/evidence/ledger.py; backend/app/database/repository.py |
| AI6 | EXPERIMENT-TRACEABILITY PROBLEMS | Store waveform. | `implemented_and_tested` | backend/app/evidence/ledger.py; backend/app/database/repository.py |
| AI7 | EXPERIMENT-TRACEABILITY PROBLEMS | Store amplitude. | `implemented_and_tested` | backend/app/evidence/ledger.py; backend/app/database/repository.py |
| AI8 | EXPERIMENT-TRACEABILITY PROBLEMS | Store duration. | `implemented_and_tested` | backend/app/evidence/ledger.py; backend/app/database/repository.py |
| AI9 | EXPERIMENT-TRACEABILITY PROBLEMS | Store sensor IDs. | `implemented_and_tested` | backend/app/evidence/ledger.py; backend/app/database/repository.py |
| AI10 | EXPERIMENT-TRACEABILITY PROBLEMS | Store environmental conditions. | `implemented_and_tested` | backend/app/evidence/ledger.py; backend/app/database/repository.py |
| AI11 | EXPERIMENT-TRACEABILITY PROBLEMS | Store model version. | `implemented_and_tested` | backend/app/evidence/ledger.py; backend/app/database/repository.py |
| AI12 | EXPERIMENT-TRACEABILITY PROBLEMS | Store digital-twin version. | `implemented_and_tested` | backend/app/evidence/ledger.py; backend/app/database/repository.py |
| AI13 | EXPERIMENT-TRACEABILITY PROBLEMS | Store planner score. | `implemented_and_tested` | backend/app/evidence/ledger.py; backend/app/database/repository.py |
| AI14 | EXPERIMENT-TRACEABILITY PROBLEMS | Store posterior before measurement. | `implemented_and_tested` | backend/app/evidence/ledger.py; backend/app/database/repository.py |
| AI15 | EXPERIMENT-TRACEABILITY PROBLEMS | Store posterior after measurement. | `implemented_and_tested` | backend/app/evidence/ledger.py; backend/app/database/repository.py |
| AI16 | EXPERIMENT-TRACEABILITY PROBLEMS | Store reason for experiment selection. | `implemented_and_tested` | backend/app/evidence/ledger.py; backend/app/database/repository.py |
| AI17 | EXPERIMENT-TRACEABILITY PROBLEMS | Store confidence. | `implemented_and_tested` | backend/app/evidence/ledger.py; backend/app/database/repository.py |
| AI18 | EXPERIMENT-TRACEABILITY PROBLEMS | Store uncertainty. | `implemented_and_tested` | backend/app/evidence/ledger.py; backend/app/database/repository.py |
| AI19 | EXPERIMENT-TRACEABILITY PROBLEMS | Store OOD score. | `implemented_and_tested` | backend/app/evidence/ledger.py; backend/app/database/repository.py |
| AI20 | EXPERIMENT-TRACEABILITY PROBLEMS | Store operator overrides. | `implemented_and_tested` | backend/app/evidence/ledger.py; backend/app/database/repository.py |
| AI21 | EXPERIMENT-TRACEABILITY PROBLEMS | Store hardware faults. | `implemented_and_tested` | backend/app/evidence/ledger.py; backend/app/database/repository.py |
| AI22 | EXPERIMENT-TRACEABILITY PROBLEMS | Store final decision. | `implemented_and_tested` | backend/app/evidence/ledger.py; backend/app/database/repository.py |
| AJ1 | HARDWARE / ROBOTICS PROBLEMS | Probe movement accuracy. | `requires_physical_validation` | backend/app/safety/constraints.py; frontend/components/CameraOverlay.tsx |
| AJ2 | HARDWARE / ROBOTICS PROBLEMS | Probe repeatability. | `requires_physical_validation` | backend/app/safety/constraints.py; frontend/components/CameraOverlay.tsx |
| AJ3 | HARDWARE / ROBOTICS PROBLEMS | Mechanical positioning error. | `requires_physical_validation` | backend/app/safety/constraints.py; frontend/components/CameraOverlay.tsx |
| AJ4 | HARDWARE / ROBOTICS PROBLEMS | Collision avoidance. | `implemented_and_tested` | backend/app/safety/constraints.py; frontend/components/CameraOverlay.tsx |
| AJ5 | HARDWARE / ROBOTICS PROBLEMS | Surface accessibility. | `implemented_and_tested` | backend/app/safety/constraints.py; frontend/components/CameraOverlay.tsx |
| AJ6 | HARDWARE / ROBOTICS PROBLEMS | Curvature. | `implemented_and_tested` | backend/app/safety/constraints.py; frontend/components/CameraOverlay.tsx |
| AJ7 | HARDWARE / ROBOTICS PROBLEMS | Obstructions. | `implemented_and_tested` | backend/app/safety/constraints.py; frontend/components/CameraOverlay.tsx |
| AJ8 | HARDWARE / ROBOTICS PROBLEMS | Probe attachment. | `requires_physical_validation` | backend/app/safety/constraints.py; frontend/components/CameraOverlay.tsx |
| AJ9 | HARDWARE / ROBOTICS PROBLEMS | Actuator pressure. | `requires_physical_validation` | backend/app/safety/constraints.py; frontend/components/CameraOverlay.tsx |
| AJ10 | HARDWARE / ROBOTICS PROBLEMS | Travel time. | `requires_physical_validation` | backend/app/safety/constraints.py; frontend/components/CameraOverlay.tsx |
| AJ11 | HARDWARE / ROBOTICS PROBLEMS | Motion energy. | `requires_physical_validation` | backend/app/safety/constraints.py; frontend/components/CameraOverlay.tsx |
| AJ12 | HARDWARE / ROBOTICS PROBLEMS | Mechanical vibration during movement. | `requires_physical_validation` | backend/app/safety/constraints.py; frontend/components/CameraOverlay.tsx |
| AJ13 | HARDWARE / ROBOTICS PROBLEMS | Robot localization. | `requires_physical_validation` | backend/app/safety/constraints.py; frontend/components/CameraOverlay.tsx |
| AJ14 | HARDWARE / ROBOTICS PROBLEMS | Coordinate registration. | `requires_physical_validation` | backend/app/safety/constraints.py; frontend/components/CameraOverlay.tsx |
| AJ15 | HARDWARE / ROBOTICS PROBLEMS | Sensor placement error. | `requires_physical_validation` | backend/app/safety/constraints.py; frontend/components/CameraOverlay.tsx |
| AJ16 | HARDWARE / ROBOTICS PROBLEMS | Emergency stop. | `implemented_and_tested` | backend/app/safety/constraints.py; frontend/components/CameraOverlay.tsx |
| AJ17 | HARDWARE / ROBOTICS PROBLEMS | Mechanical safety limits. | `implemented_and_tested` | backend/app/safety/constraints.py; frontend/components/CameraOverlay.tsx |
| AJ18 | HARDWARE / ROBOTICS PROBLEMS | Hardware failure fallback. | `implemented_and_tested` | backend/app/safety/constraints.py; frontend/components/CameraOverlay.tsx |
| AK1 | REAL-TIME SYSTEM PROBLEMS | Acquisition latency. | `partially_mitigated` | backend/app/main.py; scripts/doctor.py |
| AK2 | REAL-TIME SYSTEM PROBLEMS | Preprocessing latency. | `partially_mitigated` | backend/app/main.py; scripts/doctor.py |
| AK3 | REAL-TIME SYSTEM PROBLEMS | Inference latency. | `implemented_and_tested` | backend/app/main.py; scripts/doctor.py |
| AK4 | REAL-TIME SYSTEM PROBLEMS | Planner latency. | `implemented_and_tested` | backend/app/main.py; scripts/doctor.py |
| AK5 | REAL-TIME SYSTEM PROBLEMS | Hardware-movement latency. | `partially_mitigated` | backend/app/main.py; scripts/doctor.py |
| AK6 | REAL-TIME SYSTEM PROBLEMS | Communication latency. | `partially_mitigated` | backend/app/main.py; scripts/doctor.py |
| AK7 | REAL-TIME SYSTEM PROBLEMS | Queue delays. | `partially_mitigated` | backend/app/main.py; scripts/doctor.py |
| AK8 | REAL-TIME SYSTEM PROBLEMS | Concurrent jobs. | `partially_mitigated` | backend/app/main.py; scripts/doctor.py |
| AK9 | REAL-TIME SYSTEM PROBLEMS | Real-time visualization overhead. | `partially_mitigated` | backend/app/main.py; scripts/doctor.py |
| AK10 | REAL-TIME SYSTEM PROBLEMS | Memory leaks. | `partially_mitigated` | backend/app/main.py; scripts/doctor.py |
| AK11 | REAL-TIME SYSTEM PROBLEMS | Long-run stability. | `partially_mitigated` | backend/app/main.py; scripts/doctor.py |
| AK12 | REAL-TIME SYSTEM PROBLEMS | Watchdog recovery. | `partially_mitigated` | backend/app/main.py; scripts/doctor.py |
| AK13 | REAL-TIME SYSTEM PROBLEMS | Logging overhead. | `implemented_and_tested` | backend/app/main.py; scripts/doctor.py |
| AK14 | REAL-TIME SYSTEM PROBLEMS | Edge/cloud synchronization. | `partially_mitigated` | backend/app/main.py; scripts/doctor.py |
| AK15 | REAL-TIME SYSTEM PROBLEMS | Offline operation. | `implemented_and_tested` | backend/app/main.py; scripts/doctor.py |
| AL1 | SOFTWARE ENGINEERING PROBLEMS | Monolithic architecture. | `partially_mitigated` | backend/tests; frontend/tests; backend/app/replay |
| AL2 | SOFTWARE ENGINEERING PROBLEMS | Tight coupling between UI and model. | `implemented_and_tested` | backend/tests; frontend/tests; backend/app/replay |
| AL3 | SOFTWARE ENGINEERING PROBLEMS | Lack of API versioning. | `implemented_and_tested` | backend/tests; frontend/tests; backend/app/replay |
| AL4 | SOFTWARE ENGINEERING PROBLEMS | Lack of model versioning. | `implemented_and_tested` | backend/tests; frontend/tests; backend/app/replay |
| AL5 | SOFTWARE ENGINEERING PROBLEMS | Lack of schema versioning. | `implemented_and_tested` | backend/tests; frontend/tests; backend/app/replay |
| AL6 | SOFTWARE ENGINEERING PROBLEMS | Lack of automated tests. | `implemented_and_tested` | backend/tests; frontend/tests; backend/app/replay |
| AL7 | SOFTWARE ENGINEERING PROBLEMS | Lack of integration tests. | `implemented_and_tested` | backend/tests; frontend/tests; backend/app/replay |
| AL8 | SOFTWARE ENGINEERING PROBLEMS | Lack of hardware-in-the-loop tests. | `partially_mitigated` | backend/tests; frontend/tests; backend/app/replay |
| AL9 | SOFTWARE ENGINEERING PROBLEMS | Lack of simulator-in-the-loop tests. | `implemented_and_tested` | backend/tests; frontend/tests; backend/app/replay |
| AL10 | SOFTWARE ENGINEERING PROBLEMS | No deterministic replay. | `implemented_and_tested` | backend/tests; frontend/tests; backend/app/replay |
| AL11 | SOFTWARE ENGINEERING PROBLEMS | No experiment replay functionality. | `implemented_and_tested` | backend/tests; frontend/tests; backend/app/replay |
| AL12 | SOFTWARE ENGINEERING PROBLEMS | No reproducible inference mode. | `implemented_and_tested` | backend/tests; frontend/tests; backend/app/replay |
| AL13 | SOFTWARE ENGINEERING PROBLEMS | Poor failure handling. | `implemented_and_tested` | backend/tests; frontend/tests; backend/app/replay |
| AL14 | SOFTWARE ENGINEERING PROBLEMS | Poor logging. | `implemented_and_tested` | backend/tests; frontend/tests; backend/app/replay |
| AL15 | SOFTWARE ENGINEERING PROBLEMS | No monitoring. | `partially_mitigated` | backend/tests; frontend/tests; backend/app/replay |
| AL16 | SOFTWARE ENGINEERING PROBLEMS | No model telemetry. | `partially_mitigated` | backend/tests; frontend/tests; backend/app/replay |
| AL17 | SOFTWARE ENGINEERING PROBLEMS | No data validation. | `implemented_and_tested` | backend/tests; frontend/tests; backend/app/replay |
| AL18 | SOFTWARE ENGINEERING PROBLEMS | No input sanity checks. | `implemented_and_tested` | backend/tests; frontend/tests; backend/app/replay |
| AL19 | SOFTWARE ENGINEERING PROBLEMS | No output sanity checks. | `implemented_and_tested` | backend/tests; frontend/tests; backend/app/replay |
| AL20 | SOFTWARE ENGINEERING PROBLEMS | No model rollback. | `partially_mitigated` | backend/tests; frontend/tests; backend/app/replay |
| AM1 | DATABASE / DATA ENGINEERING PROBLEMS | Raw waveform storage. | `partially_mitigated` | backend/app/database; backend/app/evidence/bundles.py |
| AM2 | DATABASE / DATA ENGINEERING PROBLEMS | Large waveform volume. | `partially_mitigated` | backend/app/database; backend/app/evidence/bundles.py |
| AM3 | DATABASE / DATA ENGINEERING PROBLEMS | Efficient indexing. | `partially_mitigated` | backend/app/database; backend/app/evidence/bundles.py |
| AM4 | DATABASE / DATA ENGINEERING PROBLEMS | Metadata consistency. | `implemented_and_tested` | backend/app/database; backend/app/evidence/bundles.py |
| AM5 | DATABASE / DATA ENGINEERING PROBLEMS | Sensor ID consistency. | `implemented_and_tested` | backend/app/database; backend/app/evidence/bundles.py |
| AM6 | DATABASE / DATA ENGINEERING PROBLEMS | Coordinate consistency. | `implemented_and_tested` | backend/app/database; backend/app/evidence/bundles.py |
| AM7 | DATABASE / DATA ENGINEERING PROBLEMS | Dataset versioning. | `implemented_and_tested` | backend/app/database; backend/app/evidence/bundles.py |
| AM8 | DATABASE / DATA ENGINEERING PROBLEMS | Experiment versioning. | `implemented_and_tested` | backend/app/database; backend/app/evidence/bundles.py |
| AM9 | DATABASE / DATA ENGINEERING PROBLEMS | Model versioning. | `implemented_and_tested` | backend/app/database; backend/app/evidence/bundles.py |
| AM10 | DATABASE / DATA ENGINEERING PROBLEMS | Digital-twin versioning. | `implemented_and_tested` | backend/app/database; backend/app/evidence/bundles.py |
| AM11 | DATABASE / DATA ENGINEERING PROBLEMS | Data lineage. | `implemented_and_tested` | backend/app/database; backend/app/evidence/bundles.py |
| AM12 | DATABASE / DATA ENGINEERING PROBLEMS | Data provenance. | `implemented_and_tested` | backend/app/database; backend/app/evidence/bundles.py |
| AM13 | DATABASE / DATA ENGINEERING PROBLEMS | Annotation provenance. | `partially_mitigated` | backend/app/database; backend/app/evidence/bundles.py |
| AM14 | DATABASE / DATA ENGINEERING PROBLEMS | Ground-truth provenance. | `partially_mitigated` | backend/app/database; backend/app/evidence/bundles.py |
| AM15 | DATABASE / DATA ENGINEERING PROBLEMS | Audit trail. | `implemented_and_tested` | backend/app/database; backend/app/evidence/bundles.py |
| AN1 | EVALUATION PROBLEMS | Mean localization error alone is insufficient. | `partially_mitigated` | backend/app/evaluation; scripts/neo_benchmark.py; scripts/neo_calibration.py |
| AN2 | EVALUATION PROBLEMS | Median localization error needed. | `partially_mitigated` | backend/app/evaluation; scripts/neo_benchmark.py; scripts/neo_calibration.py |
| AN3 | EVALUATION PROBLEMS | Worst-case error needed. | `partially_mitigated` | backend/app/evaluation; scripts/neo_benchmark.py; scripts/neo_calibration.py |
| AN4 | EVALUATION PROBLEMS | Percent within 5 mm. | `partially_mitigated` | backend/app/evaluation; scripts/neo_benchmark.py; scripts/neo_calibration.py |
| AN5 | EVALUATION PROBLEMS | Percent within 10 mm. | `partially_mitigated` | backend/app/evaluation; scripts/neo_benchmark.py; scripts/neo_calibration.py |
| AN6 | EVALUATION PROBLEMS | Percent within 15 mm. | `partially_mitigated` | backend/app/evaluation; scripts/neo_benchmark.py; scripts/neo_calibration.py |
| AN7 | EVALUATION PROBLEMS | Percent within 20 mm. | `partially_mitigated` | backend/app/evaluation; scripts/neo_benchmark.py; scripts/neo_calibration.py |
| AN8 | EVALUATION PROBLEMS | Defect-type accuracy. | `partially_mitigated` | backend/app/evaluation; scripts/neo_benchmark.py; scripts/neo_calibration.py |
| AN9 | EVALUATION PROBLEMS | Defect-size error. | `partially_mitigated` | backend/app/evaluation; scripts/neo_benchmark.py; scripts/neo_calibration.py |
| AN10 | EVALUATION PROBLEMS | Severity error. | `partially_mitigated` | backend/app/evaluation; scripts/neo_benchmark.py; scripts/neo_calibration.py |
| AN11 | EVALUATION PROBLEMS | Defect-count error. | `partially_mitigated` | backend/app/evaluation; scripts/neo_benchmark.py; scripts/neo_calibration.py |
| AN12 | EVALUATION PROBLEMS | False-positive rate. | `partially_mitigated` | backend/app/evaluation; scripts/neo_benchmark.py; scripts/neo_calibration.py |
| AN13 | EVALUATION PROBLEMS | False-negative rate. | `partially_mitigated` | backend/app/evaluation; scripts/neo_benchmark.py; scripts/neo_calibration.py |
| AN14 | EVALUATION PROBLEMS | Probability of detection. | `partially_mitigated` | backend/app/evaluation; scripts/neo_benchmark.py; scripts/neo_calibration.py |
| AN15 | EVALUATION PROBLEMS | Confidence calibration. | `partially_mitigated` | backend/app/evaluation; scripts/neo_benchmark.py; scripts/neo_calibration.py |
| AN16 | EVALUATION PROBLEMS | Coverage probability. | `partially_mitigated` | backend/app/evaluation; scripts/neo_benchmark.py; scripts/neo_calibration.py |
| AN17 | EVALUATION PROBLEMS | OOD detection accuracy. | `partially_mitigated` | backend/app/evaluation; scripts/neo_benchmark.py; scripts/neo_calibration.py |
| AN18 | EVALUATION PROBLEMS | Abstention quality. | `partially_mitigated` | backend/app/evaluation; scripts/neo_benchmark.py; scripts/neo_calibration.py |
| AN19 | EVALUATION PROBLEMS | Measurement count. | `partially_mitigated` | backend/app/evaluation; scripts/neo_benchmark.py; scripts/neo_calibration.py |
| AN20 | EVALUATION PROBLEMS | Time-to-confidence. | `partially_mitigated` | backend/app/evaluation; scripts/neo_benchmark.py; scripts/neo_calibration.py |
| AN21 | EVALUATION PROBLEMS | Cost-to-confidence. | `partially_mitigated` | backend/app/evaluation; scripts/neo_benchmark.py; scripts/neo_calibration.py |
| AN22 | EVALUATION PROBLEMS | Energy-to-confidence. | `partially_mitigated` | backend/app/evaluation; scripts/neo_benchmark.py; scripts/neo_calibration.py |
| AN23 | EVALUATION PROBLEMS | Probe distance. | `partially_mitigated` | backend/app/evaluation; scripts/neo_benchmark.py; scripts/neo_calibration.py |
| AN24 | EVALUATION PROBLEMS | Number of redundant experiments. | `partially_mitigated` | backend/app/evaluation; scripts/neo_benchmark.py; scripts/neo_calibration.py |
| AN25 | EVALUATION PROBLEMS | Computational latency. | `partially_mitigated` | backend/app/evaluation; scripts/neo_benchmark.py; scripts/neo_calibration.py |
| AN26 | EVALUATION PROBLEMS | Memory use. | `partially_mitigated` | backend/app/evaluation; scripts/neo_benchmark.py; scripts/neo_calibration.py |
| AN27 | EVALUATION PROBLEMS | Power consumption. | `partially_mitigated` | backend/app/evaluation; scripts/neo_benchmark.py; scripts/neo_calibration.py |
| AN28 | EVALUATION PROBLEMS | Robustness under noise. | `partially_mitigated` | backend/app/evaluation; scripts/neo_benchmark.py; scripts/neo_calibration.py |
| AN29 | EVALUATION PROBLEMS | Robustness under missing sensors. | `partially_mitigated` | backend/app/evaluation; scripts/neo_benchmark.py; scripts/neo_calibration.py |
| AN30 | EVALUATION PROBLEMS | Robustness under environmental changes. | `partially_mitigated` | backend/app/evaluation; scripts/neo_benchmark.py; scripts/neo_calibration.py |
| AN31 | EVALUATION PROBLEMS | Cross-structure generalization. | `partially_mitigated` | backend/app/evaluation; scripts/neo_benchmark.py; scripts/neo_calibration.py |
| AN32 | EVALUATION PROBLEMS | Cross-material generalization. | `partially_mitigated` | backend/app/evaluation; scripts/neo_benchmark.py; scripts/neo_calibration.py |
| AN33 | EVALUATION PROBLEMS | Cross-hardware generalization. | `partially_mitigated` | backend/app/evaluation; scripts/neo_benchmark.py; scripts/neo_calibration.py |
| AN34 | EVALUATION PROBLEMS | Cross-defect generalization. | `partially_mitigated` | backend/app/evaluation; scripts/neo_benchmark.py; scripts/neo_calibration.py |
| AN35 | EVALUATION PROBLEMS | Statistical significance. | `partially_mitigated` | backend/app/evaluation; scripts/neo_benchmark.py; scripts/neo_calibration.py |
| AN36 | EVALUATION PROBLEMS | Confidence intervals. | `partially_mitigated` | backend/app/evaluation; scripts/neo_benchmark.py; scripts/neo_calibration.py |
| AN37 | EVALUATION PROBLEMS | Effect sizes. | `partially_mitigated` | backend/app/evaluation; scripts/neo_benchmark.py; scripts/neo_calibration.py |
| AN38 | EVALUATION PROBLEMS | Multiple-seed variance. | `partially_mitigated` | backend/app/evaluation; scripts/neo_benchmark.py; scripts/neo_calibration.py |
| AN39 | EVALUATION PROBLEMS | Ablation results. | `partially_mitigated` | backend/app/evaluation; scripts/neo_benchmark.py; scripts/neo_calibration.py |
| AO1 | BENCHMARK DESIGN PROBLEMS | Need fixed-budget benchmark. | `partially_mitigated` | docs/BENCHMARK_PROTOCOL.md; backend/app/replay |
| AO2 | BENCHMARK DESIGN PROBLEMS | Need fixed-accuracy benchmark. | `partially_mitigated` | docs/BENCHMARK_PROTOCOL.md; backend/app/replay |
| AO3 | BENCHMARK DESIGN PROBLEMS | Need fixed-time benchmark. | `partially_mitigated` | docs/BENCHMARK_PROTOCOL.md; backend/app/replay |
| AO4 | BENCHMARK DESIGN PROBLEMS | Need fixed-cost benchmark. | `partially_mitigated` | docs/BENCHMARK_PROTOCOL.md; backend/app/replay |
| AO5 | BENCHMARK DESIGN PROBLEMS | Need same hardware across methods. | `partially_mitigated` | docs/BENCHMARK_PROTOCOL.md; backend/app/replay |
| AO6 | BENCHMARK DESIGN PROBLEMS | Need same initial prior. | `partially_mitigated` | docs/BENCHMARK_PROTOCOL.md; backend/app/replay |
| AO7 | BENCHMARK DESIGN PROBLEMS | Need same candidate action space. | `partially_mitigated` | docs/BENCHMARK_PROTOCOL.md; backend/app/replay |
| AO8 | BENCHMARK DESIGN PROBLEMS | Need same preprocessing. | `partially_mitigated` | docs/BENCHMARK_PROTOCOL.md; backend/app/replay |
| AO9 | BENCHMARK DESIGN PROBLEMS | Need independent test set. | `partially_mitigated` | docs/BENCHMARK_PROTOCOL.md; backend/app/replay |
| AO10 | BENCHMARK DESIGN PROBLEMS | Need completely blind physical test set. | `partially_mitigated` | docs/BENCHMARK_PROTOCOL.md; backend/app/replay |
| AO11 | BENCHMARK DESIGN PROBLEMS | Need structure-level split. | `partially_mitigated` | docs/BENCHMARK_PROTOCOL.md; backend/app/replay |
| AO12 | BENCHMARK DESIGN PROBLEMS | Need defect-level split. | `partially_mitigated` | docs/BENCHMARK_PROTOCOL.md; backend/app/replay |
| AO13 | BENCHMARK DESIGN PROBLEMS | Need environmental split. | `partially_mitigated` | docs/BENCHMARK_PROTOCOL.md; backend/app/replay |
| AO14 | BENCHMARK DESIGN PROBLEMS | Need hardware split. | `partially_mitigated` | docs/BENCHMARK_PROTOCOL.md; backend/app/replay |
| AO15 | BENCHMARK DESIGN PROBLEMS | Need leave-one-structure-out validation. | `partially_mitigated` | docs/BENCHMARK_PROTOCOL.md; backend/app/replay |
| AO16 | BENCHMARK DESIGN PROBLEMS | Need cross-dataset validation. | `partially_mitigated` | docs/BENCHMARK_PROTOCOL.md; backend/app/replay |
| AO17 | BENCHMARK DESIGN PROBLEMS | Need external benchmark. | `partially_mitigated` | docs/BENCHMARK_PROTOCOL.md; backend/app/replay |
| AP1 | STATISTICS PROBLEMS | 30 cases is small. | `partially_mitigated` | backend/app/evaluation/benchmark.py; backend/app/evaluation/calibration_study.py |
| AP2 | STATISTICS PROBLEMS | Mean differences may be unstable. | `partially_mitigated` | backend/app/evaluation/benchmark.py; backend/app/evaluation/calibration_study.py |
| AP3 | STATISTICS PROBLEMS | Confidence intervals may cross zero. | `partially_mitigated` | backend/app/evaluation/benchmark.py; backend/app/evaluation/calibration_study.py |
| AP4 | STATISTICS PROBLEMS | Statistical significance may be absent. | `partially_mitigated` | backend/app/evaluation/benchmark.py; backend/app/evaluation/calibration_study.py |
| AP5 | STATISTICS PROBLEMS | Multiple comparisons may inflate false discoveries. | `partially_mitigated` | backend/app/evaluation/benchmark.py; backend/app/evaluation/calibration_study.py |
| AP6 | STATISTICS PROBLEMS | Need effect size. | `partially_mitigated` | backend/app/evaluation/benchmark.py; backend/app/evaluation/calibration_study.py |
| AP7 | STATISTICS PROBLEMS | Need bootstrap confidence intervals. | `partially_mitigated` | backend/app/evaluation/benchmark.py; backend/app/evaluation/calibration_study.py |
| AP8 | STATISTICS PROBLEMS | Need appropriate paired tests when experiments are paired. | `partially_mitigated` | backend/app/evaluation/benchmark.py; backend/app/evaluation/calibration_study.py |
| AP9 | STATISTICS PROBLEMS | Need nonparametric tests where assumptions fail. | `partially_mitigated` | backend/app/evaluation/benchmark.py; backend/app/evaluation/calibration_study.py |
| AP10 | STATISTICS PROBLEMS | Need uncertainty on all major metrics. | `partially_mitigated` | backend/app/evaluation/benchmark.py; backend/app/evaluation/calibration_study.py |
| AP11 | STATISTICS PROBLEMS | Need sensitivity analysis. | `partially_mitigated` | backend/app/evaluation/benchmark.py; backend/app/evaluation/calibration_study.py |
| AP12 | STATISTICS PROBLEMS | Need power analysis for physical experiments. | `partially_mitigated` | backend/app/evaluation/benchmark.py; backend/app/evaluation/calibration_study.py |
| AQ1 | ABLATION-STUDY PROBLEMS | Cannot know whether Bayesian inference actually helps. | `partially_mitigated` | scripts/neo_benchmark.py; research_results/neo_ablation_quick.json |
| AQ2 | ABLATION-STUDY PROBLEMS | Cannot know whether physics helps. | `partially_mitigated` | scripts/neo_benchmark.py; research_results/neo_ablation_quick.json |
| AQ3 | ABLATION-STUDY PROBLEMS | Cannot know whether learned features help. | `partially_mitigated` | scripts/neo_benchmark.py; research_results/neo_ablation_quick.json |
| AQ4 | ABLATION-STUDY PROBLEMS | Cannot know whether GNN helps. | `partially_mitigated` | scripts/neo_benchmark.py; research_results/neo_ablation_quick.json |
| AQ5 | ABLATION-STUDY PROBLEMS | Cannot know whether multimodal fusion helps. | `partially_mitigated` | scripts/neo_benchmark.py; research_results/neo_ablation_quick.json |
| AQ6 | ABLATION-STUDY PROBLEMS | Cannot know whether uncertainty helps. | `partially_mitigated` | scripts/neo_benchmark.py; research_results/neo_ablation_quick.json |
| AQ7 | ABLATION-STUDY PROBLEMS | Cannot know whether OOD helps. | `partially_mitigated` | scripts/neo_benchmark.py; research_results/neo_ablation_quick.json |
| AQ8 | ABLATION-STUDY PROBLEMS | Cannot know whether active planning helps. | `partially_mitigated` | scripts/neo_benchmark.py; research_results/neo_ablation_quick.json |
| AQ9 | ABLATION-STUDY PROBLEMS | Cannot know whether cost-awareness helps. | `partially_mitigated` | scripts/neo_benchmark.py; research_results/neo_ablation_quick.json |
| AQ10 | ABLATION-STUDY PROBLEMS | Cannot know whether redundancy penalty helps. | `partially_mitigated` | scripts/neo_benchmark.py; research_results/neo_ablation_quick.json |
| AQ11 | ABLATION-STUDY PROBLEMS | Cannot know which planner terms matter. | `partially_mitigated` | scripts/neo_benchmark.py; research_results/neo_ablation_quick.json |
| AQ12 | ABLATION-STUDY PROBLEMS | Need removal/addition studies for every major contribution. | `partially_mitigated` | scripts/neo_benchmark.py; research_results/neo_ablation_quick.json |
| AR1 | RESEARCH NOVELTY PROBLEMS | Bayesian active sensing is NOT inherently novel. | `requires_literature_or_legal_review` | docs/PATENT_LANDSCAPE_AND_COMMERCIALIZATION.md; docs/PRIOR_ART_NOTES.md |
| AR2 | RESEARCH NOVELTY PROBLEMS | Bayesian sensor placement is established research. | `requires_literature_or_legal_review` | docs/PATENT_LANDSCAPE_AND_COMMERCIALIZATION.md; docs/PRIOR_ART_NOTES.md |
| AR3 | RESEARCH NOVELTY PROBLEMS | Cost-aware sensor placement is established research. | `requires_literature_or_legal_review` | docs/PATENT_LANDSCAPE_AND_COMMERCIALIZATION.md; docs/PRIOR_ART_NOTES.md |
| AR4 | RESEARCH NOVELTY PROBLEMS | Physics-informed GNNs are already published. | `requires_literature_or_legal_review` | docs/PATENT_LANDSCAPE_AND_COMMERCIALIZATION.md; docs/PRIOR_ART_NOTES.md |
| AR5 | RESEARCH NOVELTY PROBLEMS | Domain-adaptive GNNs are already published. | `requires_literature_or_legal_review` | docs/PATENT_LANDSCAPE_AND_COMMERCIALIZATION.md; docs/PRIOR_ART_NOTES.md |
| AR6 | RESEARCH NOVELTY PROBLEMS | Digital-twin SHM is already published. | `requires_literature_or_legal_review` | docs/PATENT_LANDSCAPE_AND_COMMERCIALIZATION.md; docs/PRIOR_ART_NOTES.md |
| AR7 | RESEARCH NOVELTY PROBLEMS | Multimodal guided-wave damage detection is already being published. | `requires_literature_or_legal_review` | docs/PATENT_LANDSCAPE_AND_COMMERCIALIZATION.md; docs/PRIOR_ART_NOTES.md |
| AR8 | RESEARCH NOVELTY PROBLEMS | Baseline-free guided-wave ML is already being published. | `requires_literature_or_legal_review` | docs/PATENT_LANDSCAPE_AND_COMMERCIALIZATION.md; docs/PRIOR_ART_NOTES.md |
| AR9 | RESEARCH NOVELTY PROBLEMS | Autonomous guided-wave SHM is already being published. | `requires_literature_or_legal_review` | docs/PATENT_LANDSCAPE_AND_COMMERCIALIZATION.md; docs/PRIOR_ART_NOTES.md |
| AR10 | RESEARCH NOVELTY PROBLEMS | Therefore novelty cannot simply be: "We used AI for defect detection." | `requires_literature_or_legal_review` | docs/PATENT_LANDSCAPE_AND_COMMERCIALIZATION.md; docs/PRIOR_ART_NOTES.md |
| AR11 | RESEARCH NOVELTY PROBLEMS | Novelty cannot simply be: "We used a GNN." | `requires_literature_or_legal_review` | docs/PATENT_LANDSCAPE_AND_COMMERCIALIZATION.md; docs/PRIOR_ART_NOTES.md |
| AR12 | RESEARCH NOVELTY PROBLEMS | Novelty cannot simply be: "We used a Transformer." | `requires_literature_or_legal_review` | docs/PATENT_LANDSCAPE_AND_COMMERCIALIZATION.md; docs/PRIOR_ART_NOTES.md |
| AR13 | RESEARCH NOVELTY PROBLEMS | Novelty cannot simply be: "We used a digital twin." | `requires_literature_or_legal_review` | docs/PATENT_LANDSCAPE_AND_COMMERCIALIZATION.md; docs/PRIOR_ART_NOTES.md |
| AR14 | RESEARCH NOVELTY PROBLEMS | Novelty cannot simply be: "We used Bayesian inference." | `requires_literature_or_legal_review` | docs/PATENT_LANDSCAPE_AND_COMMERCIALIZATION.md; docs/PRIOR_ART_NOTES.md |
| AR15 | RESEARCH NOVELTY PROBLEMS | Novelty should emerge from a specific new combination, algorithmic mechanism, objective, benchmark or experimentally demonstrated capability. | `requires_literature_or_legal_review` | docs/PATENT_LANDSCAPE_AND_COMMERCIALIZATION.md; docs/PRIOR_ART_NOTES.md |
| AR16 | RESEARCH NOVELTY PROBLEMS | Need a formal literature novelty matrix. | `requires_literature_or_legal_review` | docs/PATENT_LANDSCAPE_AND_COMMERCIALIZATION.md; docs/PRIOR_ART_NOTES.md |
| AR17 | RESEARCH NOVELTY PROBLEMS | Need claim-by-claim prior-art checking before publication. | `requires_literature_or_legal_review` | docs/PATENT_LANDSCAPE_AND_COMMERCIALIZATION.md; docs/PRIOR_ART_NOTES.md |
| AR18 | RESEARCH NOVELTY PROBLEMS | Need novelty claims frozen only after literature search. | `requires_literature_or_legal_review` | docs/PATENT_LANDSCAPE_AND_COMMERCIALIZATION.md; docs/PRIOR_ART_NOTES.md |
| AS1 | HUMAN-IN-THE-LOOP PROBLEMS | Operator may override model. | `partially_mitigated` | backend/app/services/session_manager.py; frontend/components/ArgusBrain.tsx |
| AS2 | HUMAN-IN-THE-LOOP PROBLEMS | Operator may disagree with model. | `partially_mitigated` | backend/app/services/session_manager.py; frontend/components/ArgusBrain.tsx |
| AS3 | HUMAN-IN-THE-LOOP PROBLEMS | Human override may not be logged. | `implemented_and_tested` | backend/app/services/session_manager.py; frontend/components/ArgusBrain.tsx |
| AS4 | HUMAN-IN-THE-LOOP PROBLEMS | Model recommendation may not be understandable. | `implemented_and_tested` | backend/app/services/session_manager.py; frontend/components/ArgusBrain.tsx |
| AS5 | HUMAN-IN-THE-LOOP PROBLEMS | Human may over-trust confidence scores. | `partially_mitigated` | backend/app/services/session_manager.py; frontend/components/ArgusBrain.tsx |
| AS6 | HUMAN-IN-THE-LOOP PROBLEMS | Human may ignore abstention warnings. | `partially_mitigated` | backend/app/services/session_manager.py; frontend/components/ArgusBrain.tsx |
| AS7 | HUMAN-IN-THE-LOOP PROBLEMS | Human may accept false negatives. | `partially_mitigated` | backend/app/services/session_manager.py; frontend/components/ArgusBrain.tsx |
| AS8 | HUMAN-IN-THE-LOOP PROBLEMS | Human may request manual inspection. | `implemented_and_tested` | backend/app/services/session_manager.py; frontend/components/ArgusBrain.tsx |
| AS9 | HUMAN-IN-THE-LOOP PROBLEMS | Human feedback could be incorporated. | `partially_mitigated` | backend/app/services/session_manager.py; frontend/components/ArgusBrain.tsx |
| AS10 | HUMAN-IN-THE-LOOP PROBLEMS | Need clear human/system responsibility boundaries. | `implemented_and_tested` | backend/app/services/session_manager.py; frontend/components/ArgusBrain.tsx |
| AS11 | HUMAN-IN-THE-LOOP PROBLEMS | Need interface for uncertainty. | `implemented_and_tested` | backend/app/services/session_manager.py; frontend/components/ArgusBrain.tsx |
| AS12 | HUMAN-IN-THE-LOOP PROBLEMS | Need interface for sensor health. | `implemented_and_tested` | backend/app/services/session_manager.py; frontend/components/ArgusBrain.tsx |
| AS13 | HUMAN-IN-THE-LOOP PROBLEMS | Need interface for inspection history. | `implemented_and_tested` | backend/app/services/session_manager.py; frontend/components/ArgusBrain.tsx |
| AT1 | SAFETY PROBLEMS | False negative may miss critical damage. | `partially_mitigated` | backend/app/safety/constraints.py; emergency-stop API |
| AT2 | SAFETY PROBLEMS | False confidence can be more dangerous than low confidence. | `partially_mitigated` | backend/app/safety/constraints.py; emergency-stop API |
| AT3 | SAFETY PROBLEMS | Sensor fault can be mistaken for healthy structure. | `implemented_and_tested` | backend/app/safety/constraints.py; emergency-stop API |
| AT4 | SAFETY PROBLEMS | Unknown damage can be forced into known class. | `implemented_and_tested` | backend/app/safety/constraints.py; emergency-stop API |
| AT5 | SAFETY PROBLEMS | Excessive excitation could potentially affect sensitive structures. | `partially_mitigated` | backend/app/safety/constraints.py; emergency-stop API |
| AT6 | SAFETY PROBLEMS | Probe motion could damage surfaces. | `partially_mitigated` | backend/app/safety/constraints.py; emergency-stop API |
| AT7 | SAFETY PROBLEMS | Hardware failure could interrupt inspection. | `partially_mitigated` | backend/app/safety/constraints.py; emergency-stop API |
| AT8 | SAFETY PROBLEMS | Need safety limits on excitation. | `implemented_and_tested` | backend/app/safety/constraints.py; emergency-stop API |
| AT9 | SAFETY PROBLEMS | Need action constraints. | `implemented_and_tested` | backend/app/safety/constraints.py; emergency-stop API |
| AT10 | SAFETY PROBLEMS | Need emergency shutdown. | `implemented_and_tested` | backend/app/safety/constraints.py; emergency-stop API |
| AT11 | SAFETY PROBLEMS | Need human escalation path. | `implemented_and_tested` | backend/app/safety/constraints.py; emergency-stop API |
| AT12 | SAFETY PROBLEMS | Need safe fallback mode. | `implemented_and_tested` | backend/app/safety/constraints.py; emergency-stop API |
| AU1 | INDUSTRIAL DEPLOYMENT PROBLEMS | Model trained on one structure may fail on another. | `requires_physical_validation` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AU2 | INDUSTRIAL DEPLOYMENT PROBLEMS | Model trained in a lab may fail in the field. | `requires_physical_validation` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AU3 | INDUSTRIAL DEPLOYMENT PROBLEMS | Model trained on one hardware stack may fail on another. | `requires_physical_validation` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AU4 | INDUSTRIAL DEPLOYMENT PROBLEMS | Model needs calibration after deployment. | `requires_physical_validation` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AU5 | INDUSTRIAL DEPLOYMENT PROBLEMS | Calibration may require labeled defects. | `requires_physical_validation` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AU6 | INDUSTRIAL DEPLOYMENT PROBLEMS | Labeled physical defects are expensive. | `requires_physical_validation` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AU7 | INDUSTRIAL DEPLOYMENT PROBLEMS | Inspection downtime is expensive. | `requires_physical_validation` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AU8 | INDUSTRIAL DEPLOYMENT PROBLEMS | Equipment cost matters. | `requires_physical_validation` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AU9 | INDUSTRIAL DEPLOYMENT PROBLEMS | Sensor installation cost matters. | `requires_physical_validation` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AU10 | INDUSTRIAL DEPLOYMENT PROBLEMS | Maintenance cost matters. | `requires_physical_validation` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AU11 | INDUSTRIAL DEPLOYMENT PROBLEMS | Operator training cost matters. | `requires_physical_validation` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AU12 | INDUSTRIAL DEPLOYMENT PROBLEMS | False alarms create operational burden. | `requires_physical_validation` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AU13 | INDUSTRIAL DEPLOYMENT PROBLEMS | Missed defects create safety risk. | `requires_physical_validation` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AU14 | INDUSTRIAL DEPLOYMENT PROBLEMS | Need lifecycle cost model. | `requires_physical_validation` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AU15 | INDUSTRIAL DEPLOYMENT PROBLEMS | Need deployment monitoring. | `requires_physical_validation` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AU16 | INDUSTRIAL DEPLOYMENT PROBLEMS | Need model drift monitoring. | `requires_physical_validation` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AU17 | INDUSTRIAL DEPLOYMENT PROBLEMS | Need periodic validation. | `requires_physical_validation` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AU18 | INDUSTRIAL DEPLOYMENT PROBLEMS | Need rollback capability. | `requires_physical_validation` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AU19 | INDUSTRIAL DEPLOYMENT PROBLEMS | Need audit logs. | `requires_physical_validation` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AU20 | INDUSTRIAL DEPLOYMENT PROBLEMS | Need cybersecurity. | `requires_physical_validation` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AV1 | EDGE AI PROBLEMS | CPU-only inference. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AV2 | EDGE AI PROBLEMS | Low-memory deployment. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AV3 | EDGE AI PROBLEMS | Quantization. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AV4 | EDGE AI PROBLEMS | Model compression. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AV5 | EDGE AI PROBLEMS | Streaming inference. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AV6 | EDGE AI PROBLEMS | Limited storage. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AV7 | EDGE AI PROBLEMS | Power consumption. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AV8 | EDGE AI PROBLEMS | Thermal limits. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AV9 | EDGE AI PROBLEMS | Intermittent connectivity. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AV10 | EDGE AI PROBLEMS | Offline operation. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AV11 | EDGE AI PROBLEMS | On-device preprocessing. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AV12 | EDGE AI PROBLEMS | On-device anomaly detection. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AV13 | EDGE AI PROBLEMS | Edge/cloud consistency. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AV14 | EDGE AI PROBLEMS | Version synchronization. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AW1 | EXPLAINABILITY / SCIENTIFIC TRUST PROBLEMS | Need evidence from raw waveform. | `implemented_and_tested` | frontend/components/SignalPlots.tsx; frontend/components/ArgusBrain.tsx |
| AW2 | EXPLAINABILITY / SCIENTIFIC TRUST PROBLEMS | Need evidence from residual waveform. | `implemented_and_tested` | frontend/components/SignalPlots.tsx; frontend/components/ArgusBrain.tsx |
| AW3 | EXPLAINABILITY / SCIENTIFIC TRUST PROBLEMS | Need predicted arrival-time evidence. | `implemented_and_tested` | frontend/components/SignalPlots.tsx; frontend/components/ArgusBrain.tsx |
| AW4 | EXPLAINABILITY / SCIENTIFIC TRUST PROBLEMS | Need physical-path explanation. | `implemented_and_tested` | frontend/components/SignalPlots.tsx; frontend/components/ArgusBrain.tsx |
| AW5 | EXPLAINABILITY / SCIENTIFIC TRUST PROBLEMS | Need hypothesis comparison. | `implemented_and_tested` | frontend/components/SignalPlots.tsx; frontend/components/ArgusBrain.tsx |
| AW6 | EXPLAINABILITY / SCIENTIFIC TRUST PROBLEMS | Need planner explanation. | `implemented_and_tested` | frontend/components/SignalPlots.tsx; frontend/components/ArgusBrain.tsx |
| AW7 | EXPLAINABILITY / SCIENTIFIC TRUST PROBLEMS | Need reason for stopping. | `implemented_and_tested` | frontend/components/SignalPlots.tsx; frontend/components/ArgusBrain.tsx |
| AW8 | EXPLAINABILITY / SCIENTIFIC TRUST PROBLEMS | Need reason for abstaining. | `implemented_and_tested` | frontend/components/SignalPlots.tsx; frontend/components/ArgusBrain.tsx |
| AW9 | EXPLAINABILITY / SCIENTIFIC TRUST PROBLEMS | Need reason for rejecting sensor. | `implemented_and_tested` | frontend/components/SignalPlots.tsx; frontend/components/ArgusBrain.tsx |
| AW10 | EXPLAINABILITY / SCIENTIFIC TRUST PROBLEMS | Need confidence decomposition. | `implemented_and_tested` | frontend/components/SignalPlots.tsx; frontend/components/ArgusBrain.tsx |
| AW11 | EXPLAINABILITY / SCIENTIFIC TRUST PROBLEMS | Need distinguish model confidence from physical evidence. | `implemented_and_tested` | frontend/components/SignalPlots.tsx; frontend/components/ArgusBrain.tsx |
| AX1 | REPRODUCIBILITY PROBLEMS | Random seeds. | `implemented_and_tested` | docs/REPRODUCIBILITY.md; scripts/doctor.py; backend/app/replay |
| AX2 | REPRODUCIBILITY PROBLEMS | Exact dataset versions. | `implemented_and_tested` | docs/REPRODUCIBILITY.md; scripts/doctor.py; backend/app/replay |
| AX3 | REPRODUCIBILITY PROBLEMS | Exact simulator parameters. | `implemented_and_tested` | docs/REPRODUCIBILITY.md; scripts/doctor.py; backend/app/replay |
| AX4 | REPRODUCIBILITY PROBLEMS | Exact hardware configuration. | `partially_mitigated` | docs/REPRODUCIBILITY.md; scripts/doctor.py; backend/app/replay |
| AX5 | REPRODUCIBILITY PROBLEMS | Exact sensor positions. | `implemented_and_tested` | docs/REPRODUCIBILITY.md; scripts/doctor.py; backend/app/replay |
| AX6 | REPRODUCIBILITY PROBLEMS | Exact preprocessing. | `implemented_and_tested` | docs/REPRODUCIBILITY.md; scripts/doctor.py; backend/app/replay |
| AX7 | REPRODUCIBILITY PROBLEMS | Exact model weights. | `partially_mitigated` | docs/REPRODUCIBILITY.md; scripts/doctor.py; backend/app/replay |
| AX8 | REPRODUCIBILITY PROBLEMS | Exact planner coefficients. | `implemented_and_tested` | docs/REPRODUCIBILITY.md; scripts/doctor.py; backend/app/replay |
| AX9 | REPRODUCIBILITY PROBLEMS | Exact evaluation split. | `implemented_and_tested` | docs/REPRODUCIBILITY.md; scripts/doctor.py; backend/app/replay |
| AX10 | REPRODUCIBILITY PROBLEMS | Exact software environment. | `implemented_and_tested` | docs/REPRODUCIBILITY.md; scripts/doctor.py; backend/app/replay |
| AX11 | REPRODUCIBILITY PROBLEMS | Containerized deployment. | `partially_mitigated` | docs/REPRODUCIBILITY.md; scripts/doctor.py; backend/app/replay |
| AX12 | REPRODUCIBILITY PROBLEMS | Reproducible benchmark script. | `implemented_and_tested` | docs/REPRODUCIBILITY.md; scripts/doctor.py; backend/app/replay |
| AX13 | REPRODUCIBILITY PROBLEMS | Automated experiment runner. | `implemented_and_tested` | docs/REPRODUCIBILITY.md; scripts/doctor.py; backend/app/replay |
| AX14 | REPRODUCIBILITY PROBLEMS | Public configuration files. | `implemented_and_tested` | docs/REPRODUCIBILITY.md; scripts/doctor.py; backend/app/replay |
| AY1 | PHYSICAL VALIDATION PROBLEMS | Too few physical panels. | `requires_physical_validation` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AY2 | PHYSICAL VALIDATION PROBLEMS | Too few defect locations. | `requires_physical_validation` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AY3 | PHYSICAL VALIDATION PROBLEMS | Too few defect types. | `requires_physical_validation` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AY4 | PHYSICAL VALIDATION PROBLEMS | Too few repetitions. | `requires_physical_validation` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AY5 | PHYSICAL VALIDATION PROBLEMS | Ground truth may be uncertain. | `requires_physical_validation` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AY6 | PHYSICAL VALIDATION PROBLEMS | Need independent ground truth. | `requires_physical_validation` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AY7 | PHYSICAL VALIDATION PROBLEMS | Need blind testing. | `requires_physical_validation` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AY8 | PHYSICAL VALIDATION PROBLEMS | Need previously unseen panels. | `requires_physical_validation` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AY9 | PHYSICAL VALIDATION PROBLEMS | Need previously unseen defects. | `requires_physical_validation` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AY10 | PHYSICAL VALIDATION PROBLEMS | Need environmental variation. | `requires_physical_validation` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AY11 | PHYSICAL VALIDATION PROBLEMS | Need sensor repositioning tests. | `requires_physical_validation` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AY12 | PHYSICAL VALIDATION PROBLEMS | Need hardware variation. | `requires_physical_validation` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AY13 | PHYSICAL VALIDATION PROBLEMS | Need sensor-fault experiments. | `requires_physical_validation` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AY14 | PHYSICAL VALIDATION PROBLEMS | Need noise experiments. | `requires_physical_validation` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AY15 | PHYSICAL VALIDATION PROBLEMS | Need long-term tests. | `requires_physical_validation` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AY16 | PHYSICAL VALIDATION PROBLEMS | Need repeatability tests. | `requires_physical_validation` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AY17 | PHYSICAL VALIDATION PROBLEMS | Need reproducibility across operators. | `requires_physical_validation` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AY18 | PHYSICAL VALIDATION PROBLEMS | Need true closed-loop physical experiment. | `requires_physical_validation` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AZ1 | DIGITAL-TWIN VALIDATION PROBLEMS | Validate direct wave arrival. | `requires_physical_validation` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AZ2 | DIGITAL-TWIN VALIDATION PROBLEMS | Validate defect-scattered arrival. | `requires_physical_validation` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AZ3 | DIGITAL-TWIN VALIDATION PROBLEMS | Validate amplitude. | `requires_physical_validation` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AZ4 | DIGITAL-TWIN VALIDATION PROBLEMS | Validate attenuation. | `requires_physical_validation` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AZ5 | DIGITAL-TWIN VALIDATION PROBLEMS | Validate spectrum. | `requires_physical_validation` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AZ6 | DIGITAL-TWIN VALIDATION PROBLEMS | Validate phase where relevant. | `requires_physical_validation` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AZ7 | DIGITAL-TWIN VALIDATION PROBLEMS | Validate temperature response. | `requires_physical_validation` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AZ8 | DIGITAL-TWIN VALIDATION PROBLEMS | Validate sensor response. | `requires_physical_validation` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AZ9 | DIGITAL-TWIN VALIDATION PROBLEMS | Validate boundary behavior. | `requires_physical_validation` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AZ10 | DIGITAL-TWIN VALIDATION PROBLEMS | Validate defect geometry response. | `requires_physical_validation` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AZ11 | DIGITAL-TWIN VALIDATION PROBLEMS | Quantify simulator error. | `requires_physical_validation` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AZ12 | DIGITAL-TWIN VALIDATION PROBLEMS | Quantify surrogate error. | `requires_physical_validation` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| AZ13 | DIGITAL-TWIN VALIDATION PROBLEMS | Propagate simulator uncertainty into posterior. | `requires_physical_validation` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| BA1 | MODEL FAILURE INTERPRETATION | Need classify failures into: - physics mismatch - sensor failure - insufficient data - ambiguity - model error - planner error - domain shift. | `implemented_and_tested` | backend/app/assurance/monitor.py; backend/app/research/failure_explorer.py |
| BA2 | MODEL FAILURE INTERPRETATION | Need failure taxonomy. | `implemented_and_tested` | backend/app/assurance/monitor.py; backend/app/research/failure_explorer.py |
| BA3 | MODEL FAILURE INTERPRETATION | Need automatically log failure conditions. | `implemented_and_tested` | backend/app/assurance/monitor.py; backend/app/research/failure_explorer.py |
| BA4 | MODEL FAILURE INTERPRETATION | Need post-mortem analysis. | `implemented_and_tested` | backend/app/assurance/monitor.py; backend/app/research/failure_explorer.py |
| BA5 | MODEL FAILURE INTERPRETATION | Need failure replay. | `implemented_and_tested` | backend/app/assurance/monitor.py; backend/app/research/failure_explorer.py |
| BA6 | MODEL FAILURE INTERPRETATION | Need counterfactual analysis. | `implemented_and_tested` | backend/app/assurance/monitor.py; backend/app/research/failure_explorer.py |
| BB1 | COUNTERFACTUAL REASONING PROBLEMS | Current planner may generate counterfactual responses using simplified physics. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| BB2 | COUNTERFACTUAL REASONING PROBLEMS | Counterfactual model can be wrong. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| BB3 | COUNTERFACTUAL REASONING PROBLEMS | Hypothesis disagreement can be artificially large. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| BB4 | COUNTERFACTUAL REASONING PROBLEMS | Hypothesis disagreement can be artificially small. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| BB5 | COUNTERFACTUAL REASONING PROBLEMS | Need validate predicted discrimination experimentally. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| BB6 | COUNTERFACTUAL REASONING PROBLEMS | Need compare predicted vs observed information gain. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| BB7 | COUNTERFACTUAL REASONING PROBLEMS | Need calibrate expected information gain. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| BB8 | COUNTERFACTUAL REASONING PROBLEMS | Need model uncertainty in counterfactual predictions. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| BC1 | EXPERIMENTAL DESIGN PROBLEMS | Candidate space may be continuous. | `partially_mitigated` | backend/app/active_learning/neo_planner.py; backend/app/safety/constraints.py |
| BC2 | EXPERIMENTAL DESIGN PROBLEMS | Candidate space may be mixed discrete/continuous. | `partially_mitigated` | backend/app/active_learning/neo_planner.py; backend/app/safety/constraints.py |
| BC3 | EXPERIMENTAL DESIGN PROBLEMS | Frequency selection may be continuous. | `partially_mitigated` | backend/app/active_learning/neo_planner.py; backend/app/safety/constraints.py |
| BC4 | EXPERIMENTAL DESIGN PROBLEMS | Geometry selection may be continuous. | `partially_mitigated` | backend/app/active_learning/neo_planner.py; backend/app/safety/constraints.py |
| BC5 | EXPERIMENTAL DESIGN PROBLEMS | Waveform selection may be categorical. | `partially_mitigated` | backend/app/active_learning/neo_planner.py; backend/app/safety/constraints.py |
| BC6 | EXPERIMENTAL DESIGN PROBLEMS | Amplitude selection may be continuous. | `partially_mitigated` | backend/app/active_learning/neo_planner.py; backend/app/safety/constraints.py |
| BC7 | EXPERIMENTAL DESIGN PROBLEMS | Duration selection may be continuous. | `partially_mitigated` | backend/app/active_learning/neo_planner.py; backend/app/safety/constraints.py |
| BC8 | EXPERIMENTAL DESIGN PROBLEMS | Action feasibility constraints. | `implemented_and_tested` | backend/app/active_learning/neo_planner.py; backend/app/safety/constraints.py |
| BC9 | EXPERIMENTAL DESIGN PROBLEMS | Mechanical constraints. | `implemented_and_tested` | backend/app/active_learning/neo_planner.py; backend/app/safety/constraints.py |
| BC10 | EXPERIMENTAL DESIGN PROBLEMS | Safety constraints. | `implemented_and_tested` | backend/app/active_learning/neo_planner.py; backend/app/safety/constraints.py |
| BC11 | EXPERIMENTAL DESIGN PROBLEMS | Cost constraints. | `implemented_and_tested` | backend/app/active_learning/neo_planner.py; backend/app/safety/constraints.py |
| BC12 | EXPERIMENTAL DESIGN PROBLEMS | Sensor availability constraints. | `implemented_and_tested` | backend/app/active_learning/neo_planner.py; backend/app/safety/constraints.py |
| BC13 | EXPERIMENTAL DESIGN PROBLEMS | Need efficient optimization. | `implemented_and_tested` | backend/app/active_learning/neo_planner.py; backend/app/safety/constraints.py |
| BC14 | EXPERIMENTAL DESIGN PROBLEMS | Need candidate pruning. | `implemented_and_tested` | backend/app/active_learning/neo_planner.py; backend/app/safety/constraints.py |
| BC15 | EXPERIMENTAL DESIGN PROBLEMS | Need uncertainty-aware planning. | `implemented_and_tested` | backend/app/active_learning/neo_planner.py; backend/app/safety/constraints.py |
| BD1 | MULTI-OBJECTIVE OPTIMIZATION PROBLEMS | Information gain. | `implemented_and_tested` | backend/app/active_learning/neo_planner.py; backend/app/decision/loss.py |
| BD2 | MULTI-OBJECTIVE OPTIMIZATION PROBLEMS | Localization improvement. | `implemented_and_tested` | backend/app/active_learning/neo_planner.py; backend/app/decision/loss.py |
| BD3 | MULTI-OBJECTIVE OPTIMIZATION PROBLEMS | Detection probability. | `partially_mitigated` | backend/app/active_learning/neo_planner.py; backend/app/decision/loss.py |
| BD4 | MULTI-OBJECTIVE OPTIMIZATION PROBLEMS | Measurement time. | `implemented_and_tested` | backend/app/active_learning/neo_planner.py; backend/app/decision/loss.py |
| BD5 | MULTI-OBJECTIVE OPTIMIZATION PROBLEMS | Energy. | `implemented_and_tested` | backend/app/active_learning/neo_planner.py; backend/app/decision/loss.py |
| BD6 | MULTI-OBJECTIVE OPTIMIZATION PROBLEMS | Probe movement. | `implemented_and_tested` | backend/app/active_learning/neo_planner.py; backend/app/decision/loss.py |
| BD7 | MULTI-OBJECTIVE OPTIMIZATION PROBLEMS | Safety risk. | `implemented_and_tested` | backend/app/active_learning/neo_planner.py; backend/app/decision/loss.py |
| BD8 | MULTI-OBJECTIVE OPTIMIZATION PROBLEMS | Hardware wear. | `implemented_and_tested` | backend/app/active_learning/neo_planner.py; backend/app/decision/loss.py |
| BD9 | MULTI-OBJECTIVE OPTIMIZATION PROBLEMS | Redundancy. | `implemented_and_tested` | backend/app/active_learning/neo_planner.py; backend/app/decision/loss.py |
| BD10 | MULTI-OBJECTIVE OPTIMIZATION PROBLEMS | Operator burden. | `partially_mitigated` | backend/app/active_learning/neo_planner.py; backend/app/decision/loss.py |
| BD11 | MULTI-OBJECTIVE OPTIMIZATION PROBLEMS | Need trade-off mechanism. | `implemented_and_tested` | backend/app/active_learning/neo_planner.py; backend/app/decision/loss.py |
| BD12 | MULTI-OBJECTIVE OPTIMIZATION PROBLEMS | Need application-specific weighting. | `implemented_and_tested` | backend/app/active_learning/neo_planner.py; backend/app/decision/loss.py |
| BD13 | MULTI-OBJECTIVE OPTIMIZATION PROBLEMS | Need Pareto analysis. | `partially_mitigated` | backend/app/active_learning/neo_planner.py; backend/app/decision/loss.py |
| BD14 | MULTI-OBJECTIVE OPTIMIZATION PROBLEMS | Need demonstrate chosen solution is not arbitrary. | `partially_mitigated` | backend/app/active_learning/neo_planner.py; backend/app/decision/loss.py |
| BE1 | COST MODEL PROBLEMS | Movement cost. | `implemented_and_tested` | backend/app/decision/loss.py; backend/app/active_learning/planner.py |
| BE2 | COST MODEL PROBLEMS | Excitation cost. | `implemented_and_tested` | backend/app/decision/loss.py; backend/app/active_learning/planner.py |
| BE3 | COST MODEL PROBLEMS | Acquisition time. | `implemented_and_tested` | backend/app/decision/loss.py; backend/app/active_learning/planner.py |
| BE4 | COST MODEL PROBLEMS | Probe repositioning time. | `implemented_and_tested` | backend/app/decision/loss.py; backend/app/active_learning/planner.py |
| BE5 | COST MODEL PROBLEMS | Sensor switching cost. | `implemented_and_tested` | backend/app/decision/loss.py; backend/app/active_learning/planner.py |
| BE6 | COST MODEL PROBLEMS | Computational cost. | `implemented_and_tested` | backend/app/decision/loss.py; backend/app/active_learning/planner.py |
| BE7 | COST MODEL PROBLEMS | Energy consumption. | `implemented_and_tested` | backend/app/decision/loss.py; backend/app/active_learning/planner.py |
| BE8 | COST MODEL PROBLEMS | Maintenance cost. | `partially_mitigated` | backend/app/decision/loss.py; backend/app/active_learning/planner.py |
| BE9 | COST MODEL PROBLEMS | Failure cost. | `partially_mitigated` | backend/app/decision/loss.py; backend/app/active_learning/planner.py |
| BE10 | COST MODEL PROBLEMS | Inspection downtime. | `partially_mitigated` | backend/app/decision/loss.py; backend/app/active_learning/planner.py |
| BE11 | COST MODEL PROBLEMS | Human labor cost. | `partially_mitigated` | backend/app/decision/loss.py; backend/app/active_learning/planner.py |
| BE12 | COST MODEL PROBLEMS | Safety cost. | `partially_mitigated` | backend/app/decision/loss.py; backend/app/active_learning/planner.py |
| BE13 | COST MODEL PROBLEMS | Need distinguish monetary cost from physical cost. | `implemented_and_tested` | backend/app/decision/loss.py; backend/app/active_learning/planner.py |
| BF1 | DATA QUALITY PROBLEMS | Duplicate samples. | `implemented_and_tested` | backend/app/services/session_manager.py; backend/app/inference/diagnostics.py |
| BF2 | DATA QUALITY PROBLEMS | Near-duplicate samples. | `partially_mitigated` | backend/app/services/session_manager.py; backend/app/inference/diagnostics.py |
| BF3 | DATA QUALITY PROBLEMS | Corrupted files. | `implemented_and_tested` | backend/app/services/session_manager.py; backend/app/inference/diagnostics.py |
| BF4 | DATA QUALITY PROBLEMS | Missing channels. | `implemented_and_tested` | backend/app/services/session_manager.py; backend/app/inference/diagnostics.py |
| BF5 | DATA QUALITY PROBLEMS | Invalid metadata. | `implemented_and_tested` | backend/app/services/session_manager.py; backend/app/inference/diagnostics.py |
| BF6 | DATA QUALITY PROBLEMS | Invalid timestamps. | `implemented_and_tested` | backend/app/services/session_manager.py; backend/app/inference/diagnostics.py |
| BF7 | DATA QUALITY PROBLEMS | Wrong coordinates. | `partially_mitigated` | backend/app/services/session_manager.py; backend/app/inference/diagnostics.py |
| BF8 | DATA QUALITY PROBLEMS | Sensor ID mismatch. | `implemented_and_tested` | backend/app/services/session_manager.py; backend/app/inference/diagnostics.py |
| BF9 | DATA QUALITY PROBLEMS | Unit mismatch. | `implemented_and_tested` | backend/app/services/session_manager.py; backend/app/inference/diagnostics.py |
| BF10 | DATA QUALITY PROBLEMS | Sampling frequency mismatch. | `implemented_and_tested` | backend/app/services/session_manager.py; backend/app/inference/diagnostics.py |
| BF11 | DATA QUALITY PROBLEMS | Signal scaling mismatch. | `implemented_and_tested` | backend/app/services/session_manager.py; backend/app/inference/diagnostics.py |
| BF12 | DATA QUALITY PROBLEMS | Different file formats. | `implemented_and_tested` | backend/app/services/session_manager.py; backend/app/inference/diagnostics.py |
| BF13 | DATA QUALITY PROBLEMS | Different experiment conventions. | `partially_mitigated` | backend/app/services/session_manager.py; backend/app/inference/diagnostics.py |
| BF14 | DATA QUALITY PROBLEMS | Annotation inconsistencies. | `partially_mitigated` | backend/app/services/session_manager.py; backend/app/inference/diagnostics.py |
| BF15 | DATA QUALITY PROBLEMS | Ground-truth inconsistency. | `partially_mitigated` | backend/app/services/session_manager.py; backend/app/inference/diagnostics.py |
| BG1 | SOFTWARE-UI PROBLEMS | Heatmap can visually imply certainty incorrectly. | `partially_mitigated` | frontend/components; frontend/app/page.tsx |
| BG2 | SOFTWARE-UI PROBLEMS | Color scale can distort interpretation. | `partially_mitigated` | frontend/components; frontend/app/page.tsx |
| BG3 | SOFTWARE-UI PROBLEMS | Confidence may be confused with accuracy. | `implemented_and_tested` | frontend/components; frontend/app/page.tsx |
| BG4 | SOFTWARE-UI PROBLEMS | Multiple defects may be hard to visualize. | `partially_mitigated` | frontend/components; frontend/app/page.tsx |
| BG5 | SOFTWARE-UI PROBLEMS | Uncertainty region needs visualization. | `implemented_and_tested` | frontend/components; frontend/app/page.tsx |
| BG6 | SOFTWARE-UI PROBLEMS | Sensor health needs visualization. | `implemented_and_tested` | frontend/components; frontend/app/page.tsx |
| BG7 | SOFTWARE-UI PROBLEMS | Measurement history needs visualization. | `implemented_and_tested` | frontend/components; frontend/app/page.tsx |
| BG8 | SOFTWARE-UI PROBLEMS | Planner reason needs visualization. | `implemented_and_tested` | frontend/components; frontend/app/page.tsx |
| BG9 | SOFTWARE-UI PROBLEMS | Raw signal should be traceable. | `implemented_and_tested` | frontend/components; frontend/app/page.tsx |
| BG10 | SOFTWARE-UI PROBLEMS | Model version should be visible. | `implemented_and_tested` | frontend/components; frontend/app/page.tsx |
| BG11 | SOFTWARE-UI PROBLEMS | Audit trail should be visible. | `implemented_and_tested` | frontend/components; frontend/app/page.tsx |
| BG12 | SOFTWARE-UI PROBLEMS | Operator should see why inspection stopped. | `implemented_and_tested` | frontend/components; frontend/app/page.tsx |
| BH1 | MLOPS PROBLEMS | Data drift monitoring. | `partially_mitigated` | backend/app/assurance/monitor.py; backend/app/models/registry.py |
| BH2 | MLOPS PROBLEMS | Model drift monitoring. | `partially_mitigated` | backend/app/assurance/monitor.py; backend/app/models/registry.py |
| BH3 | MLOPS PROBLEMS | Sensor drift monitoring. | `partially_mitigated` | backend/app/assurance/monitor.py; backend/app/models/registry.py |
| BH4 | MLOPS PROBLEMS | Environment drift monitoring. | `partially_mitigated` | backend/app/assurance/monitor.py; backend/app/models/registry.py |
| BH5 | MLOPS PROBLEMS | Performance monitoring. | `partially_mitigated` | backend/app/assurance/monitor.py; backend/app/models/registry.py |
| BH6 | MLOPS PROBLEMS | Confidence monitoring. | `partially_mitigated` | backend/app/assurance/monitor.py; backend/app/models/registry.py |
| BH7 | MLOPS PROBLEMS | OOD rate monitoring. | `partially_mitigated` | backend/app/assurance/monitor.py; backend/app/models/registry.py |
| BH8 | MLOPS PROBLEMS | Abstention rate monitoring. | `partially_mitigated` | backend/app/assurance/monitor.py; backend/app/models/registry.py |
| BH9 | MLOPS PROBLEMS | Planner behavior monitoring. | `partially_mitigated` | backend/app/assurance/monitor.py; backend/app/models/registry.py |
| BH10 | MLOPS PROBLEMS | Experiment cost monitoring. | `partially_mitigated` | backend/app/assurance/monitor.py; backend/app/models/registry.py |
| BH11 | MLOPS PROBLEMS | Failed-experiment monitoring. | `partially_mitigated` | backend/app/assurance/monitor.py; backend/app/models/registry.py |
| BH12 | MLOPS PROBLEMS | Model rollback. | `partially_mitigated` | backend/app/assurance/monitor.py; backend/app/models/registry.py |
| BH13 | MLOPS PROBLEMS | Model version control. | `partially_mitigated` | backend/app/assurance/monitor.py; backend/app/models/registry.py |
| BH14 | MLOPS PROBLEMS | Data version control. | `partially_mitigated` | backend/app/assurance/monitor.py; backend/app/models/registry.py |
| BI1 | LONG-TERM MONITORING PROBLEMS | Structural aging. | `requires_physical_validation` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| BI2 | LONG-TERM MONITORING PROBLEMS | Sensor aging. | `requires_physical_validation` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| BI3 | LONG-TERM MONITORING PROBLEMS | Adhesive aging. | `requires_physical_validation` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| BI4 | LONG-TERM MONITORING PROBLEMS | Baseline drift. | `requires_physical_validation` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| BI5 | LONG-TERM MONITORING PROBLEMS | Environmental seasonality. | `requires_physical_validation` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| BI6 | LONG-TERM MONITORING PROBLEMS | Changing operating loads. | `requires_physical_validation` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| BI7 | LONG-TERM MONITORING PROBLEMS | Damage evolution. | `requires_physical_validation` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| BI8 | LONG-TERM MONITORING PROBLEMS | Recalibration frequency. | `requires_physical_validation` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| BI9 | LONG-TERM MONITORING PROBLEMS | Model drift. | `requires_physical_validation` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| BI10 | LONG-TERM MONITORING PROBLEMS | Concept drift. | `requires_physical_validation` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| BI11 | LONG-TERM MONITORING PROBLEMS | Lifelong learning. | `requires_physical_validation` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| BI12 | LONG-TERM MONITORING PROBLEMS | Catastrophic forgetting. | `requires_physical_validation` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| BJ1 | RESEARCH-PAPER QUALITY PROBLEMS | Novelty claim must be literature-verified. | `requires_literature_or_legal_review` | paper/main.tex; docs/VERIFICATION_REPORT.md; docs/LIMITATIONS.md |
| BJ2 | RESEARCH-PAPER QUALITY PROBLEMS | All baselines must be strong. | `requires_literature_or_legal_review` | paper/main.tex; docs/VERIFICATION_REPORT.md; docs/LIMITATIONS.md |
| BJ3 | RESEARCH-PAPER QUALITY PROBLEMS | Metrics must be comprehensive. | `requires_literature_or_legal_review` | paper/main.tex; docs/VERIFICATION_REPORT.md; docs/LIMITATIONS.md |
| BJ4 | RESEARCH-PAPER QUALITY PROBLEMS | Results must include uncertainty. | `requires_literature_or_legal_review` | paper/main.tex; docs/VERIFICATION_REPORT.md; docs/LIMITATIONS.md |
| BJ5 | RESEARCH-PAPER QUALITY PROBLEMS | Results must include statistical significance. | `requires_literature_or_legal_review` | paper/main.tex; docs/VERIFICATION_REPORT.md; docs/LIMITATIONS.md |
| BJ6 | RESEARCH-PAPER QUALITY PROBLEMS | Failure cases must be reported. | `requires_literature_or_legal_review` | paper/main.tex; docs/VERIFICATION_REPORT.md; docs/LIMITATIONS.md |
| BJ7 | RESEARCH-PAPER QUALITY PROBLEMS | Negative results should be reported. | `requires_literature_or_legal_review` | paper/main.tex; docs/VERIFICATION_REPORT.md; docs/LIMITATIONS.md |
| BJ8 | RESEARCH-PAPER QUALITY PROBLEMS | Simulation and physical results must be separated. | `requires_literature_or_legal_review` | paper/main.tex; docs/VERIFICATION_REPORT.md; docs/LIMITATIONS.md |
| BJ9 | RESEARCH-PAPER QUALITY PROBLEMS | Simulation assumptions must be explicit. | `requires_literature_or_legal_review` | paper/main.tex; docs/VERIFICATION_REPORT.md; docs/LIMITATIONS.md |
| BJ10 | RESEARCH-PAPER QUALITY PROBLEMS | Real-world limitations must be explicit. | `requires_literature_or_legal_review` | paper/main.tex; docs/VERIFICATION_REPORT.md; docs/LIMITATIONS.md |
| BJ11 | RESEARCH-PAPER QUALITY PROBLEMS | Reproducibility materials should be released. | `requires_literature_or_legal_review` | paper/main.tex; docs/VERIFICATION_REPORT.md; docs/LIMITATIONS.md |
| BJ12 | RESEARCH-PAPER QUALITY PROBLEMS | Dataset processing should be documented. | `requires_literature_or_legal_review` | paper/main.tex; docs/VERIFICATION_REPORT.md; docs/LIMITATIONS.md |
| BJ13 | RESEARCH-PAPER QUALITY PROBLEMS | Hyperparameters should be documented. | `requires_literature_or_legal_review` | paper/main.tex; docs/VERIFICATION_REPORT.md; docs/LIMITATIONS.md |
| BJ14 | RESEARCH-PAPER QUALITY PROBLEMS | Hardware should be documented. | `requires_literature_or_legal_review` | paper/main.tex; docs/VERIFICATION_REPORT.md; docs/LIMITATIONS.md |
| BJ15 | RESEARCH-PAPER QUALITY PROBLEMS | Evaluation splits should be documented. | `requires_literature_or_legal_review` | paper/main.tex; docs/VERIFICATION_REPORT.md; docs/LIMITATIONS.md |
| BJ16 | RESEARCH-PAPER QUALITY PROBLEMS | Avoid inflated claims. | `requires_literature_or_legal_review` | paper/main.tex; docs/VERIFICATION_REPORT.md; docs/LIMITATIONS.md |
| BJ17 | RESEARCH-PAPER QUALITY PROBLEMS | Clearly distinguish: implemented, experimentally validated, proposed, future work. | `requires_literature_or_legal_review` | paper/main.tex; docs/VERIFICATION_REPORT.md; docs/LIMITATIONS.md |
| BK1 | RESUME / INTERVIEW PROBLEMS | "Built a CNN" is weak. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| BK2 | RESUME / INTERVIEW PROBLEMS | "Built a GNN" is insufficient. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| BK3 | RESUME / INTERVIEW PROBLEMS | "Built a dashboard" is insufficient. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| BK4 | RESUME / INTERVIEW PROBLEMS | "Used Bayesian optimization" is insufficient. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| BK5 | RESUME / INTERVIEW PROBLEMS | Need quantitative improvements. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| BK6 | RESUME / INTERVIEW PROBLEMS | Need measurable engineering constraints. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| BK7 | RESUME / INTERVIEW PROBLEMS | Need real hardware if possible. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| BK8 | RESUME / INTERVIEW PROBLEMS | Need reproducible benchmarks. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| BK9 | RESUME / INTERVIEW PROBLEMS | Need strong ablation. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| BK10 | RESUME / INTERVIEW PROBLEMS | Need system architecture knowledge. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| BK11 | RESUME / INTERVIEW PROBLEMS | Need deployment story. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| BK12 | RESUME / INTERVIEW PROBLEMS | Need failure-handling story. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| BK13 | RESUME / INTERVIEW PROBLEMS | Need explainable decision-making story. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| BK14 | RESUME / INTERVIEW PROBLEMS | Need real-world constraints. | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| BL1 | PATENT / IP PROBLEMS | Existing prior art must be searched. | `requires_literature_or_legal_review` | docs/PATENT_LANDSCAPE_AND_COMMERCIALIZATION.md; docs/PATENT_TECHNICAL_DISCLOSURE_NOTES.md |
| BL2 | PATENT / IP PROBLEMS | Bayesian experiment design has prior art. | `requires_literature_or_legal_review` | docs/PATENT_LANDSCAPE_AND_COMMERCIALIZATION.md; docs/PATENT_TECHNICAL_DISCLOSURE_NOTES.md |
| BL3 | PATENT / IP PROBLEMS | Active sensor placement has prior art. | `requires_literature_or_legal_review` | docs/PATENT_LANDSCAPE_AND_COMMERCIALIZATION.md; docs/PATENT_TECHNICAL_DISCLOSURE_NOTES.md |
| BL4 | PATENT / IP PROBLEMS | Digital-twin SHM has prior art. | `requires_literature_or_legal_review` | docs/PATENT_LANDSCAPE_AND_COMMERCIALIZATION.md; docs/PATENT_TECHNICAL_DISCLOSURE_NOTES.md |
| BL5 | PATENT / IP PROBLEMS | Physics-informed GNNs have prior art. | `requires_literature_or_legal_review` | docs/PATENT_LANDSCAPE_AND_COMMERCIALIZATION.md; docs/PATENT_TECHNICAL_DISCLOSURE_NOTES.md |
| BL6 | PATENT / IP PROBLEMS | Autonomous guided-wave SHM has prior art. | `requires_literature_or_legal_review` | docs/PATENT_LANDSCAPE_AND_COMMERCIALIZATION.md; docs/PATENT_TECHNICAL_DISCLOSURE_NOTES.md |
| BL7 | PATENT / IP PROBLEMS | Generic AI defect detection will likely not be patentable. | `requires_literature_or_legal_review` | docs/PATENT_LANDSCAPE_AND_COMMERCIALIZATION.md; docs/PATENT_TECHNICAL_DISCLOSURE_NOTES.md |
| BL8 | PATENT / IP PROBLEMS | Novel claim must involve a specific technical mechanism. | `requires_literature_or_legal_review` | docs/PATENT_LANDSCAPE_AND_COMMERCIALIZATION.md; docs/PATENT_TECHNICAL_DISCLOSURE_NOTES.md |
| BL9 | PATENT / IP PROBLEMS | Need novelty search before claiming patentability. | `requires_literature_or_legal_review` | docs/PATENT_LANDSCAPE_AND_COMMERCIALIZATION.md; docs/PATENT_TECHNICAL_DISCLOSURE_NOTES.md |
| BL10 | PATENT / IP PROBLEMS | Need define the unique system interaction, not just components. | `requires_literature_or_legal_review` | docs/PATENT_LANDSCAPE_AND_COMMERCIALIZATION.md; docs/PATENT_TECHNICAL_DISCLOSURE_NOTES.md |
| BM1 | ETHICAL / RESPONSIBLE-DEPLOYMENT PROBLEMS | False confidence. | `implemented_and_tested` | backend/app/assurance/monitor.py; backend/app/evidence/ledger.py; docs/LIMITATIONS.md |
| BM2 | ETHICAL / RESPONSIBLE-DEPLOYMENT PROBLEMS | Unsafe automation. | `implemented_and_tested` | backend/app/assurance/monitor.py; backend/app/evidence/ledger.py; docs/LIMITATIONS.md |
| BM3 | ETHICAL / RESPONSIBLE-DEPLOYMENT PROBLEMS | Inadequate human oversight. | `implemented_and_tested` | backend/app/assurance/monitor.py; backend/app/evidence/ledger.py; docs/LIMITATIONS.md |
| BM4 | ETHICAL / RESPONSIBLE-DEPLOYMENT PROBLEMS | Data provenance. | `implemented_and_tested` | backend/app/assurance/monitor.py; backend/app/evidence/ledger.py; docs/LIMITATIONS.md |
| BM5 | ETHICAL / RESPONSIBLE-DEPLOYMENT PROBLEMS | Explainability. | `implemented_and_tested` | backend/app/assurance/monitor.py; backend/app/evidence/ledger.py; docs/LIMITATIONS.md |
| BM6 | ETHICAL / RESPONSIBLE-DEPLOYMENT PROBLEMS | Traceability. | `implemented_and_tested` | backend/app/assurance/monitor.py; backend/app/evidence/ledger.py; docs/LIMITATIONS.md |
| BM7 | ETHICAL / RESPONSIBLE-DEPLOYMENT PROBLEMS | Auditability. | `implemented_and_tested` | backend/app/assurance/monitor.py; backend/app/evidence/ledger.py; docs/LIMITATIONS.md |
| BM8 | ETHICAL / RESPONSIBLE-DEPLOYMENT PROBLEMS | Safety thresholds. | `implemented_and_tested` | backend/app/assurance/monitor.py; backend/app/evidence/ledger.py; docs/LIMITATIONS.md |
| BM9 | ETHICAL / RESPONSIBLE-DEPLOYMENT PROBLEMS | Model limitations. | `implemented_and_tested` | backend/app/assurance/monitor.py; backend/app/evidence/ledger.py; docs/LIMITATIONS.md |
| BM10 | ETHICAL / RESPONSIBLE-DEPLOYMENT PROBLEMS | Unseen operating conditions. Do NOT claim: | `implemented_and_tested` | backend/app/assurance/monitor.py; backend/app/evidence/ledger.py; docs/LIMITATIONS.md |
| BN1 | FINAL "DO-NOT-CLAIM" CHECKLIST | "First AI system for guided-wave defect localization." | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| BN2 | FINAL "DO-NOT-CLAIM" CHECKLIST | "First Bayesian active sensing system." | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| BN3 | FINAL "DO-NOT-CLAIM" CHECKLIST | "First physics-informed GNN." | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| BN4 | FINAL "DO-NOT-CLAIM" CHECKLIST | "First digital-twin SHM system." | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| BN5 | FINAL "DO-NOT-CLAIM" CHECKLIST | "First autonomous guided-wave SHM system." | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| BN6 | FINAL "DO-NOT-CLAIM" CHECKLIST | "AI guarantees defect localization." | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| BN7 | FINAL "DO-NOT-CLAIM" CHECKLIST | "Confidence equals probability of correctness." | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| BN8 | FINAL "DO-NOT-CLAIM" CHECKLIST | "Simulation results prove real-world performance." | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| BN9 | FINAL "DO-NOT-CLAIM" CHECKLIST | "High accuracy means industrial readiness." | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| BN10 | FINAL "DO-NOT-CLAIM" CHECKLIST | "More neural-network complexity automatically means better science." | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| BN11 | FINAL "DO-NOT-CLAIM" CHECKLIST | "Multimodal automatically means novel." | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| BN12 | FINAL "DO-NOT-CLAIM" CHECKLIST | "GNN automatically means physics-informed." | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| BN13 | FINAL "DO-NOT-CLAIM" CHECKLIST | "A Transformer automatically provides superior performance." | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| BN14 | FINAL "DO-NOT-CLAIM" CHECKLIST | "A small benchmark proves generalization." | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| BN15 | FINAL "DO-NOT-CLAIM" CHECKLIST | "A single public dataset proves robustness." | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| BO1 | HIGHEST-PRIORITY PROBLEMS | Sim-to-real gap. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md |
| BO2 | HIGHEST-PRIORITY PROBLEMS | Simplified/incorrect physics. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md |
| BO3 | HIGHEST-PRIORITY PROBLEMS | Weak uncertainty calibration. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md |
| BO4 | HIGHEST-PRIORITY PROBLEMS | Lack of OOD / abstention. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md |
| BO5 | HIGHEST-PRIORITY PROBLEMS | Single-defect limitation. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md |
| BO6 | HIGHEST-PRIORITY PROBLEMS | Location-only output. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md |
| BO7 | HIGHEST-PRIORITY PROBLEMS | Limited dataset diversity. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md |
| BO8 | HIGHEST-PRIORITY PROBLEMS | Weak real physical validation. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md |
| BO9 | HIGHEST-PRIORITY PROBLEMS | Weak statistical power. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md |
| BO10 | HIGHEST-PRIORITY PROBLEMS | Potential train/test leakage. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md |
| BO11 | HIGHEST-PRIORITY PROBLEMS | Handcrafted planner objective. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md |
| BO12 | HIGHEST-PRIORITY PROBLEMS | Incomplete physical cost model. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md |
| BO13 | HIGHEST-PRIORITY PROBLEMS | Incomplete risk model. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md |
| BO14 | HIGHEST-PRIORITY PROBLEMS | Sensor-failure robustness. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md |
| BO15 | HIGHEST-PRIORITY PROBLEMS | Environmental robustness. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md |
| BO16 | HIGHEST-PRIORITY PROBLEMS | Cross-panel generalization. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md |
| BO17 | HIGHEST-PRIORITY PROBLEMS | Cross-material generalization. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md |
| BO18 | HIGHEST-PRIORITY PROBLEMS | Cross-hardware generalization. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md |
| BO19 | HIGHEST-PRIORITY PROBLEMS | Unknown defect handling. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md |
| BO20 | HIGHEST-PRIORITY PROBLEMS | Defect severity/size/type estimation. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md |
| BO21 | HIGHEST-PRIORITY PROBLEMS | Digital-twin calibration. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md |
| BO22 | HIGHEST-PRIORITY PROBLEMS | Surrogate uncertainty. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md |
| BO23 | HIGHEST-PRIORITY PROBLEMS | Active sensing exploration/exploitation. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md |
| BO24 | HIGHEST-PRIORITY PROBLEMS | Multi-step planning. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md |
| BO25 | HIGHEST-PRIORITY PROBLEMS | True closed-loop hardware demonstration. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md |
| BO26 | HIGHEST-PRIORITY PROBLEMS | End-to-end latency. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md |
| BO27 | HIGHEST-PRIORITY PROBLEMS | Reproducibility. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md |
| BO28 | HIGHEST-PRIORITY PROBLEMS | Strong baseline comparison. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md |
| BO29 | HIGHEST-PRIORITY PROBLEMS | Ablation study completeness. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md |
| BO30 | HIGHEST-PRIORITY PROBLEMS | Literature novelty verification. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md |
| BP1 | "KILLER RESEARCH QUESTIONS" | Can adaptive sensing reach a target defect-localization accuracy with fewer physical measurements than fixed-grid inspection? | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| BP2 | "KILLER RESEARCH QUESTIONS" | Can physics-informed learning reduce sim-to-real degradation? | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| BP3 | "KILLER RESEARCH QUESTIONS" | Can the system remain calibrated under environmental shift? | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| BP4 | "KILLER RESEARCH QUESTIONS" | Can the system reliably abstain on unknown defects? | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| BP5 | "KILLER RESEARCH QUESTIONS" | Can the system detect and compensate for sensor faults? | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| BP6 | "KILLER RESEARCH QUESTIONS" | Can the system localize multiple defects? | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| BP7 | "KILLER RESEARCH QUESTIONS" | Can the system estimate defect size and severity? | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| BP8 | "KILLER RESEARCH QUESTIONS" | Can the planner optimize information, risk and physical cost jointly? | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| BP9 | "KILLER RESEARCH QUESTIONS" | Can a learned planner outperform a handcrafted Bayesian planner? | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| BP10 | "KILLER RESEARCH QUESTIONS" | Can a fast learned surrogate replace expensive forward simulation without changing experiment-selection decisions? | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| BP11 | "KILLER RESEARCH QUESTIONS" | Can real-world performance improve using few-shot / unlabeled adaptation? | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| BP12 | "KILLER RESEARCH QUESTIONS" | Can the system preserve reliability under unseen structures? | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| BP13 | "KILLER RESEARCH QUESTIONS" | Can the entire inspection loop operate autonomously on real hardware? | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| BP14 | "KILLER RESEARCH QUESTIONS" | Can the system provide calibrated uncertainty rather than heuristic confidence? | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| BP15 | "KILLER RESEARCH QUESTIONS" | Can the system determine when it should NOT make a prediction? | `acknowledged_and_bounded` | docs/ARGUS_X_DISPOSITION.md; docs/LIMITATIONS.md |
| BQ1 | THE FINAL SYSTEM REQUIREMENTS WE SHOULD AIM FOR | Detect healthy vs damaged. | `implemented_and_tested` | docs/ARGUS_X_DISPOSITION.md; backend/app; frontend/components |
| BQ2 | THE FINAL SYSTEM REQUIREMENTS WE SHOULD AIM FOR | Localize damage. | `implemented_and_tested` | docs/ARGUS_X_DISPOSITION.md; backend/app; frontend/components |
| BQ3 | THE FINAL SYSTEM REQUIREMENTS WE SHOULD AIM FOR | Detect multiple defects. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md; backend/app; frontend/components |
| BQ4 | THE FINAL SYSTEM REQUIREMENTS WE SHOULD AIM FOR | Classify defect type. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md; backend/app; frontend/components |
| BQ5 | THE FINAL SYSTEM REQUIREMENTS WE SHOULD AIM FOR | Estimate defect size. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md; backend/app; frontend/components |
| BQ6 | THE FINAL SYSTEM REQUIREMENTS WE SHOULD AIM FOR | Estimate defect severity. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md; backend/app; frontend/components |
| BQ7 | THE FINAL SYSTEM REQUIREMENTS WE SHOULD AIM FOR | Produce calibrated uncertainty. | `implemented_and_tested` | docs/ARGUS_X_DISPOSITION.md; backend/app; frontend/components |
| BQ8 | THE FINAL SYSTEM REQUIREMENTS WE SHOULD AIM FOR | Detect OOD cases. | `implemented_and_tested` | docs/ARGUS_X_DISPOSITION.md; backend/app; frontend/components |
| BQ9 | THE FINAL SYSTEM REQUIREMENTS WE SHOULD AIM FOR | Abstain when uncertain. | `implemented_and_tested` | docs/ARGUS_X_DISPOSITION.md; backend/app; frontend/components |
| BQ10 | THE FINAL SYSTEM REQUIREMENTS WE SHOULD AIM FOR | Detect sensor faults. | `implemented_and_tested` | docs/ARGUS_X_DISPOSITION.md; backend/app; frontend/components |
| BQ11 | THE FINAL SYSTEM REQUIREMENTS WE SHOULD AIM FOR | Estimate sensor reliability. | `implemented_and_tested` | docs/ARGUS_X_DISPOSITION.md; backend/app; frontend/components |
| BQ12 | THE FINAL SYSTEM REQUIREMENTS WE SHOULD AIM FOR | Adapt to environmental conditions. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md; backend/app; frontend/components |
| BQ13 | THE FINAL SYSTEM REQUIREMENTS WE SHOULD AIM FOR | Adapt from simulation to reality. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md; backend/app; frontend/components |
| BQ14 | THE FINAL SYSTEM REQUIREMENTS WE SHOULD AIM FOR | Adapt between structures. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md; backend/app; frontend/components |
| BQ15 | THE FINAL SYSTEM REQUIREMENTS WE SHOULD AIM FOR | Choose the next experiment. | `implemented_and_tested` | docs/ARGUS_X_DISPOSITION.md; backend/app; frontend/components |
| BQ16 | THE FINAL SYSTEM REQUIREMENTS WE SHOULD AIM FOR | Choose experiment geometry. | `implemented_and_tested` | docs/ARGUS_X_DISPOSITION.md; backend/app; frontend/components |
| BQ17 | THE FINAL SYSTEM REQUIREMENTS WE SHOULD AIM FOR | Choose frequency. | `implemented_and_tested` | docs/ARGUS_X_DISPOSITION.md; backend/app; frontend/components |
| BQ18 | THE FINAL SYSTEM REQUIREMENTS WE SHOULD AIM FOR | Choose waveform. | `implemented_and_tested` | docs/ARGUS_X_DISPOSITION.md; backend/app; frontend/components |
| BQ19 | THE FINAL SYSTEM REQUIREMENTS WE SHOULD AIM FOR | Choose sensing modality where applicable. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md; backend/app; frontend/components |
| BQ20 | THE FINAL SYSTEM REQUIREMENTS WE SHOULD AIM FOR | Account for physical cost. | `implemented_and_tested` | docs/ARGUS_X_DISPOSITION.md; backend/app; frontend/components |
| BQ21 | THE FINAL SYSTEM REQUIREMENTS WE SHOULD AIM FOR | Account for safety risk. | `implemented_and_tested` | docs/ARGUS_X_DISPOSITION.md; backend/app; frontend/components |
| BQ22 | THE FINAL SYSTEM REQUIREMENTS WE SHOULD AIM FOR | Avoid redundant experiments. | `implemented_and_tested` | docs/ARGUS_X_DISPOSITION.md; backend/app; frontend/components |
| BQ23 | THE FINAL SYSTEM REQUIREMENTS WE SHOULD AIM FOR | Stop when evidence is sufficient. | `implemented_and_tested` | docs/ARGUS_X_DISPOSITION.md; backend/app; frontend/components |
| BQ24 | THE FINAL SYSTEM REQUIREMENTS WE SHOULD AIM FOR | Explain why the next measurement was chosen. | `implemented_and_tested` | docs/ARGUS_X_DISPOSITION.md; backend/app; frontend/components |
| BQ25 | THE FINAL SYSTEM REQUIREMENTS WE SHOULD AIM FOR | Explain why the system stopped. | `implemented_and_tested` | docs/ARGUS_X_DISPOSITION.md; backend/app; frontend/components |
| BQ26 | THE FINAL SYSTEM REQUIREMENTS WE SHOULD AIM FOR | Explain why it abstained. | `implemented_and_tested` | docs/ARGUS_X_DISPOSITION.md; backend/app; frontend/components |
| BQ27 | THE FINAL SYSTEM REQUIREMENTS WE SHOULD AIM FOR | Operate under sensor failure. | `implemented_and_tested` | docs/ARGUS_X_DISPOSITION.md; backend/app; frontend/components |
| BQ28 | THE FINAL SYSTEM REQUIREMENTS WE SHOULD AIM FOR | Operate with realistic environmental variation. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md; backend/app; frontend/components |
| BQ29 | THE FINAL SYSTEM REQUIREMENTS WE SHOULD AIM FOR | Work with a real physical prototype. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md; backend/app; frontend/components |
| BQ30 | THE FINAL SYSTEM REQUIREMENTS WE SHOULD AIM FOR | Provide a complete audit trail. | `implemented_and_tested` | docs/ARGUS_X_DISPOSITION.md; backend/app; frontend/components |
| BQ31 | THE FINAL SYSTEM REQUIREMENTS WE SHOULD AIM FOR | Provide real-time inference. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md; backend/app; frontend/components |
| BQ32 | THE FINAL SYSTEM REQUIREMENTS WE SHOULD AIM FOR | Provide reproducible benchmarks. | `implemented_and_tested` | docs/ARGUS_X_DISPOSITION.md; backend/app; frontend/components |
| BQ33 | THE FINAL SYSTEM REQUIREMENTS WE SHOULD AIM FOR | Provide statistical uncertainty in results. | `implemented_and_tested` | docs/ARGUS_X_DISPOSITION.md; backend/app; frontend/components |
| BQ34 | THE FINAL SYSTEM REQUIREMENTS WE SHOULD AIM FOR | Demonstrate cross-domain generalization. | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md; backend/app; frontend/components |
| BQ35 | THE FINAL SYSTEM REQUIREMENTS WE SHOULD AIM FOR | Demonstrate blind physical validation. END OF MASTER INVENTORY | `partially_mitigated` | docs/ARGUS_X_DISPOSITION.md; backend/app; frontend/components |
