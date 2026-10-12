# ARGUS audit remediation — 20 September 2026

This is an implementation and evidence record. It does not assert that every
weakness is eliminated, that ARGUS is field validated, or that a patent will be
granted. The unresolved rows below are release and claim limitations.

## Implemented corrections

| Audit finding | Change | Evidence / remaining boundary |
|---|---|---|
| One delay was used to independently shrink velocity and timing uncertainty | Joint first-order Gaussian update with a retained velocity/timing covariance; Joseph covariance update; serialization | Rank-one information and multiple-distance identifiability tests. Still a local Gaussian approximation. |
| Calibration geometries had equal path lengths | Three distinct direct-path lengths | Repeated-path versus varied-path synthetic parameter-identification test. |
| Waveform quality was treated as absolute pose or separate TX/RX coupling evidence | Pose calibration requires external measured errors and uncertainty; quality alone no longer shrinks both coupling variables | Missing-pose and coupling-uncertainty regression tests. Actual force/pose sensors remain absent. |
| Calibration was allowed to increase whole-model trust by a fixed amount | Removed the repeated trust bonus; valid reference only permits cautious recovery; support scope recorded as propagation-reference-only | A reference does not validate the scattered-wave model. Remaining trust scores are explicitly heuristic. |
| OOD was checked after posterior fusion | Assess against the pre-observation belief, block structural fusion on OOD/abstain, temper caution | Forced-OOD test proves an outlier cannot move the posterior before being blocked. |
| Rejected or stale verification labels counted toward stopping | Require the latest accepted, distinct measurement to remain consistent with the previous modeled R90 region, with nominal OOD status | Rejected-verification, stale-label and persistence tests. This is a consistency test, not calibrated field coverage. |
| Calibration residuals contaminated the conformal reference pool | Direct-path calibration no longer registers its fitted residual as defect-scatter reference evidence | The two residual populations are not presumed exchangeable. No conformal coverage certificate is claimed. |
| Calibration-versus-diagnosis used unrelated proxy scores | Added optional finite-horizon Bayes risk planner comparing both in m² plus declared acquisition cost | Actual observation branches with shared propagation covariance. Experimental; accuracy superiority not established. |
| Claimed lookahead had no measurement branches | New risk planner branches on first observations and optimizes the second action; includes stopping after the first | Existing fast route scorer is explicitly labelled a geometric proxy. New horizon is at most two. |
| “Risk” and “confidence” could be read as calibrated failure probabilities | Added method/unit metadata; experimental UI displays mm²; legacy UI identifies proxy scores | No maintenance decision loss or field probability calibration is available. |
| Calibration study compared a heuristic score with an unrelated 20 mm success event | Reliability now compares posterior mass within 20 mm with the matching physical event | This fixes the definition; it does not calibrate the model by itself. |
| Forward cache could reuse stale predictions after covariance/material changes | Cache key includes correlation, material and panel | Forward variances include the velocity/timing cross term. |
| Local ledger verification checked only internal hashes | Now verifies raw/processed/posterior/likelihood content and experiment identity; optional independently retained head/count checkpoint | Tests show a recomputed full history passes local consistency but fails the original trusted checkpoint. No signature or trusted timestamp. |
| Stereo integer WAVs lost normalization, unsigned PCM was not centered | Convert integer channels before averaging; center unsigned PCM; reject nonfinite and duplicate bank actions | Stereo and unsigned regression tests. |
| Replay ignored recording sample rates | Resample each recorded action using its recorded rate | Does not invent synchronization or hardware calibration. |
| Replay risk planner could select nonexistent calibration evidence | Only explicitly labelled, available direct-path reference recordings enter replay calibration candidates | Missing action outcomes are never simulated for physical replay. |
| Replanning could lose a successfully acquired result when no next action existed | Persist acquisition and enter explicit abstention if constrained next-action planning fails | Preserves evidence and suppresses automatic recovery from a blocked planner. |
| Profile defaults prevented explicit overrides | Merge profile settings and overrides once | Configuration regression test. |
| Website could call another application's API and show it as online | Check `service=argus`; configurable API port; launcher propagates the port | This workspace has WitnessNet-X on 8000 and ARGUS on 8001. Other project left running. |
| Physical collection was not reproducibly specified | Added `scripts/physical_campaign.py plan` and `audit` | Plan contains no recordings or invented ground truth. Audit detects missing metadata, split leakage, duplicate samples and unequal action coverage. |
| Broad/current/historical claims were mixed | Added current support matrix and mathematical disclosure; marked broad patent draft historical | Human inventorship, filing dates and prior-art assessment remain external decisions. |

