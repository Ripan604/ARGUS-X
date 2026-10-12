# Landing-page hydration diagnostics — 12 October 2026

The reported screenshot shows a React hydration mismatch in the landing-page
router tree. The visible portion does not include React's element-level `+`/`-`
diff, so it does not establish which element differed or the exact trigger.

The existing server and client component startup states were inspected. Engine
health and saved-session storage are loaded in effects; the first markup uses
fixed values. The visual refinement's canvas changes execute after mounting.
No invalid initial HTML nesting or deterministic first-render difference was
found. An older repeated React renderer warning was present in the previous
development process, but that warning alone does not prove the hydration cause.

## Recovery action

The verified ARGUS workspace launcher and its child services were restarted.
The new runtime serves the frontend on `http://localhost:5173` and API on port
8001. No session database, scientific result, uploaded observation or model was
deleted. The long-lived hot-reload runtime was replaced; the visual changes were
retained. A hard refresh is needed to verify the result in the affected browser.
The original browser-specific failure was not reproduced in the fresh runtime's
virtual DOM checks. Its exact cause remains unconfirmed.

## New verification

`frontend/tests/hydration.test.ts` bundles the actual Home and SpatialWorld
components, renders their server HTML and hydrates that markup in jsdom. It
checks that hydration emits no React console/recoverable errors and that saved
session storage and a later health response update the page after hydration.
This catches real initial-render mismatches, rather than comparing two strings
or suppressing hydration warnings.

The explicit live check loads the local server's actual inline RSC bootstrap
and HTTP-transformed module graph, preserving the router, root layout and
existing server DOM:

```powershell
cd frontend
npm run test:hydration-live
```

The final check loaded 187 modules and eight client references. It reached the
hydrated state, preserved the original landing and 3D scene DOM nodes, and
reported zero errors. Real loopback API health was checked. The bounded report
is `output/release/hydration-live-2026-10-12.json`, including source hashes and
an explicit description of its mocked browser APIs.

This is virtual DOM integration, not an interactive Chrome/Edge verification.
Canvas/media/animation, HMR and CSS loading are mocked. It does not reproduce
browser extensions, asset-cache behavior or every real browser timing sequence.
Those limits prevent claiming that the screenshot's exact cause is proven.
If the error persists after a hard refresh, the copied overlay diff is needed
to identify the actual mismatched element.

The complete frontend run passed **89 tests**, TypeScript checking, lint and a
production build. Twelve focused continuity tests also passed. Frontend check
hashing now includes diagnostic `.mjs` scripts, so edits to that verification
code invalidate the retained freshness record. No production data/state logic
or measured performance claim changed.

The live checker loads executable code only from fixed localhost:5173, rejects
credentials and redirects, limits module/document counts and allocations, and
allows only read-only local API health requests. Temporary directories are
resolved and verified within the workspace before recursive cleanup. No full
DOM, API body, client-reference URLs or credentials are stored in its report.
