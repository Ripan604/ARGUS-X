import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { mkdir, mkdtemp, readFile, realpath, rm, stat, writeFile } from 'node:fs/promises';
import { basename, dirname, isAbsolute, relative, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { build } from 'esbuild';
import { JSDOM, VirtualConsole } from 'jsdom';

// This runs the live local framework graph in a virtual DOM, not a visual browser.
// Network code loading is restricted to this fixed local frontend origin.
const origin = 'http://localhost:5173';
const frontendRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const workspaceRoot = resolve(frontendRoot, '..');
const temporaryParent = resolve(workspaceRoot, 'tmp');
const maximumDocumentBytes = 2 * 1024 * 1024;
const maximumModuleBytes = 6 * 1024 * 1024;
const maximumTotalBytes = 40 * 1024 * 1024;
const maximumModules = 250;
const fetchActual = globalThis.fetch;
let totalBytes = 0;
let moduleCount = 0;
let engineHealthRequests = 0;
const errors = [];
const originalConsoleError = console.error;
let dom;
let temporaryRoot;

async function fetchText(address, maximumBytes, permittedOrigins = [origin]) {
  const url = new URL(address, origin);
  assert.ok(permittedOrigins.includes(url.origin), 'Hydration checker request escaped its permitted loopback origins');
  assert.equal(url.username + url.password, '', 'URL credentials are forbidden');
  const response = await fetchActual(url, { redirect: 'error', signal: AbortSignal.timeout(15_000) });
  assert.ok(response.ok, `HTTP ${response.status} while loading local framework code`);
  assert.ok(response.body, 'Local response must provide a body');
  const reader = response.body.getReader();
  const chunks = [];
  let bytes = 0;
  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      bytes += value.byteLength;
      totalBytes += value.byteLength;
      assert.ok(bytes <= maximumBytes && totalBytes <= maximumTotalBytes, 'Hydration checker allocation limit exceeded');
      chunks.push(value);
    }
  } finally { await reader.cancel(); }
  return Buffer.concat(chunks).toString('utf8');
}

function recordError(error) {
  const message = error instanceof Error ? `${error.name}: ${error.message}` : String(error);
  // Keep the persisted result small and avoid storing DOM diffs or arbitrary log objects.
  if (errors.length < 30) errors.push(message.split('\n')[0].slice(0, 1000).replaceAll(workspaceRoot, '<workspace>'));
}

