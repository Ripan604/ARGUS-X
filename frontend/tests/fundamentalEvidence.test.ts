import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import { parseFundamentalReport } from '../utils/fundamentalEvidence.ts';

const saved = () => JSON.parse(readFileSync(new URL('../public/research/fundamental-summary.json', import.meta.url), 'utf8'));

test('missing fundamental records do not become plausible zero metrics', () => {
  for (const value of [undefined, null, [], {}, { schema_version: 1 }]) assert.equal(parseFundamentalReport(value), null);
});

test('invalid errors, counts, units and alert denominators are refused', () => {
  assert.ok(parseFundamentalReport(saved()));
  const mutations = [
    (value: ReturnType<typeof saved>) => { value.confirmation.adaptive[0].mean_error_mm = NaN; },
    (value: ReturnType<typeof saved>) => { value.confirmation.adaptive[0].mean_error_mm = -1; },
    (value: ReturnType<typeof saved>) => { value.confirmation.adaptive[0].mean_error_mm = '161.2'; },
    (value: ReturnType<typeof saved>) => { value.confirmation.model_order_trajectories = 864.5; },
    (value: ReturnType<typeof saved>) => { value.confirmation.adaptive[0].damage_alerts = 9; },
    (value: ReturnType<typeof saved>) => { value.confirmation.adaptive[0].healthy_alerts = 3; },
    (value: ReturnType<typeof saved>) => { value.healthy_reference.unit = 'mm'; },
    (value: ReturnType<typeof saved>) => { value.healthy_reference.after_di = Infinity; },
    (value: ReturnType<typeof saved>) => { value.healthy_reference.after_di = 1.1; },
    (value: ReturnType<typeof saved>) => { value.qualified_paths = 67; },
    (value: ReturnType<typeof saved>) => { value.confirmation_acquired_banks = 28; },
    (value: ReturnType<typeof saved>) => { value.confirmation.minimum_reference_rank = 0; },
  ];
  for (const mutate of mutations) { const value = saved(); mutate(value); assert.equal(parseFundamentalReport(value), null); }
});

test('malformed provenance and unsupported qualification claims cannot render as verified', () => {
  assert.ok(parseFundamentalReport(saved()));
  const mutations = [
    (value: ReturnType<typeof saved>) => { delete value.confirmation; },
    (value: ReturnType<typeof saved>) => { value.sources_verified_at_export = false; },
    (value: ReturnType<typeof saved>) => { value.hardware_validated = true; },
    (value: ReturnType<typeof saved>) => { value.field_accuracy_established = true; },
    (value: ReturnType<typeof saved>) => { value.artifacts[0].source_verification.matches_at_export = false; },
    (value: ReturnType<typeof saved>) => { value.artifacts[0].sha256 = 'unverified'; },
    (value: ReturnType<typeof saved>) => { value.artifacts[0].path = '../private.json'; },
    (value: ReturnType<typeof saved>) => { value.source_url = 'javascript:alert(1)'; },
    (value: ReturnType<typeof saved>) => { value.confirmation.previously_seen_data = true; },
    (value: ReturnType<typeof saved>) => { value.artifacts[1].role = 'healthy'; },
    (value: ReturnType<typeof saved>) => { value.exported_at_utc = 'unknown'; },
  ];
  for (const mutate of mutations) { const value = saved(); mutate(value); assert.equal(parseFundamentalReport(value), null); }
});
