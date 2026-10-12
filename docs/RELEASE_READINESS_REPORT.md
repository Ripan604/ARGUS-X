# ARGUS security, scientific integrity and release report

**Source boundary:** this report records the pre-v2 audit. Later changed-source
verification and acquisition evidence are in PROBE_V2_RELEASE_REVIEW.md; the
original saved results and their source hashes remain intact.

**Date:** 7 October 2026. **Scope:** current local working tree, including edits
that existed before this audit. Existing source history and September evidence
were preserved. No external publication, patent filing, deployment or grade
assessment is represented as completed.

The project is now a more defensible local research prototype with tested security
and evidence controls, an updated manuscript and a practitioner-facing technical
disclosure. It is not a field-validated NDE product or a demonstrated patentable
invention. Some important scientific failures remain visible in the fresh study.

## Executed checks

| Check | Actual result | Evidence |
|---|---|---|
| Backend full suite in patched virtual environment | 294 passed, 1 skipped; no failures | output/release/backend-tests.xml |
| Historical binary-model test | Skipped because legacy pickle deserialization is refused; safe-format prediction round trip passes | test_surrogate.py; test_safe_checkpoints.py |
| Frontend | 26 tests passed; typecheck, lint and production build passed | Local commands and output/release/frontend-checks.json |
| Readiness | All imports, SQLite and one closed-loop measurement pass with PyTorch 2.6.0+cpu | scripts/doctor.py |
| Deterministic demo | Eight actions; approximately 10.0 mm MAP error; entropy 0.473; STOP_BUDGET | easy, seed17, eight observations |
| Fresh paired synthetic study | 48/48 runs complete, source unchanged and rechecked against current backend | release_validation_2026_10_07.json |
| Release source/evidence bundle | Allowlisted members, hashes and declared evidence checked by builder/verifier | scripts/build_release_bundle.py |

The one upstream Starlette/httpx test-client deprecation warning is retained;
it is not a test failure. The main application source, regression tests and CLI
workflows were verified locally; no full interactive browser or physical-device
campaign was performed. Production build passes with Vinext's informational
route-classification notice. A test or build is not proof that no vulnerability
exists outside its declared cases.

## Remediated security and control issues

Severity below is this audit's local threat assessment, not an invented CVSS score.

| Finding | Risk | Implemented correction | Regression evidence |
|---|---|---|---|
| Anonymous LAN controls by default | High: session, jobs and physical controls exposed | Loopback default; explicit LAN mode, strong key, exact origins/hosts, HTTP/WS authentication | test_network_security.py |
| Hostile browser/socket origins and DNS-rebinding access | High: unauthorized local/LAN operation | Host, peer and exact-origin checks before routing/parsing | test_network_security.py |
| Hardware acquisition ran before latch/constraints | High: unsafe action could execute then be rejected | Validate stop, source geometry/no-go and drive before device.acquire; per-device serialization | Acquisition-spy security tests |
| HTTP/WS and job resource exhaustion | High: memory/CPU service denial | Byte/deadline/rate/concurrency/frame limits; bounded config and metadata; no automatic missing benchmark computation | Network/input/artifact tests |
| Unsafe pickle checkpoint readers; vulnerable PyTorch | High when an untrusted model is loaded | Remove torch.load readers; bounded ZIP/NPY/JSON format; patched project-local Torch2.6 | Safe checkpoint tests; publisher advisory |
| Next.js dependency behind publisher security release | Potential affected-framework exposure | Next.js16.3.8 and updated lockfile; scripts/audit disabled during patch fetch | Frontend checks and build |
| Malicious ZIP/NPY/JSON/zlib artifacts | High: allocations/ambiguous state before validation | Preflight paths, headers, sizes, dtype, duplicates, expansion and stored decompression; strict JSON | test_artifact_security.py |
| Imported state did not bind enough content | Medium: inconsistent posterior/model/verification state | Validate complete transition chain and online buffers; schema2 planner/diagnostic hashes | Artifact and evidence tests |
| Commit-only evidence misidentified edited code | Medium: wrong reproducibility identity | Fingerprint actual tracked/untracked source bytes; retain independent head/count checkpoint option | Dirty-source and tampering tests |
| Edge key forwarded across redirects | High: operator credential disclosure | Redirect refusal and server-address validation | test_launcher_edge_security.py |
| Edge captured only its first recommendation | Medium: incomplete adaptive acquisition | Track the pre-capture count; register once per connection | Two-consecutive-capture regression |
| UI suppressed emergency stop while busy | High control defect | Independent stop dispatch, enabled stop button and preservation of acknowledged latch | Hook/panel review; backend stop regressions |
| Launcher could leave Node children and exposed key to frontend | Medium: orphan listener/secret exposure | Windows owned-process-tree termination; separate frontend environment | Launcher regression tests |

## Remediated scientific/evidence issues

