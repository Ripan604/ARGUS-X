import assert from 'node:assert/strict';
import test from 'node:test';

import { resolveApiUrl } from '../services/api.ts';

test('local API URL follows the browser hostname for phone and LAN clients', () => {
  assert.equal(resolveApiUrl(undefined, '10.186.241.130'), 'http://10.186.241.130:8000');
  assert.equal(resolveApiUrl(undefined, 'localhost'), 'http://localhost:8000');
  assert.equal(resolveApiUrl(undefined, undefined), 'http://127.0.0.1:8000');
});

test('an explicit API URL overrides hostname discovery and removes trailing slashes', () => {
  assert.equal(resolveApiUrl('https://argus.example/api///', '10.0.0.5'), 'https://argus.example/api');
});
