# Research and spatial interface release - 2026-09-16

## Completed

- Unified spatial interface and live probability relief, physical panel aspect,
  physical R90 contours, global motion pause and reduced-motion support.
- Opt-in nuisance-aware regional-information planner, explicit numerical and
  uncertainty diagnostics, persistent API configuration and default-off rollout.
- Reserved-seed paired evaluation: 80 completed synthetic runs, eight acquisitions
  each, fixed shared candidate banks, nominal and mismatched acquisition contexts.
- Recorded results in the UI, generated from the raw artifact with a verified
  SHA-256 source fingerprint rather than manually transcribed performance claims.
- Research method and evaluation documentation, updated 16-page IEEE manuscript,
  and a self-contained Overleaf source ZIP.

## Verification performed

- Full backend test suite passed during implementation. Final targeted rerun:
  22 tests passed across nuisance design, research validation and published report.
- Frontend: 22 tests passed; TypeScript, ESLint and production build passed.
- Root `git diff --check` passed (Windows line-ending conversion notices only).
- A live research-enabled session completed five acquisitions and its five-record
  evidence ledger validated. The backend health endpoint returned `ok`.
- Local landing, setup, simulator, probe and research routes returned HTTP 200.
- The manuscript compiled without undefined references or overfull-box warnings.
  Rendered pages and the separate social illustration were visually inspected.
- An independent read-only scientific review found no high/medium correctness
  issue in the added method, evaluation or reported conclusions.

The available browser connection exposed no browser, so interactive visual,
mobile-device and cross-browser QA could not be performed. Automated checks are
not a claim of zero possible defects. An upstream Starlette/httpx deprecation
warning remains; it did not fail the tests.

## Scientific and hosting boundaries

The new planner is experimental and disabled by default. Both paired mean-error
confidence intervals include zero, so the reserved synthetic evaluation does not
establish a reliable accuracy improvement. The stress condition exposes large
errors in both methods. No new physical training campaign, field calibration,
certification, patentability finding or market-leadership claim is supported.

The hosted frontend provides the interface, virtual lab and static research
evidence. Full instrument sessions and local research jobs require the Python
backend; publishing the frontend does not deploy that backend. The complete
local instrument remains available while `python run_argus.py` is running.
