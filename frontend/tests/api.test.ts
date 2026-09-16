import assert from 'node:assert/strict';
import test from 'node:test';

import { argusApi, resolveApiUrl } from '../services/api.ts';

test('local API URL follows the browser hostname for phone and LAN clients', () => {
  assert.equal(resolveApiUrl(undefined, '10.186.241.130'), 'http://10.186.241.130:8000');
  assert.equal(resolveApiUrl(undefined, 'localhost'), 'http://localhost:8000');
  assert.equal(resolveApiUrl(undefined, undefined), 'http://127.0.0.1:8000');
});

test('an explicit API URL overrides hostname discovery and removes trailing slashes', () => {
  assert.equal(resolveApiUrl('https://argus.example/api///', '10.0.0.5'), 'https://argus.example/api');
});

test('session creation preserves panel dimensions and explicit research opt-in', async (context) => {
  const requests: RequestInit[] = [];
  context.mock.method(globalThis, 'fetch', async (_url: string, options: RequestInit) => {
    requests.push(options);
    return Response.json({ id: 'unit-test' });
  });
  await argusApi.createSession('hard', 17, 'simulation', 800, 300, true);
  await argusApi.createSession('easy');
  const requested = JSON.parse(String(requests[0].body));
  assert.equal(requested.enable_nuisance_aware_design, true);
  assert.equal(requested.panel_width_mm, 800);
  assert.equal(requested.panel_height_mm, 300);
  assert.equal(requested.seed, 17);
  assert.equal(JSON.parse(String(requests[1].body)).enable_nuisance_aware_design, false);
});

test('health checks forward cancellation and validation errors remain actionable', async (context) => {
  const controller = new AbortController();
  let receivedSignal: AbortSignal | null | undefined;
  context.mock.method(globalThis, 'fetch', async (_url: string, options: RequestInit) => {
    receivedSignal = options.signal;
    return Response.json({ detail: [{ loc: ['body', 'panel_width_mm'], msg: 'must be positive' }] }, { status: 422 });
  });
  await assert.rejects(argusApi.health(controller.signal), /panel_width_mm: must be positive/);
  assert.equal(receivedSignal, controller.signal);
});
