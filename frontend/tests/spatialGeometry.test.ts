import assert from 'node:assert/strict';
import test from 'node:test';
import { normalizedRelief, physicalCircle } from '../components/spatialGeometry.ts';

test('3D contour samples are an exact physical circle on a rectangular panel', () => {
  const circle = physicalCircle(.25, .7, 90, 1200, 300, 64);
  assert.equal(circle.length, 65);
  for (const point of circle) {
    assert.ok(Math.abs(Math.hypot((point.x - .25) * 1200, (point.y - .7) * 300) - 90) < 1e-10);
  }
  assert.ok(Math.abs(circle[0].x - circle.at(-1)!.x) < 1e-12);
  assert.ok(Math.abs(circle[0].y - circle.at(-1)!.y) < 1e-12);
});

test('contour retains out-of-panel geometry for clipping, not an invented smaller radius', () => {
  const circle = physicalCircle(.02, .5, 90, 600, 400);
  assert.ok(circle.some((point) => point.x < 0));
  assert.deepEqual(physicalCircle(.5, .5, -1, 600, 400), []);
  assert.deepEqual(physicalCircle(NaN, .5, 10, 600, 400), []);
  assert.deepEqual(physicalCircle(.5, .5, 10, 600, 400, 0), []);
});

test('posterior relief preserves relative probabilities and has no invented landing peak', () => {
  assert.equal(normalizedRelief(undefined), null);
  assert.equal(normalizedRelief([]), null);
  const relief = normalizedRelief([[.1, .2], [.3, .4]])!;
  relief.flat().forEach((value, index) => assert.ok(Math.abs(value - [.25, .5, .75, 1][index]) < 1e-12));
  assert.deepEqual(normalizedRelief([[.25, .25], [.25, .25]]), [[1, 1], [1, 1]]);
  assert.equal(normalizedRelief([[0, NaN]]), null);
  assert.equal(normalizedRelief([[1], [1, 2]]), null);
});