## Scientific evaluation

`research_results/audit_risk_pilot.json` is a development pilot. Its source-change
flag must be checked before reuse; it is not the final validation artifact.

`research_results/audit_risk_validation.json` uses separate seeds 53000–53005,
six measurements, twelve shared diagnostic candidate opportunities per step,
nominal and mismatched/noisy acquisition, and the legacy and optional risk
policies. Acquisition and inference physics remain separate. Truth is used for
scoring, not action selection. The report retains failed runs, physical errors,
R90 coverage and paired bootstrap intervals. Fixed budget does not establish
measurement compression. Six seeds per condition are an engineering check,
not a powered efficacy study.

All 24 runs completed, with `source_changed_during_run=false`:

| Condition (6 paired seeds) | Legacy mean error | Experimental risk mean error | Mean advantage of risk, paired bootstrap 95% interval |
|---|---:|---:|---:|
| Nominal | 43.90 mm | 12.58 mm | 31.32 mm [-2.71, 93.38] |
| Mismatch + noise | 150.22 mm | 203.78 mm | -53.56 mm [-174.99, 17.82] |

Both intervals cross zero. Nominal success within 20 mm is 5/6 for both policies;
under mismatch it is 0/6 for both. The risk policy used about 21 seconds of
computation per six-measurement case, versus 0.35-0.39 seconds for the legacy
policy on this machine. The nominal mean improvement is strongly influenced by
one legacy outlier. No overall superiority, acceptable field accuracy, or
calibration benefit has been established. These negative/inconclusive outcomes
are retained rather than removed or presented as successful physical tests.

The new policy remains off by default. Numerical correctness and a more explicit
loss function do not imply better localization. The present waveform update is
still a generalized matched-filter likelihood, while planning uses a coarsened
arrival model; that mismatch is an open scientific limitation.

## Software verification

- Full backend suite: 107 tests passed; upstream Starlette/httpx deprecation
  warning remains, with no test failures.
- Frontend: 24 tests passed; lint, TypeScript check and production build passed.
- Live HTTP checks: `/`, `/setup`, `/simulator`, `/research`, `/probe` returned 200.
- Live API: ARGUS service identity, experimental session creation, acquisition,
  reduced remaining planning horizon, checkpoint export and anchored verification
  passed on port 8001.
- In-app browser automation was unavailable (no browser instance), so no claim of
  completed interactive visual UI testing is made.
- The physical acquisition plan contains no recordings and cannot pass the
  measured-campaign audit until actual acquisition and metadata exist.
- IEEE manuscript: 17-page PDF rebuilt with pdfLaTeX/BibTeX, with no undefined
  references or overfull text boxes; all pages rendered and visually inspected.
  Updated source archive: `paper/argus-ieee-overleaf.zip`; PDF copy:
  `output/pdf/argus-audit-manuscript.pdf`. MiKTeX's update-check notice is an
  environment maintenance notice, not a compilation failure.

## Open restrictions and required closure evidence

