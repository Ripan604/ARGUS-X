# Visual refinement — 12 October 2026

ARGUS retains its dark instrument presentation with a consistent graphite/navy
palette, warm ivory landing headline, soft teal controls, restrained amber
caution states and shared panel surfaces. The refinement covers the landing
page, workspace navigation, observation readouts, 3D/2D observatory, numerical
profiles and candidate comparisons.

## What changed

- Shared palette and surface tokens in `frontend/app/globals.css`; rounded
  panels, quieter borders and subtle depth replace the competing visual styles.
- Landing composition in `frontend/components/landing-aesthetic.css`, scoped
  to the launcher: framed interactive 3D illustration, clearer primary action,
  larger input controls, editorial headings and method cards.
- Workspace hierarchy: readable navigation, separate KPI cards, tabular numeric
  readouts, larger recommendation text and a wrapping mobile toolbar that keeps
  the stop action available.
- Spatial panels: segmented view controls, framed cyan/violet profile charts,
  legible field facts and larger inspection controls. The pointer viewport has
  no padding or border, preserving its alignment with the canvas.
- 3D rendering: a soft floor shadow and subtle panel finish. Quarter-axis labels
  use the actual physical dimensions and appear only on sufficiently long
  projected axes in wider viewports. Labels outside the canvas are omitted;
  zoom or narrow physical aspects do not invent displaced coordinates.
- Candidate cards: distinct recommended and selected states, framed route
  previews, larger signed scores and grouped parameters. Ranking, execution and
  underlying scientific values are unchanged.

Responsive rules preserve the 3D, 2D and split modes and support narrow layouts
down to 320 pixels. Keyboard focus, linked inspection, touch behavior, pause
controls and reduced-motion preferences remain available. Canvas lighting is a
display effect; surface height still represents relative posterior mass, and
the panel thickness and animated waves remain illustrative.

## Verification and limits

The final frontend run passed **88 tests**, TypeScript checking, lint and a
production build. The source hashes remained unchanged during that run;
`output/release/frontend-checks.json` records the actual results. Geometric
selection, physical coordinates and exported profile values remain covered by
the existing behavioral tests. No backend behavior or measured experiment was
changed, so physical performance findings remain as documented.

The main opaque palette pairs have approximate contrast ratios of 15.42 for
panel text, 7.93 for secondary labels and 10.96 for the primary action. These
calculations cover the declared colours only, not every composited element or
a complete accessibility audit.

The browser connector returned no available browser. Screenshot review and
interactive checks of wrapping, pointer behavior and rendering on real devices
remain pending. Passing the build and geometry tests does not substitute for
that visual verification.
