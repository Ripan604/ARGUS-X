import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { mkdir, mkdtemp, realpath, rm } from 'node:fs/promises';
import { basename, dirname, isAbsolute, relative, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import test from 'node:test';
import { build } from 'esbuild';
import { JSDOM } from 'jsdom';
import React, { act } from 'react';
import { renderToString } from 'react-dom/server';

const frontendRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const require = createRequire(import.meta.url);

test('landing hydrates its actual server markup before browser storage and engine health update it', async (context) => {
  await mkdir(resolve(frontendRoot, '../tmp'), { recursive: true });
  const temporaryRoot = await mkdtemp(resolve(frontendRoot, '../tmp/hydration-test-'));
  let root: import('react-dom/client').Root | undefined;
  let dom: JSDOM | undefined;
  const previousGlobals = new Map<string, PropertyDescriptor | undefined>();
  const globals: Record<string, unknown> = {};
  try {
    const bundlePath = resolve(temporaryRoot, 'landing.cjs');
    await build({
      stdin: {
        contents: "export {default as Home} from './app/page.tsx'; export {SpatialWorld} from './components/SpatialWorld.tsx';",
        resolveDir: frontendRoot,
        sourcefile: 'landing-hydration-entry.tsx',
        loader: 'tsx',
      },
      bundle: true,
      platform: 'node',
      format: 'cjs',
      outfile: bundlePath,
      loader: { '.css': 'empty' },
      plugins: [{
        name: 'shared-react-runtime',
        setup(builder) {
          builder.onResolve({ filter: /^react(?:\/.*)?$|^react-dom(?:\/.*)?$/ }, (args) => ({
            path: require.resolve(args.path), external: true,
          }));
        },
      }],
    });
    const { Home, SpatialWorld } = require(bundlePath) as {
      Home: React.ComponentType;
      SpatialWorld: React.ComponentType<{ children?: React.ReactNode }>;
    };
    const element = React.createElement(SpatialWorld, null, React.createElement(Home));
    const html = renderToString(element);
    assert.match(html, /Connecting to engine/);
    assert.doesNotMatch(html, /Resume last session/);

    dom = new JSDOM(`<div id="root">${html}</div>`, { url: 'http://localhost:5173/', pretendToBeVisual: true });
    const window = dom.window;
    window.localStorage.setItem('argus_last_session', 'previous-session');
    let resolveHealth: (response: Response) => void = () => { throw new Error('Health request was not started'); };
    const health = new Promise<Response>((resolveResponse) => { resolveHealth = resolveResponse; });
    const errors: unknown[] = [];
    context.mock.method(console, 'error', (...args: unknown[]) => { errors.push(args); });
    context.mock.method(window.HTMLCanvasElement.prototype, 'getContext', () => null);
    Object.assign(globals, {
      window,
      document: window.document,
      navigator: window.navigator,
      HTMLElement: window.HTMLElement,
      HTMLCanvasElement: window.HTMLCanvasElement,
      Event: window.Event,
      Node: window.Node,
      requestAnimationFrame: () => 0,
      cancelAnimationFrame: () => {},
      matchMedia: () => ({ matches: false, addEventListener() {}, removeEventListener() {} }),
      fetch: async () => health,
      IS_REACT_ACT_ENVIRONMENT: true,
    });
    for (const [key, value] of Object.entries(globals)) {
      previousGlobals.set(key, Object.getOwnPropertyDescriptor(globalThis, key));
      Object.defineProperty(globalThis, key, { configurable: true, writable: true, value });
    }
    const container = window.document.getElementById('root');
    assert.ok(container);
    const { hydrateRoot } = await import('react-dom/client');
    await act(async () => {
      root = hydrateRoot(container, element, { onRecoverableError: (error) => { errors.push(error); } });
    });
    await act(async () => { await new Promise((resolveTimer) => setTimeout(resolveTimer, 10)); });
    assert.match(container.textContent ?? '', /Resume last session/);
    assert.match(container.textContent ?? '', /Connecting to engine/);
    await act(async () => {
      resolveHealth(Response.json({ status: 'ok', service: 'argus' }));
      await health;
    });
    assert.match(container.textContent ?? '', /Local engine online/);
    assert.deepEqual(errors, [], 'Hydration and subsequent effects must produce no React errors');
  } finally {
    if (root) await act(async () => { root?.unmount(); });
    dom?.window.close();
    for (const [key, descriptor] of previousGlobals) {
      if (descriptor) Object.defineProperty(globalThis, key, descriptor);
      else Reflect.deleteProperty(globalThis, key);
    }
    const intendedTemporaryRoot = await realpath(resolve(frontendRoot, '../tmp'));
    const resolvedTemporaryRoot = await realpath(temporaryRoot);
    const generatedDirectory = relative(intendedTemporaryRoot, resolvedTemporaryRoot);
    assert.ok(generatedDirectory && !isAbsolute(generatedDirectory) && !generatedDirectory.startsWith('..'));
    assert.equal(dirname(resolvedTemporaryRoot), intendedTemporaryRoot);
    assert.ok(basename(resolvedTemporaryRoot).startsWith('hydration-test-'));
    await rm(resolvedTemporaryRoot, { recursive: true, force: true });
  }
});
