import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

import { clamp01, percent, responseDelayMilliseconds, typedValue } from '../utils/neo.ts';

test('uncertainty display values are bounded and explicit', () => {
  assert.equal(clamp01(-0.4), 0);
  assert.equal(clamp01(1.4), 1);
  assert.equal(clamp01(Number.NaN), 0);
  assert.equal(percent(0.456, 1), '45.6%');
});

test('structured planner values reject non-numeric content', () => {
  assert.equal(typedValue({ value: 0.75 }, 'value'), 0.75);
  assert.equal(typedValue({ value: '0.75' }, 'value', 0.2), 0.2);
  assert.equal(typedValue(undefined, 'value', 0.3), 0.3);
});

test('counterfactual response delay is extracted safely', () => {
  assert.equal(responseDelayMilliseconds({ mean: [0.00125, 2] }), 1.25);
  assert.equal(responseDelayMilliseconds({ mean: [] }), null);
  assert.equal(responseDelayMilliseconds({}), null);
});

test('development runtime disables unsafe pre-socket console forwarding', () => {
  const config = readFileSync(new URL('../vite.config.ts', import.meta.url), 'utf8');
  assert.match(config, /forwardConsole:\s*false/);
});

test('3D narrative preserves semantic story and reduced-motion accessibility', () => {
  const component = readFileSync(new URL('../components/NarrativeTwin.tsx', import.meta.url), 'utf8');
  const styles = readFileSync(new URL('../app/globals.css', import.meta.url), 'utf8');
  assert.match(component, /From silence to a defensible next move/);
  assert.match(component, /Animated digital twin showing an acoustic experiment/);
  assert.match(styles, /prefers-reduced-motion:\s*reduce/);
  assert.match(styles, /\.mission-narrative/);
});
