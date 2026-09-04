import assert from 'node:assert/strict';
import test from 'node:test';

import { DEFAULT_VIRTUAL_CONFIG, flexuralPlateProperties, simulateVirtualExperiment } from '../utils/virtualAcoustics.ts';

test('flexural plate model responds to physical thickness and frequency', () => {
  const baseline = flexuralPlateProperties('aluminum', 3, 6000);
  const thicker = flexuralPlateProperties('aluminum', 6, 6000);
  const higherFrequency = flexuralPlateProperties('aluminum', 3, 12000);
  assert.ok(baseline.groupVelocityMps > 0);
  assert.ok(thicker.groupVelocityMps > baseline.groupVelocityMps);
  assert.ok(higherFrequency.groupVelocityMps > baseline.groupVelocityMps);
  assert.ok(baseline.flexuralRigidityNm > 0);
});

test('virtual measurement is deterministic for a fixed seed and sample rate', () => {
  const first = simulateVirtualExperiment(DEFAULT_VIRTUAL_CONFIG);
  const second = simulateVirtualExperiment(DEFAULT_VIRTUAL_CONFIG);
  assert.equal(first.samples.length, Math.round(DEFAULT_VIRTUAL_CONFIG.sampleRateHz * DEFAULT_VIRTUAL_CONFIG.durationMs / 1000));
  assert.deepEqual(first.samples.slice(0, 100), second.samples.slice(0, 100));
  assert.ok(first.samples.every(Number.isFinite));
  assert.ok(first.spectrum.every((point) => Number.isFinite(point.frequencyHz) && Number.isFinite(point.magnitudeDb)));
});

test('scattered route obeys geometry and a healthy panel removes defect gain', () => {
  const damaged = simulateVirtualExperiment(DEFAULT_VIRTUAL_CONFIG);
  const healthy = simulateVirtualExperiment({ ...DEFAULT_VIRTUAL_CONFIG, defectSeverity: 0 });
  assert.ok(damaged.metrics.scatterPathM >= damaged.metrics.directPathM);
  assert.ok(damaged.metrics.scatterArrivalMs >= damaged.metrics.directArrivalMs);
  assert.ok(damaged.paths.find((path) => path.id === 'scatter')!.relativeGain > 0);
  assert.equal(healthy.paths.find((path) => path.id === 'scatter')!.relativeGain, 0);
});

test('moving the receiver changes path length and predicted arrival', () => {
  const near = simulateVirtualExperiment({ ...DEFAULT_VIRTUAL_CONFIG, receiver: { x: 0.25, y: 0.25 } });
  const far = simulateVirtualExperiment({ ...DEFAULT_VIRTUAL_CONFIG, receiver: { x: 0.92, y: 0.88 } });
  assert.ok(far.metrics.directPathM > near.metrics.directPathM);
  assert.ok(far.metrics.directArrivalMs > near.metrics.directArrivalMs);
});

test('invalid sample-rate input is sanitized before enforcing the Nyquist margin', () => {
  const invalid = simulateVirtualExperiment({ ...DEFAULT_VIRTUAL_CONFIG, sampleRateHz: Number.NaN, centerFrequencyHz: 16000 });
  assert.equal(invalid.config.sampleRateHz, 8000);
  assert.equal(invalid.config.centerFrequencyHz, 3360);
  assert.ok(invalid.samples.every(Number.isFinite));
  assert.ok(Object.values(invalid.metrics).every((value) => typeof value === 'boolean' || Number.isFinite(value)));
});
