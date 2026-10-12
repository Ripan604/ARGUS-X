import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import { formatMeasuredMetric, parseMeasuredReport } from '../utils/measuredEvidence.ts';

const published = () => JSON.parse(readFileSync(new URL('../public/research/measured-data-summary.json', import.meta.url), 'utf8'));

test('saved measured summary is bounded and keeps screening, quality and localization distinct', () => {
  const raw = readFileSync(new URL('../public/research/measured-data-summary.json', import.meta.url), 'utf8');
  assert.ok(Buffer.byteLength(raw) <= 100000);
  const report = parseMeasuredReport(JSON.parse(raw));
  assert.ok(report);
  assert.equal(report.studies.length, 4);
  const gfrp = report.studies.find((study) => study.id === 'gfrp');
  assert.equal(gfrp?.task, 'tap_screening');
  assert.equal(gfrp?.headline.unit, 'fraction');
  const ogw = report.studies.find((study) => study.id === 'ogw');
  assert.equal(ogw?.task, 'recorded_path_replay');
  assert.equal(ogw?.native_sample_rate_hz, 10000000);
  assert.equal(ogw?.headline.unit, 'mm');
  assert.equal(report.hardware_validated, false);
});

test('source mismatches, unsupported links and task relabelling cannot render as verified evidence', () => {
  for (const mutate of [
    (value: ReturnType<typeof published>) => { value.studies[0].source_verification.current_matches = false; },
    (value: ReturnType<typeof published>) => { value.studies[0].source_url = 'javascript:alert(1)'; },
    (value: ReturnType<typeof published>) => { value.studies[0].task = 'recorded_path_replay'; },
    (value: ReturnType<typeof published>) => { value.studies[0].headline.unit = 'mm'; },
    (value: ReturnType<typeof published>) => { value.studies[1].id = 'gfrp'; },
    (value: ReturnType<typeof published>) => { value.hardware_validated = true; },
  ]) {
    const payload = published(); mutate(payload);
    assert.equal(parseMeasuredReport(payload), null);
  }
});

test('invalid metric values and reversed intervals do not produce plausible results', () => {
  for (const invalid of [NaN, Infinity, -0.1, 1.1, '0.83']) {
    const payload = published(); payload.studies[0].headline.value = invalid;
    assert.equal(parseMeasuredReport(payload), null);
  }
  const payload = published(); payload.studies[0].interval.bounds = [0.9, 0.7];
  assert.equal(parseMeasuredReport(payload), null);
});

test('metric formatting preserves units and unavailable evidence', () => {
  assert.equal(formatMeasuredMetric(0.838, 'fraction'), '83.8%');
  assert.equal(formatMeasuredMetric(108.991, 'mm'), '108.99 mm');
  assert.equal(formatMeasuredMetric(1, 'count'), '1');
  assert.equal(formatMeasuredMetric(null, 'fraction'), 'Unavailable');
});
