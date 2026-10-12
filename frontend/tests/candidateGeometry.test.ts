import assert from 'node:assert/strict';
import test from 'node:test';
import type { ExperimentParameters } from '../types/argus.ts';
import { candidatePanelGeometry, candidateScoreGeometry, sameCandidateExperiment } from '../components/candidateGeometry.ts';

const experiment: ExperimentParameters = { source_x: .1, source_y: .2, receiver_x: .8, receiver_y: .9, frequency_start_hz: 40000, frequency_end_hz: 80000, amplitude: .2, duration_s: .001, waveform: 'chirp' };

test('recommendation marking requires excitation parameters as well as matching endpoints', () => {
  assert.equal(sameCandidateExperiment(experiment, { ...experiment }), true);
  assert.equal(sameCandidateExperiment(experiment, { ...experiment, amplitude: .3 }), false);
  assert.equal(sameCandidateExperiment(experiment, { ...experiment, waveform: 'sine' }), false);
  assert.equal(sameCandidateExperiment(experiment, { ...experiment, spectral_notches_hz: [[42000, 45000]] }), false);
  assert.equal(sameCandidateExperiment({ ...experiment, source_x: NaN }, { ...experiment, source_x: NaN }), false);
});

test('signed comparison bars share a zero axis across negative and positive scores', () => {
  assert.deepEqual(candidateScoreGeometry(-2, [-2, 1, 3]), { zero: 40, left: 0, width: 40, negative: true });
  assert.deepEqual(candidateScoreGeometry(3, [-2, 1, 3]), { zero: 40, left: 40, width: 60, negative: false });
  assert.deepEqual(candidateScoreGeometry(-1, [-2, -1]), { zero: 100, left: 50, width: 50, negative: true });
  assert.deepEqual(candidateScoreGeometry(0, [0, 0]), { zero: 0, left: 0, width: 0, negative: false });
});

test('candidate geometry preserves physical aspect for both landscape and portrait panels', () => {
  for (const [widthMm, heightMm] of [[1200, 300], [300, 1200]]) {
    const panel = candidatePanelGeometry(widthMm, heightMm, 430, 236, 40)!;
    assert.ok(Math.abs(panel.width / panel.height - widthMm / heightMm) < 1e-10);
    assert.ok(panel.x >= 40 && panel.y >= 40);
    assert.ok(panel.x + panel.width <= 390 && panel.y + panel.height <= 196);
  }
  assert.equal(candidatePanelGeometry(0, 300, 430, 236, 40), null);
});
