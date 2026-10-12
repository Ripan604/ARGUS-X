import assert from 'node:assert/strict';
import test from 'node:test';
import { summarizePosterior, comparePosteriors } from '../utils/posteriorReview.ts';

test('uniform and concentrated fields have correct entropy, tied mass and physical means', () => {
  const flat = summarizePosterior([[.25, .25], [.25, .25]])!;
  assert.equal(flat.entropyBits, 2); assert.equal(flat.effectiveCells, 4);
  assert.equal(flat.area90Fraction, 1); assert.equal(flat.mass90, 1);
  assert.deepEqual(flat.mean, { x: .5, y: .5 });
  const point = summarizePosterior([[0, 0], [0, 1]])!;
  assert.equal(point.entropyBits, 0); assert.equal(point.area90Fraction, .25);
  assert.deepEqual(point.map, { x: .75, y: .75 });
});
test('comparison measures distribution change independently of entropy reduction', () => {
  const result = comparePosteriors([[1, 0]], [[0, 1]], 600, 400)!;
  assert.equal(result.jsBits, 1); assert.equal(result.totalVariation, 1);
  assert.equal(result.entropyChangeBits, 0); assert.equal(result.meanShiftMm, 300);
  const unchanged = comparePosteriors([[.3, .7]], [[.3, .7]], 400, 600)!;
  assert.equal(unchanged.jsBits, 0); assert.equal(unchanged.totalVariation, 0);
});
test('posterior comparison is symmetric and does not mutate recorded fields', () => {
  const a = [[.1, .4], [.2, .3]], b = [[.2, .1], [.3, .4]], copy = JSON.stringify([a, b]);
  const ab = comparePosteriors(a, b, 600, 400)!, ba = comparePosteriors(b, a, 600, 400)!;
  assert.ok(Math.abs(ab.jsBits - ba.jsBits) < 1e-12);
  assert.ok(Math.abs(ab.entropyChangeBits + ba.entropyChangeBits) < 1e-12);
  assert.equal(JSON.stringify([a, b]), copy);
});
test('invalid distributions and incompatible grids cannot produce plausible review metrics', () => {
  for (const grid of [[], [[]], [[.5], [.25, .25]], [[NaN, 1]], [[-.1, 1.1]], [[0, 0]], [[.6, .6]]]) {
    assert.equal(summarizePosterior(grid), null);
  }
  assert.equal(comparePosteriors([[1, 0]], [[1], [0]], 600, 400), null);
  assert.equal(comparePosteriors([[1]], [[1]], Infinity, 400), null);
});
