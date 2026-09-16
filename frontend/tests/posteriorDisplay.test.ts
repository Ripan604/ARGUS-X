import assert from 'node:assert/strict';
import test from 'node:test';
import { containmentEllipse, panelCanvasSize, posteriorColor } from '../utils/posteriorDisplay.ts';

test('physical panel fit preserves aspect for wide, tall, and square panels', () => {
  for (const [width, height] of [[0.6, 0.4], [0.1, 5], [5, 0.1], [1, 1]]) {
    const fitted = panelCanvasSize(width, height);
    assert.ok(fitted.width <= 900 && fitted.height <= 590);
    assert.ok(Math.abs((fitted.width - 48) / width - (fitted.height - 48) / height) <= 5.1);
  }
  assert.throws(() => panelCanvasSize(0, 1), RangeError);
  assert.throws(() => panelCanvasSize(Infinity, 1), RangeError);
});

test('R90 circle is projected using physical millimetres on each axis, including zero radius', () => {
  assert.deepEqual(containmentEllipse(30, 0.6, 0.4, 600, 400), { x: 30, y: 30 });
  assert.deepEqual(containmentEllipse(30, 0.6, 0.4, 600, 200), { x: 30, y: 15 });
  assert.deepEqual(containmentEllipse(0, 0.6, 0.4, 600, 400), { x: 0, y: 0 });
  assert.equal(containmentEllipse(NaN, 0.6, 0.4, 600, 400), null);
});

test('posterior palette remains finite at zero, malformed, and normalized extremes', () => {
  assert.equal(posteriorColor(0, 1), 'rgb(13,25,40)');
  assert.equal(posteriorColor(1, 1), 'rgb(119,219,235)');
  assert.equal(posteriorColor(NaN, 0), posteriorColor(0, 1));
  assert.equal(posteriorColor(-0.1, 1), posteriorColor(0, 1));
});
