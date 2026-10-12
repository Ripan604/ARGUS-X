import assert from 'node:assert/strict';
import test from 'node:test';

import { argusApi, resolveApiUrl, setApiToken, getWebSocketProtocols } from '../services/api.ts';

test('local API URL follows the browser hostname for phone and LAN clients', () => {
  assert.equal(resolveApiUrl(undefined, '10.186.241.130'), 'http://10.186.241.130:8000');
  assert.equal(resolveApiUrl(undefined, 'localhost'), 'http://localhost:8000');
  assert.equal(resolveApiUrl(undefined, undefined), 'http://127.0.0.1:8000');
});

test('research polling forwards cancellation without changing mutation requests', async (context) => {
  const controller = new AbortController();
  let signal: AbortSignal | null | undefined;
  context.mock.method(globalThis, 'fetch', async (_url: string, options: RequestInit) => {
    signal = options.signal;
    return Response.json({ jobs: [] });
  });
  assert.deepEqual(await argusApi.jobs(controller.signal), { jobs: [] });
  assert.equal(signal, controller.signal);
});

test('an explicit API URL overrides hostname discovery and removes trailing slashes', () => {
  assert.equal(resolveApiUrl('https://argus.example/api///', '10.0.0.5'), 'https://argus.example/api');
});

test('custom API ports preserve LAN host discovery', () => {
  assert.equal(resolveApiUrl(undefined, '10.0.0.2', '8001'), 'http://10.0.0.2:8001');
  assert.throws(() => resolveApiUrl(undefined, 'localhost', 'invalid'), /Invalid ARGUS API port/);
});

test('a different application health endpoint cannot appear as ARGUS online', async (context) => {
  context.mock.method(globalThis, 'fetch', async () => Response.json({ status: 'ok', service: 'another_app' }));
  await assert.rejects(argusApi.health(), /another application/);
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

test('API addresses reject embedded credentials and non-http protocols', () => {
  assert.throws(() => resolveApiUrl('https://secret@argus.example',undefined), /without URL credentials/);
  assert.throws(() => resolveApiUrl('javascript:alert(1)',undefined), /HTTP/);
  assert.equal(resolveApiUrl(undefined,'::1'),'http://[::1]:8000');
});

test('shared-engine authentication uses headers and WebSocket protocols, never URL tokens', async (context) => {
  const storage = new Map<string,string>();
  const fakeWindow = { location: { hostname:'localhost' }, sessionStorage: {
    getItem:(key:string) => storage.get(key) || null,
    setItem:(key:string,value:string) => storage.set(key,value),
    removeItem:(key:string) => storage.delete(key),
  } };
  Object.defineProperty(globalThis,'window',{value:fakeWindow,configurable:true});
  try {
    const key='a'.repeat(40);
    setApiToken(key);
    let header='';
    let requested='';
    context.mock.method(globalThis,'fetch',async (url: string,init:RequestInit) => {
      requested=String(url);header=new Headers(init.headers).get('Authorization') || '';
      return Response.json({jobs:[]});
    });
    await argusApi.jobs();
    assert.equal(header,`Bearer ${key}`);
    assert.ok(!requested.includes(key));
    assert.deepEqual(getWebSocketProtocols(),['argus',`argus-token.${key}`]);
    assert.throws(() => setApiToken('short'), /complete access key/);
    setApiToken('');
    await argusApi.jobs();
    assert.equal(header,'');
    assert.equal(storage.size,0);
  } finally {
    Reflect.deleteProperty(globalThis,'window');
  }
});
