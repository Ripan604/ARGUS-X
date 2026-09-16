import assert from 'node:assert/strict';
import test from 'node:test';
import { readNuisanceDesign } from '../utils/researchDesign.ts';

const payload = {
  method: 'nuisance_marginal_arrival_time', information_bits: 0.41,
  normalized_information: 0.205, nuisance_penalty_bits: 0.23,
  quadrature_error_bits: 0.002, region_count: 4, posterior_mass: 1,
};

test('research readout preserves information units and supplied measurements', () => {
  assert.deepEqual(readNuisanceDesign(payload), {
    method: payload.method, informationBits: 0.41, normalizedInformation: 0.205,
    nuisancePenaltyBits: 0.23, quadratureErrorBits: 0.002, regionCount: 4, posteriorMass: 1,
  });
});

test('legacy sessions and malformed diagnostics do not produce fabricated zero readouts', () => {
  for (const value of [undefined, null, [], {}, { ...payload, information_bits: '0.41' },
    { ...payload, information_bits: NaN }, { ...payload, quadrature_error_bits: Infinity },
    { ...payload, normalized_information: 1.2 }, { ...payload, region_count: 1.5 },
    { ...payload, posterior_mass: 0 }, { ...payload, posterior_mass: 1.02 }]) {
    assert.equal(readNuisanceDesign(value), null);
  }
});

test('roundoff in posterior mass is tolerated; signed nuisance effects are not hidden', () => {
  assert.equal(readNuisanceDesign({ ...payload, posterior_mass: 1 + 1e-12 })?.posteriorMass, 1);
  assert.equal(readNuisanceDesign({ ...payload, nuisance_penalty_bits: -0.01 })?.nuisancePenaltyBits, -0.01);
});