| Restriction | Why code alone cannot close it | Required next evidence |
|---|---|---|
| Prior public disclosure | A local code change cannot reverse a public disclosure | Dated filing/disclosure timeline and jurisdiction review by patent counsel; preserve repository history. |
| Novelty/inventive step | Bayesian design, Gaussian conditioning, dual control, NDE and hash chains are established | Professional claim chart and non-patent literature search for the specific physical sequence. |
| Human inventorship/ownership | Software cannot decide or fabricate who conceived each claim | Human conception records; university, collaborator and competition agreements. |
| General guided-wave physics | Effective isotropic velocity cannot represent all dispersion, anisotropy, boundaries and contact physics | Calibrated target material, transfer functions and measured wavefields; integrate a validated solver where needed. |
| Multiple defects, type, depth and severity | Current spatial state assumes one dominant scatterer; several displayed attributes remain priors/proxies | A supported multi-defect likelihood and blind physical labels, or exclude these claims. |
| Fully coupled structural/metrology inference | Current runtime stores structural and nuisance blocks separately, with a velocity/timing covariance | Persistent hierarchical posterior and identifiability validation before claiming a general joint posterior. |
| All-fidelity runtime integration | Only analytical and physics-signature levels are wired in the live legacy planner | Matched-feature, uncertainty-calibrated response-bank/surrogate adapters and blind evidence before enabling levels 2/3. |
| Waveform optimality | Finite families/codes are enumerated; hardware transfer functions are unknown | Measured transducer response and constrained optimization experiment; otherwise say candidate selection. |
| Field OOD thresholds / credible-region coverage | No target-domain calibration cohort exists | Frozen calibration split, independent test specimens, coverage and false-confidence analysis. |
| Physical apparatus | Firmware and phone mode cannot supply calibrated, synchronized ultrasonic measurements | Build and measure trigger/clock, analog front end, output limits, contact and pose; document device-specific limits. |
| Broad modalities / robotics | These are proposed embodiments, not implemented systems | Build enabling embodiments or exclude from current independent claims. |
| Evidence authenticity | A retained checksum is not a signature, secure device or trusted clock | Institutional independent checkpoint retention; add signing/time authority if that threat model is required. |
| Commercial superiority | Synthetic effects and visual polish do not establish industrial performance | Blind comparisons against relevant reference inspection, probability of detection and operational cost. |

## How to use the corrected work

- Open the local instrument at `http://localhost:5173`.
- The API in this workspace is `http://127.0.0.1:8001`.
- On a new session, select **Calibration-aware risk planning** to use the optional
  two-measurement controller. Inspect physical loss and numerical ambiguity in
  **Reasoning**. It overrides the older information planner when both are checked.
- In **Evidence**, save a checkpoint and retain it independently. The verification
  API accepts both `trusted_head_hash` and `trusted_record_count`.
- Generate a new physical acquisition plan with:

```powershell
python scripts/physical_campaign.py plan --output output/my_acquisition_plan.json
python scripts/physical_campaign.py audit path/to/recorded_manifest.json --output output/my_campaign_audit.json
```

An acquisition plan is provided at `output/audit_physical_acquisition_plan.json`.
The audit intentionally rejects it until actual recordings and measured metadata
exist. Two laptops and a phone can produce an audio-band timing/impact prototype;
those observations must not be relabelled as validated persistent-defect NDE.

## Legal/source boundaries

The current supported technical scope is in `CURRENT_INVENTION_DISCLOSURE.md`.
The historical broad claims are retained for provenance, not represented as
filing-ready. A provisional application also needs adequate technical disclosure;
unsupported later features do not automatically receive its priority date.

- [USPTO provisional application guidance](https://www.uspto.gov/patents/basics/apply/provisional-application)
- [Indian Patents Act, Section 10](https://ipindia.gov.in/acts/patent-act-1970/section-10)
- [EPO simulation/design/modelling guidance](https://www.epo.org/en/legal/guidelines-epc/2026/g_ii_3_3_2.html)

No patent filing, repository publication, licence change or external deployment
is performed as part of this local audit remediation.