try {
  await mkdir(temporaryParent, { recursive: true });
  temporaryRoot = await mkdtemp(resolve(temporaryParent, 'hydration-live-'));
  const html = await fetchText('/', maximumDocumentBytes);
  const virtualConsole = new VirtualConsole();
  virtualConsole.on('jsdomError', recordError);
  console.error = (...args) => { args.forEach(recordError); originalConsoleError(...args); };
  dom = new JSDOM(html, { url: `${origin}/`, runScripts: 'outside-only', pretendToBeVisual: true, virtualConsole });
  const { window } = dom;
  const originalLanding = window.document.querySelector('main.landing-shell');
  const originalScene = window.document.querySelector('.scene-viewport');
  assert.ok(originalLanding && originalScene, 'Live response must be the ARGUS landing page');
  window.addEventListener('error', (event) => recordError(event.error ?? event.message));
  for (const script of window.document.querySelectorAll('script:not([src])')) {
    if (script.textContent.includes('Symbol.for("vinext.navigationRuntime")')) window.eval(script.textContent);
  }
  const runtimeKey = Symbol.for('vinext.navigationRuntime');
  const bootstrap = window[runtimeKey]?.bootstrap.rsc;
  assert.ok(Array.isArray(bootstrap?.rsc) && bootstrap.done, 'Complete inline RSC bootstrap is required');
  const references = [];
  for (const line of bootstrap.rsc.join('').split('\n')) {
    const match = line.match(/^[^:]+:I(.+)$/);
    if (!match) continue;
    const id = JSON.parse(match[1])[0].replace(/\$\$cache=.+$/, '');
    assert.ok(id.startsWith('/') && !id.startsWith('//') && id.length < 2000);
    if (!references.includes(id)) references.push(id);
  }
  assert.ok(references.length > 0 && references.length <= 50, 'Unexpected RSC reference count');
  const hot = { data: {}, accept() {}, dispose() {}, prune() {}, on() {}, off() {}, send() {}, invalidate() {} };
  window.$RefreshReg$ = () => {};
  window.$RefreshSig$ = () => (type) => type;
  window.__vite_plugin_react_preamble_installed__ = true;
  window.HTMLCanvasElement.prototype.getContext = () => null;
  window.scrollTo = () => {};
  Object.assign(globalThis, {
    window, self: window, document: window.document, location: window.location, history: window.history,
    HTMLElement: window.HTMLElement, HTMLCanvasElement: window.HTMLCanvasElement, Node: window.Node,
    Event: window.Event, CustomEvent: window.CustomEvent, MutationObserver: window.MutationObserver,
    $RefreshReg$: window.$RefreshReg$, $RefreshSig$: window.$RefreshSig$,
    requestAnimationFrame: () => 0, cancelAnimationFrame: () => {},
    matchMedia: () => ({ matches: false, addEventListener() {}, removeEventListener() {} }),
    __ARGUS_HYDRATION_HOT__: hot,
    __ARGUS_HYDRATION_ENV__: { DEV: true, PROD: false, BASE_URL: '/', MODE: 'development', SSR: false },
    fetch: async (address, options) => {
      const url = new URL(address, origin);
      assert.ok(!options?.method || options.method === 'GET', 'Mutating runtime requests are forbidden');
      if (url.pathname === '/health') {
        assert.ok(['localhost', '127.0.0.1'].includes(url.hostname) && ['8000', '8001'].includes(url.port));
        assert.ok(!url.search && !url.hash && (!options?.method || options.method === 'GET'));
        engineHealthRequests++;
        return new Response(await fetchText(url.href, 64 * 1024, [url.origin]), { headers: { 'Content-Type': 'application/json' } });
      }
      assert.equal(url.origin, origin, 'Runtime requests are restricted to the local frontend');
      return fetchActual(url, { ...options, redirect: 'error', signal: AbortSignal.timeout(15_000) });
    },
  });
  Object.defineProperty(globalThis, 'navigator', { configurable: true, value: window.navigator });
  globalThis[runtimeKey] = window[runtimeKey];
  globalThis.WebSocket = class {
    static OPEN = 1; static CLOSED = 3; readyState = 1;
    addEventListener() {} removeEventListener() {} send() {} close() {}
  };
  const plugin = {
    name: 'bounded-local-http-modules',
    setup(builder) {
      const resolveLocal = (address, importer = `${origin}/`) => {
        const url = new URL(address, importer);
        assert.equal(url.origin, origin, 'Module import escaped the local frontend');
        return { path: url.href, namespace: 'local-http' };
      };
      builder.onResolve({ filter: /^https?:\/\// }, (args) => resolveLocal(args.path));
      builder.onResolve({ filter: /.*/, namespace: 'local-http' }, (args) => resolveLocal(args.path, args.importer));
      builder.onLoad({ filter: /.*/, namespace: 'local-http' }, async (args) => {
        assert.ok(++moduleCount <= maximumModules, 'Hydration checker module limit exceeded');
        const url = new URL(args.path);
        if (url.pathname === '/@vite/client') return { contents: 'export const createHotContext=()=>globalThis.__ARGUS_HYDRATION_HOT__;export const updateStyle=()=>{};export const removeStyle=()=>{};export const injectQuery=url=>url;', loader: 'js' };
        if (url.pathname.endsWith('.css')) return { contents: 'export default {};', loader: 'js' };
        let contents = (await fetchText(args.path, maximumModuleBytes)).replace(/\n\/\/# sourceMappingURL=data:[\s\S]*$/, '');
        contents = contents.replaceAll('import.meta.hot', 'globalThis.__ARGUS_HYDRATION_HOT__')
          .replaceAll('import.meta.env', 'globalThis.__ARGUS_HYDRATION_ENV__').replaceAll('import.meta.url', JSON.stringify(args.path));
        // Same wire decoder and module exports; only browser native dynamic loading changes.
        contents = contents.replace(/(?:__vite_rsc_raw_import__|import)\(withTrailingSlash\(globalThis\.__ARGUS_HYDRATION_ENV__\.BASE_URL\) \+ id\.slice\(1\)\)/g, 'globalThis.__ARGUS_HYDRATION_IMPORT__(id)');
        return { contents, loader: 'js' };
      });
    },
  };
  const entry = references.map((id, index) => `import * as ref${index} from ${JSON.stringify(origin + id)};`).join('\n')
    + '\nconst refs={' + references.map((id, index) => `${JSON.stringify(id)}:ref${index}`).join(',') + '};'
    + '\nglobalThis.__ARGUS_HYDRATION_IMPORT__=async id=>{if(!refs[id])throw new Error("Unknown RSC client reference");return refs[id];};'
    + `\nawait import(${JSON.stringify(`${origin}/@id/__x00__virtual:vite-rsc/entry-browser`)});`;
  const bundlePath = resolve(temporaryRoot, 'live-graph.mjs');
  await build({ stdin: { contents: entry, loader: 'js', sourcefile: 'local-hydration-entry.js' }, bundle: true, format: 'esm', platform: 'browser', outfile: bundlePath, plugins: [plugin], logLevel: 'error' });
  process.on('unhandledRejection', recordError);
  await import(pathToFileURL(bundlePath).href);
  await new Promise((resolveTimer) => setTimeout(resolveTimer, 1500));
  const sourceFiles = ['package.json', 'package-lock.json', 'app/page.tsx', 'app/layout.tsx', 'app/globals.css', 'components/SpatialWorld.tsx', 'components/SpatialScene.tsx', 'components/spatial-scene.css', 'components/landing-aesthetic.css', 'hooks/useArgusSession.ts', 'tests/hydration.test.ts', 'scripts/check-hydration-live.mjs'];
  const sources = {};
  for (const file of sourceFiles) {
    const path = resolve(frontendRoot, file);
    sources[`frontend/${file}`] = { sha256: createHash('sha256').update(await readFile(path)).digest('hex'), modifiedAt: (await stat(path)).mtime.toISOString() };
  }
  const result = {
    verification: 'Live Vinext/RSC integration in jsdom; no visual browser verification',
    checkedAt: new Date().toISOString(), route: '/', status: window.__VINEXT_RSC_BOOTSTRAP_STATE__,
    moduleCount, clientReferenceCount: references.length,
    landingDOMPreserved: window.document.querySelector('main.landing-shell') === originalLanding,
    sceneDOMPreserved: window.document.querySelector('.scene-viewport') === originalScene,
    engineHealthFixture: false, engineHealthRequests, engineStatus: window.document.querySelector('.system-state')?.textContent,
    browserAPIMocks: ['Vite HMR and WebSocket', 'CSS import application', 'Canvas drawing', 'Animation frames', 'Reduced-motion media query'],
    sourceFingerprintScope: 'Selected landing code, styles, hydration checks and dependency manifests',
    errors, sources,
  };
  result.passed = result.status === 'hydrated' && result.landingDOMPreserved && result.sceneDOMPreserved && errors.length === 0;
  const outputRoot = resolve(workspaceRoot, 'output/release');
  await mkdir(outputRoot, { recursive: true });
  await writeFile(resolve(outputRoot, 'hydration-live-2026-10-12.json'), JSON.stringify(result, null, 2) + '\n');
  assert.equal(result.status, 'hydrated');
  assert.ok(result.landingDOMPreserved && result.sceneDOMPreserved, 'Hydration replaced the server DOM');
  assert.deepEqual(errors, [], 'Live framework hydration must produce no React/runtime errors');
  console.log(`Live virtual DOM hydration passed: ${moduleCount} modules, ${references.length} client references, original landing and scene DOM preserved.`);
} catch (error) {
  originalConsoleError(error);
  process.exitCode = 1;
} finally {
  dom?.window.__VINEXT_RSC_ROOT__?.unmount();
  dom?.window.close();
  console.error = originalConsoleError;
  if (temporaryRoot) {
    const intendedRoot = await realpath(temporaryParent);
    const target = await realpath(temporaryRoot);
    const child = relative(intendedRoot, target);
    assert.ok(child && !isAbsolute(child) && !child.startsWith('..'));
    assert.equal(dirname(target), intendedRoot);
    assert.ok(basename(target).startsWith('hydration-live-'));
    await rm(target, { recursive: true, force: true });
  }
}