| Finding | Why it threatened interpretation | Correction |
|---|---|---|
| Sensor reliability evaluated after fusion | A faulty channel could influence the grid or calibration first | Gate reliability before structural/nuisance/discrepancy/screening updates |
| Short/2D/invalid signals silently changed observation | Missing or mixed evidence retained the original experiment label | Exact mono/window checks before engine mutation; reject missing data |
| Resampling hid original Nyquist failure | Interpolation cannot recover aliased measurement content | Require original-rate support for declared excitation band |
| Sensor name could suppress measured-reference OOD | Client labels changed whether physical evidence was checked | Server-owned physical-acquisition provenance |
| Raw physical unit labels used normalized-model thresholds | Unit names are not a transfer calibration | Explicit affine conversion and recorded reference; declaration remains unvalidated |
| Rejected measurements became repeat references on restart | Persistence could reintroduce poisoned consistency evidence | Restore only accepted, reliable, structurally supported or calibrated references |
| Probability overflow, negative/zero support, rounded persistence | Invalid support or tiny mass could silently change belief | Stable normalization/log update, support validation and full-precision state |
| Calibration used missing/unsupported diagnostics | Uncertainty could shrink without the required observation | Require valid measured diagnostics and support; no partial invalid update |
| Amplitude/duration/reciprocal changes counted as verification | No new structural path constraint | Meaningful geometry or excitation diversity required |
| Fixed severity prior influenced spatial uncertainty | Unlearned attributes changed a decision score | Location uncertainty uses learned spatial quantities; attributes labelled unchanged priors |
| Particle helper ignored speed/timing covariance | Inconsistent prediction sampling | Correlated sampling helper; explicitly not deployed hierarchical inference |
| Gain variance missing from predictive log gain | Mean depended on an uncertain quantity omitted from variance | Include its first-order variance contribution |
| Heuristic existence/count weights implied healthy disposition | Single-defect prior does not infer defect absence | Label heuristics and disable unsupported healthy release |

All fixes have a bounded supported claim. Statistical quality/OOD/verification
tests do not guarantee detection of all mismatch or measured confidence coverage.

## Fresh current-source results

Eight held-out engineering seeds per condition/policy, six observations, twelve
shared diagnostic opportunities, and three policies produced 48 completed runs.
Every run and failure is retained. The protocol was recorded before execution;
source fingerprints were unchanged and rechecked afterward.

| Condition | Legacy mean error | Nuisance-aware mean error | Risk-controller mean error |
|---|---|---|---|
| Nominal | 16.04 mm | 14.30 mm | 13.35 mm |
| Mismatch plus noise | 189.95 mm | 144.36 mm | 143.71 mm |

Paired nuisance-aware advantages over legacy: 1.74 mm, 95% interval
[-6.78,9.50] nominally; 45.59 mm, [-22.85,107.10] under mismatch. Paired risk
advantages: 2.69 mm, [-0.78,7.59] and 46.24 mm, [-10.48,112.27]. All intervals
cross zero. All policies succeed within 20 mm in 6/8 nominal cases. Under mismatch,
legacy succeeds in 0/8 and each optional policy in 1/8. Large stressed errors and
missed mismatch remain material failures. The optional policies stay off by default.

Timing is descriptive on a shared workstation: about 0.33-0.37 seconds per
six-observation legacy case, 0.45-0.50 for nuisance-aware, and 20.84-20.87 for risk.
This is not a dedicated real-time benchmark. Fixed budget cannot establish
measurement compression. Software-control improvements are demonstrated by
specific invariants, not by an unsupported claim of field accuracy.

## Publication/IP deliverables

- Updated IEEE working manuscript: paper/main.tex and the generated October table.
- Technical disclosure and preliminary adjacent-art worksheet:
  docs/PATENT_REVIEW_PACKAGE.md and CURRENT_INVENTION_DISCLOSURE.md.
- Frozen protocol and raw per-run report: VALIDATION_PROTOCOL_2026_10_07.md and
  research_results/release_validation_2026_10_07.json.
- Local source/evidence ZIP with separate manifest, excluding private environment,
  credentials, raw data and binary models.
- Detailed readable audit/disclosure PDF and a rebuilt manuscript PDF.

No novelty, filing status, editorial acceptance or course outcome is inferred from
these artifacts. Existing manuscript authorship was preserved; human inventorship
and university ownership need real records. The closest literature/patents still
require a professional claim/family search. A physical-control method must have
an enabling apparatus description and evidence at the scope actually claimed.

## Remaining release/claim limitations

1. No blind physical adaptive hidden-defect study; stress accuracy is not acceptable
   as a deployment claim. Real coupling, triggers/clocks, dispersion, boundaries
   and transfer functions remain uncharacterized for the intended apparatus.
2. One dominant location grid; existence, number, type, depth, radius and severity
   are not validated joint inverse outputs.
3. Different planning and waveform likelihoods; configured costs/trust/confidence
   are proxies/preferences rather than measured maintenance loss or field probabilities.
4. Shared operator key, cleartext trusted-LAN mode and per-process limits;
   multi-user/public deployment requires additional authentication/TLS architecture.
5. An emergency latch prevents future acquisition but cannot interrupt an in-flight
   hardware action. A physical interlock must be built and measured.
6. Hashes and imported manifests prove consistency only; no independent sensor
   authenticity, signed timestamp or human contribution is established.
7. Online npm audit remains pending explicit approval. Automatic approval review
   rejected sending dependency metadata to registry.npmjs.org. Public advisory
   checks and targeted patches do not constitute a complete transitive audit.

The strongest next milestone is the specimen/defect-held-out physical protocol in
VALIDATION_PROTOCOL_2026_10_07.md. Reviewers should receive the genuine failure
cases and this claim boundary alongside the functioning demo and software evidence.
