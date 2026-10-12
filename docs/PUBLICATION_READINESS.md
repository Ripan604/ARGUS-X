# ARGUS publication and academic-review readiness

**Source boundary:** this is the pre-v2 audit assessment. The subsequent concurrent
probe implementation, time-origin gate and stronger study are reported in
PROBE_V2_RELEASE_REVIEW.md and PATENT_STRENGTHENING_ASSESSMENT.md.

Prepared 7 October 2026. The local package supports a transparent prototype/method
review; it does not establish a publication acceptance, patent grant or course grade.

The later final-review extension is documented separately in
ARGUS_FINAL_TECHNICAL_DISCLOSURE.md. Its scalar-reference study does not replace
the earlier 48-run defect-localization results or establish physical performance.

## Contribution stated at the supported scope

ARGUS is an inspectable single-scatterer acoustic interrogation prototype combining
conditional spatial inference, uncertain propagation calibration, finite candidate
selection, acquisition-validity/OOD gating and verification-supported termination.
An optional two-observation regional arrival-risk controller compares diagnosis and
direct-reference calibration in common squared-position units. The hardened system
records actual source identity and content-bound evidence.

Do not describe the contribution as a new Bayesian update, globally optimal design,
fully joint learned inference, physical depth/type/size reconstruction, a certified
instrument, or a proven accuracy upgrade. The false-certainty and input-integrity
controls are concrete engineering results, but efficacy remains an empirical question.

## Manuscript corrections

The IEEE-format working manuscript in paper/main.tex now distinguishes:

- Separate structural and metrology state from an exact joint posterior or deployed
  particle inference.
- The executed quality/channel/OOD evidence exponent from a conceptual trust/temperature
  formula that is not used by the runtime.
- Fresh qualifying verification from threshold-only stopping.
- KL-derived separation proxies from actual Jensen-Shannon divergence.
- Finite waveform candidates and live forward levels 0/1 from proposed all-fidelity
  continuous optimization.
- Fast geometric route reranking from actual optional observation branching <=2.
- Unchanged attribute priors and heuristic damage-existence weights from learned
  defect existence/type/depth/severity.
- September synthetic results from the source-fingerprinted October release run.

Numerical tables preserve adverse and inconclusive results; none is relabelled as
physical evidence. Final test counts and limitations are in RELEASE_READINESS_REPORT.

## Review 1 evidence map

| Review topic | Concrete artifact | Honest next milestone |
|---|---|---|
| Problem and objective | README, current architecture and study guide | Define target specimen/apparatus and tolerances |
| Physics and method | Simulation, likelihood, covariance calibration, risk planner | Independently measure propagation/model error |
| Technical implementation | API/UI/device contracts and reproducible launcher | Assemble and characterize actual acquisition |
| Software correctness/security | Regression suite and JUnit report | External audit under a declared deployment threat model |
| Experimental evidence | Historical studies plus frozen October protocol/results | Blind physical study with matched budgets |
| Differentiation/IP | Technical disclosure and preliminary adjacent-art worksheet | Practitioner claim chart and human contribution record |

## Submission decisions still outstanding

Identify the venue and paper category; check its template, scope, authorship,
AI-assistance disclosure and reproducibility/data requirements. Complete genuine
author affiliations and contributions without inventing coauthors or experimental
work. Obtain institutional approvals where applicable. A prototype/method paper
can report limitations and failed stress cases, but acceptance is an editorial
decision. No public upload, journal submission or patent filing was made.

## Reproduce and inspect the local package

```powershell
.venv\Scripts\python.exe -m pytest backend\tests -q -o addopts="" --junitxml=output/release/backend-tests.xml
cd frontend
npm.cmd test
npm.cmd run typecheck
npm.cmd run lint
npm.cmd run build
```

From the project root, run the frozen validation command in
VALIDATION_PROTOCOL_2026_10_07.md. Build and verify the local source/evidence ZIP
using scripts/build_release_bundle.py. The manifest excludes private environment
files, credentials, raw external data and binary models. Hashes show which files
were reviewed; they are not signatures or proof of scientific correctness.
