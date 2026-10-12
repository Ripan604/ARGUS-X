# ARGUS instrument workspace and evidence review

Updated 9 October 2026. This upgrade improves operation, interpretation and
reproducibility of the existing research instrument. It does not change the
frozen scientific study implementations or establish new physical accuracy.

## Using the instrument

Run `python run_argus.py`, open `http://localhost:5173`, and start or resume a
session. The workspace separates investigation, validation and field tools.
Use **Find a view** or **Ctrl/Cmd K** to search for a workspace. The narrow-screen
layout uses the Instrument view selector. The toolbar remains visible while
scrolling, including Refresh state and Stop session. Stop release remains in
Assurance with an operator reason.

Overview puts the current posterior, physical containment radius, model trust,
operating condition and recommended acquisition together. A compact spacing
mode is available. The animated spatial explanation is opened on demand.
Model trust is an internal agreement score. Posterior mass is not a measured
probability that an inspection will be correct.

Posterior review compares an experiment's stored before/after fields or the
initial loaded field. It provides:

- Side-by-side fields, a signed probability-change map, and a 90% mass overlay.
- Entropy change in bits, Jensen–Shannon divergence, and physical mean shift.
- A selectable entropy timeline and a CSV of the recorded update metrics.
- Explicit handling of missing history and invalid probability fields.

Cells use their physical centers and the actual panel dimensions. The 90%
region includes all cells tied at the cutoff, so a uniform field selects the
whole panel. Selected cells may be disconnected. Difference-map colors share
a symmetric scale; probability fields use their own maximum for visibility.
These calculations describe the recorded model, including an increase in
uncertainty. They do not use sealed ground truth or change the live inference.

CSV rows always compare each experiment with its own recorded before-state,
regardless of the interactive comparison selection. Use Evidence ledger for
the complete stored acquisition record and integrity checks.

## Evidence laboratory

`http://localhost:5173/research` works without the acoustic backend. It includes
the completed 29-bank reference-conditioned confirmation and a four-task
measured-data explorer with context and metric controls. Every study retains
its units, grouping, original source, license, source hashes and limitations.
The general failure summary remains visible when a task filter is applied.

`scripts/export_fundamental_web_summary.py` checks all three canonical study
artifacts, their before/after source manifests, the review document and the
canonical summary before creating the compact browser artifact. The export
checked 58 distinct source/data files. The page reports when that check was
performed; the browser itself does not rehash local recordings.

The completed confirmation remains negative for the proposed compensation:
adaptive conditional mean errors are 161.2 mm raw, 206.5 mm with global-noise
transport and 215.4 mm with path-specific-noise transport. Each adaptive
variant alerted on 0/8 damage conditions and 0/2 unique healthy test banks.
Zero healthy alerts alongside zero damage detections is not successful
detection. Healthy reference discrepancy improved from 0.271 to 0.063, while
only 20/66 paths qualified across all three healthy temperature anchors.

## Request lifecycle and fault handling

Session operations now carry an identity, start time, status and ownership
epoch. Reset, replacement and unmount invalidate the old response context.
Late responses cannot restore a departed session, clear a new operation's
busy flag or overwrite a replacement session with an unrelated result.
Duplicate foreground actions are refused before dispatch.

Safety acknowledgments are session-bound, require the requested latch state
and an engine timestamp, and compare timestamps at microsecond precision.
A late ordinary response cannot clear a confirmed stop. A pending stop blocks
the next stage of microphone/device acquisition before that stage is sent.
Only engine acknowledgments establish the displayed confirmed stop state.

A completed measurement followed by an unavailable history read is shown as
partial success, with the measurement preserved and a reconciliation message.
Refresh state reads saved state/history without repeating the physical action.
Leaving a busy session explicitly says that dispatched work may still finish
on the engine. Response fencing is not cancellation or physical interruption.

Instrument views are loaded on demand and isolated by a view error boundary;
navigation and stop controls remain outside it. The spatial renderer is not
mounted while its disclosure is closed. Research-job polling does not stack
requests, uses a slower interval when idle, stops in hidden tabs, aborts reads
on unmount and prevents duplicate job actions. No new dependency was added.

## Validation

The final frontend check record is `output/release/frontend-checks.json`.
It records 56 passing tests, TypeScript checking, ESLint and a production build,
with source hashes captured around the run. Tests exercise delayed successes
and failures, replacement sessions, stop/release ordering, malformed evidence,
posterior geometry, tied mass regions and distribution-change identities.

Browser checks covered saved-session resumption, a simulation measurement,
historical field comparison, overlays, search/keyboard navigation, the mobile
view selector, evidence filters/context/metric controls and page overflow at
a 390-pixel viewport setting (375 CSS content pixels after the scrollbar).
No physical probe was connected or actuated. Safety ordering is covered by
the controlled request tests; browser actions did not stop another saved
session for testing.

The earlier backend validation remains 662 passed and one deliberate legacy
checkpoint skip. These UI changes do not rerun or relabel the measured studies.
The two research PDFs contain the frozen scientific results; this document
describes the subsequent workspace improvements.

## Boundaries

The UI does not turn the experimental compensation into a deployed detector,
certify structural safety or establish patent novelty. The remaining physical
work is a stronger structural forward model, independent specimen evaluation,
and a prospective apparatus campaign with measured timing and drive evidence.

Review artifacts are local. No site was published and no patent was filed.
