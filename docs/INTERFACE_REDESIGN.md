# ARGUS spatial interface

The interface uses one ink-navy/ivory visual system across the launch page,
instrument views, virtual lab, physical guide and phone probe. A lightweight
canvas-projected spatial field runs behind the whole app. The main panel is a
real geometric projection of the live posterior, not a rendered stock image.

## What the operator sees

- Launch: editorial introduction, interactive panel orbit, difficulty and actual
  panel dimensions, simulation/physical entry points, and an explicit research
  planner opt-in.
- Overview: live posterior relief, source/receiver positions, physical R90,
  a compact acquisition loop, the authoritative 2D posterior, and an auditable
  candidate table. The 2D panel preserves physical aspect ratio.
- Reasoning: structure/instrument uncertainty, counterfactual hypotheses and,
  when enabled, actual regional information bits with numerical diagnostics.
- Research: recorded paired results, uncertainty intervals, losses and failures,
  plus existing local research jobs. `/research` works without the backend.
- Signals/history: matching colours, keyboard-selectable posterior frames and
  accessible canvas descriptions.

Relief height is relative posterior probability, never defect depth. Circles
are computed in physical units; they are not a certified coverage guarantee.
Moving acoustic rings are labelled illustrative. Before a session there is no
fabricated posterior peak.

Global pause and reduced-motion preferences stop background/canvas animation.
Hidden-page and off-screen rendering is suspended; high-DPI buffers are capped.
The scene uses the existing browser canvas API and adds no 3D runtime dependency.
The page recovers when the local engine starts after it has already loaded.

## Sharing artwork

Asset: `frontend/public/og.png`, 1733 x 907 PNG. Generated with one built-in
image-generation request and visually inspected. Used only as the branded
sharing preview; it does not replace the live scientific visualization.

Final generation brief:

> Premium editorial ARGUS social card, ink-navy background, warm ivory
> "ARGUS." and "See beyond the surface." typography, physically rendered
> isometric opaque panel with acoustic concentric ripples, restrained ice-blue
> lighting, tiny amber accents, modest technical grid, calm negative space;
> conceptual illustration without metrics or claims.

The Open Graph/X image URL uses the existing trusted Sites origin, not an
unvalidated request host.

## Verification boundary

TypeScript, frontend unit tests, lint and production build were checked. The
geometry tests verify physical circles, panel aspect, posterior-relative heights,
malformed input handling, and explicit research opt-in. Backend tests and live
API acquisition verify the scientific integration. The browser connection was
unavailable in this session, so visual browser/device QA was not performed.
The generated social image and rendered manuscript were inspected separately.
