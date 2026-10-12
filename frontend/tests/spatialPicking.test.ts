import assert from 'node:assert/strict';
import test from 'node:test';
import { normalizedRelief, panelProjection, pickPosteriorCell, projectedReliefFaces } from '../components/spatialGeometry.ts';

const view = { widthMm: 600, heightMm: 400, viewportWidth: 800, viewportHeight: 430, azimuthDeg: -27, elevationDeg: 38, zoom: 1 };
const posterior = Array.from({ length: 5 }, () => Array.from({ length: 8 }, () => 1 / 40));

test('top-view picks every discrete cell with the same upper-left origin as 2D', () => {
  const top = { ...view, azimuthDeg: 0, elevationDeg: 90 }, { project } = panelProjection(top);
  for (let row = 0; row < 5; row++) for (let column = 0; column < 8; column++) {
    const point = project((column + .5) / 8, (row + .5) / 5, .23);
    assert.deepEqual(pickPosteriorCell(posterior, top, point.x, point.y), { row, column });
  }
});

test('picking follows the elevated visible surface rather than its displaced floor', () => {
  for (const azimuthDeg of [-120, -27, 0, 60, 150]) for (const elevationDeg of [25, 38, 70]) {
    const camera = { ...view, azimuthDeg, elevationDeg }, { project } = panelProjection(camera);
    const point = project(.45, .55, .23);
    assert.deepEqual(pickPosteriorCell(posterior, camera, point.x, point.y), { row: 2, column: 3 });
  }
});

test('camera zoom and panel aspect preserve the same physical selection', () => {
  for (const zoom of [.6, 1, 1.6]) for (const [widthMm, heightMm] of [[600, 400], [100, 5000], [5000, 100]]) {
    const camera = { ...view, widthMm, heightMm, zoom, viewportWidth: 320, viewportHeight: 380 };
    const point = panelProjection(camera).project(.6, .66, .23);
    assert.deepEqual(pickPosteriorCell(posterior, camera, point.x, point.y), { row: 3, column: 4 });
  }
});

test('outside clicks and an edge-on flat surface do not invent a selection', () => {
  assert.equal(pickPosteriorCell(posterior, view, 0, 0), null);
  assert.equal(pickPosteriorCell(posterior, view, NaN, 100), null);
  const front = { ...view, azimuthDeg: 0, elevationDeg: 0 };
  const point = panelProjection(front).project(.5, .5, .23);
  assert.equal(pickPosteriorCell(posterior, front, point.x, point.y), null);
});

test('the floor rim and single-cell grids remain inspectable', () => {
  const top = { ...view, azimuthDeg: 0, elevationDeg: 90 }, { project } = panelProjection(top);
  const rim = project(.01, .99);
  assert.deepEqual(pickPosteriorCell(posterior, top, rim.x, rim.y), { row: 4, column: 0 });
  const center = project(.5, .5);
  assert.deepEqual(pickPosteriorCell([[1]], top, center.x, center.y), { row: 0, column: 0 });
});

test('render and picking share the exact vertex samples, relative heights and painter order', () => {
  const field = normalizedRelief([[.05, .1, .15], [.2, .2, .3]])!;
  const { project } = panelProjection(view), faces = projectedReliefFaces(field, project);
  assert.equal(faces.length, 2);
  assert.ok(faces[0].depth <= faces[1].depth);
  for (const face of faces) for (const point of face.points) {
    const row = Math.floor(point.panelY * 2), column = Math.floor(point.panelX * 3);
    assert.deepEqual({ x: point.x, y: point.y, depth: point.depth }, project(point.panelX, point.panelY, field[row][column] * .23));
  }
});

test('sparse, oversized or malformed posterior grids cannot enter surface picking', () => {
  const sparse = [[.5, .5], new Array<number>(2)];
  assert.equal(normalizedRelief(sparse), null);
  assert.equal(pickPosteriorCell(sparse, view, 100, 100), null);
  assert.equal(normalizedRelief(Array.from({ length: 257 }, () => new Array<number>(256).fill(1))), null);
  assert.equal(pickPosteriorCell([[.1], [.2, .3]], view, 100, 100), null);
});
