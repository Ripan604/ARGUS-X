# Spatial visualization upgrade — 11 October 2026

The overview now opens with a full-width spatial observatory. The live 3D
posterior is visible by default; it is no longer inside a collapsed explanation.
The next experiment and its recursive sequence appear directly below it.

## Using the views

- **3D surface:** drag to orbit, or use the azimuth, elevation and zoom sliders.
  Isometric, Top, Front and Reset view provide reproducible camera positions.
  Arrow keys rotate a focused scene, +/− zoom, and Home resets the camera.
  Expand scene increases the drawing area.
- **2D inspection:** hover, tap or use arrow keys on the focused map to inspect
  exact cell mass and physical cell-centre coordinates. Home and End select the
  first and last cells. Physical axes use an upper-left origin.
- **Split view:** compare both representations of the current posterior. On
  smaller screens these views stack rather than shrink into unreadable panels.
- **Overlays:** independently inspect measurement paths, hypotheses and the
  R90 boundary. The 3D scene also includes grid and illustrative-ring controls.
- **Exclusion zones:** enter Draw exclusion zone, drag a rectangle and release
  to submit it. The preview appears during the drag. Escape cancels. Inspection
  does not submit region changes; editing is blocked during operations, while
  offline, or with the emergency stop latched.
- **Candidate comparison:** select a route card to inspect its actual parameters
  and planner terms. Previewing an alternative does not change the engine's
  recommendation or execute an experiment.

## Visual and scientific meaning

The shaded 3D surface uses the current posterior divided by its largest cell.
The two planar dimensions preserve the panel's physical aspect ratio. Surface
height is a display coordinate for relative probability, not material thickness
or defect depth. The landing-page panel remains flat and illustrative.

Transmitter, receiver and MAP markers have distinct colours. Recorded paths and
the next recommended route are projected annotations, not ray tracing or measured
wave propagation. The optional moving rings are explicitly illustrative. Motion
obeys the global pause control, reduced-motion preference, page visibility and
scene visibility. Static scenes do not run a continuous animation loop.

R90 is drawn using the radius in millimetres on each physical panel axis. It is
clipped at the panel boundary, without shrinking the underlying radius. This is
model posterior containment, not field-calibrated localization coverage. The
readout lists physical MAP coordinates, cell spacing, exact peak mass and mass
within the supplied radii. Revealed simulation truth is shown in the planar view
only when the session says it has been revealed.

Candidate cards preserve physical aspect and distinguish the actual engine
recommendation by the complete excitation parameters. Comparison bars share
zero-inclusive axes so a negative planner score is not displayed as positive.
All figures use session data; no research results or validation studies were
changed by this interface upgrade.

## Verification

The frontend suite covers camera projection, physical aspect at extreme panel
dimensions, top/front orientation, depth ordering, relative relief, contour
geometry, pointer conversion, keyboard cell movement, exclusion rectangles,
candidate identity and signed score bars. Final command results and source
hashes are recorded in `output/release/frontend-checks.json`.

The local engine and frontend responded successfully during implementation.
The browser integration returned no available Chrome or in-app browser surface,
including after the user requested browser access. Consequently, this revision
has not yet received an interactive browser or screenshot review. Build and
geometry checks do not establish pixel-perfect rendering or end-to-end pointer
behaviour on every device.

Main implementation: `SpatialObservatory.tsx`, `SpatialScene.tsx`,
`PosteriorMap.tsx` and `CandidateComparison.tsx` in `frontend/components/`.

## Linked inspection refinement — 12 October 2026

The inspection location is now shared by the 2D map, 3D surface and two numerical
profile charts. It starts at the MAP cell. Move it by inspecting the map or by
using the X/Y cell sliders; Inspect MAP returns to the current model estimate.
The camera and layer controls remain mounted when switching views, while hidden
views suspend their drawing work. Inspection stays separate from region editing.

The cyan trace follows the selected row and the violet trace follows the selected
column. Each plotted value is the original probability mass of that cell. Both
charts share the full posterior's peak as their vertical maximum. No slice is
renormalized, smoothed or summed into a marginal. Their coordinates are physical
cell centres; their heights do not represent cuts through the material. The same
traces appear on the 3D relief. Export slices downloads the exact row and column
as CSV, including the intersection cell once in each slice.

Camera keyboard handling preserves browser shortcuts, and mobile sliders have
larger touch targets. The scene distinguishes next recommended TX/RX positions
from historical paths, and computed R90 from illustrative excitation rings.
The linked readout and profile charts stay available in Split view.

Exclusion drawing now has a single owning pointer. A second touch cannot replace
or cancel that gesture. Switching modes, blocking editing, changing sessions or
changing region geometry clears the draft and exits drawing mode without losing
the selected cell or overlay choices. Late events from an old interaction cannot
submit a region in the new one.

New profile tests verify exact numerical slices, shared scale, physical
coordinates, unmodified source data, malformed-input rejection and CSV contents.
Read-only calculations also passed against saved one- and eight-experiment
simulation sessions. These checks did not acquire measurements or edit regions.
Gesture tests cover pointer ownership, cancellation, blocking and stale events.
The browser connector still reported no available browser on 12 October, so the
interactive visual review remains pending. The final source-hash check record
is the verification authority for this revision.

## Direct 3D surface inspection — 12 October 2026

The default 3D view now has two explicit interaction modes. **Orbit camera**
retains pointer and arrow-key camera navigation. **Inspect surface** picks a
visible location on the rendered probability relief and updates the same cell
used by the 2D crosshair and numerical profiles. Its readout gives physical cell
centre coordinates and the original probability mass. Arrow keys move through
cells, Home/End reach grid corners, and Escape returns to camera orbit.

Rendering and picking share the relief vertices, normalized heights and painter
order; picking accounts for overlapping faces and rejects outside clicks.
Seven added geometric tests cover camera angle, zoom, physical aspect, surface
height, edge-on ambiguity and malformed grids. The complete frontend run passed
88 tests, type checking, lint and a production build, with unchanged source
hashes during that run. No connected browser was available for visual review.
