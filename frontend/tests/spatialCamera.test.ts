import assert from 'node:assert/strict';
import test from 'node:test';
import { panelProjection, reliefNormal, wrapAzimuth } from '../components/spatialGeometry.ts';

const view = { widthMm: 600, heightMm: 400, viewportWidth: 800, viewportHeight: 430, azimuthDeg: 0, elevationDeg: 90, zoom: 1 };

test('top camera preserves physical aspect, upper-left origin and probability height does not displace the planar position', () => {
  const { project } = panelProjection(view);
  const origin = project(0, 0), x = project(1, 0), y = project(0, 1), peak = project(0, 0, .23);
  assert.ok(x.x > origin.x && y.y > origin.y);
  assert.ok(Math.abs((x.x - origin.x) / (y.y - origin.y) - 1.5) < 1e-9);
  assert.ok(Math.abs(peak.x - origin.x) < 1e-9 && Math.abs(peak.y - origin.y) < 1e-9);
  assert.ok(peak.depth > origin.depth);
});

test('front camera gives a real side projection; orbit changes which panel side is near', () => {
  const front = panelProjection({ ...view, elevationDeg: 0 }).project;
  assert.ok(Math.abs(front(.5, 0).y - front(.5, 1).y) < 1e-9);
  assert.ok(front(.5, .5, .2).y < front(.5, .5, 0).y);
  const forward = panelProjection({ ...view, elevationDeg: 38 }).project;
  const reverse = panelProjection({ ...view, elevationDeg: 38, azimuthDeg: 180 }).project;
  assert.ok(forward(.5, 1).depth > forward(.5, 0).depth);
  assert.ok(reverse(.5, 1).depth < reverse(.5, 0).depth);
});

test('camera fit remains finite and inside the viewport for extreme physical aspects and orbit angles', () => {
  for (const [widthMm, heightMm] of [[600, 400], [100, 5000], [5000, 100]]) for (const azimuthDeg of [-180, -90, 0, 90, 179]) for (const elevationDeg of [0, 38, 90]) {
    const project = panelProjection({ ...view, widthMm, heightMm, azimuthDeg, elevationDeg, viewportWidth: 320, viewportHeight: 330 }).project;
    for (const x of [0, 1]) for (const y of [0, 1]) for (const z of [-.032, .26]) {
      const p = project(x, y, z);
      assert.ok(Number.isFinite(p.depth) && p.x > 0 && p.x < 320 && p.y > 0 && p.y < 330);
    }
  }
});

test('camera rejects invalid scales and wraps angles; shading normals remain unit length', () => {
  for (const change of [{ widthMm: 0 }, { heightMm: NaN }, { viewportWidth: 0 }, { elevationDeg: 91 }, { zoom: 0 }]) assert.throws(() => panelProjection({ ...view, ...change }), RangeError);
  assert.equal(wrapAzimuth(540), -180);
  assert.equal(wrapAzimuth(-361), -1);
  assert.throws(() => wrapAzimuth(NaN), RangeError);
  const normal = reliefNormal(.5, -.3, 1, 2 / 3);
  assert.ok(Math.abs(Math.hypot(normal.x, normal.y, normal.z) - 1) < 1e-12);
  assert.ok(normal.x < 0 && normal.y > 0 && normal.z > 0);
});
