'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.join(__dirname, '..', 'dashboard');
const scope = 'https://example.github.io/bist-research-terminal/';
function worker(fetchImpl) {
  const handlers = {}, accesses = [];
  const cache = {addAll: async urls => accesses.push(['addAll', urls]), put: async (...args) => accesses.push(['put', args])};
  const context = {URL, Response, Set, Promise, Error,
    fetch: fetchImpl,
    self: {registration: {scope}, addEventListener: (name, fn) => handlers[name] = fn,
      skipWaiting: async () => {}, clients: {claim: async () => {}}},
    caches: {open: async () => cache, keys: async () => [], delete: async () => true,
      match: async request => {accesses.push(['match', request.url]); return new Response('cached asset');}}};
  vm.runInNewContext(fs.readFileSync(path.join(root, 'sw.js'), 'utf8'), context);
  const request = (relative, mode = 'cors') => {
    const pending = [];
    let result;
    handlers.fetch({request: {url: new URL(relative, scope).href, method: 'GET', mode},
      respondWith: promise => result = promise, waitUntil: promise => pending.push(promise)});
    return {result, pending};
  };
  return {handlers, accesses, request};
}
test('manifest uses scoped start URL and present install icons', () => {
  const manifest = JSON.parse(fs.readFileSync(path.join(root, 'manifest.webmanifest')));
  assert.equal(manifest.start_url, './');
  assert.equal(manifest.scope, './');
  assert.equal(manifest.display, 'standalone');
  for (const icon of manifest.icons) assert.ok(fs.statSync(path.join(root, icon.src)).size > 0);
});
test('precache contains static assets only; no financial data or snapshot', async () => {
  const w = worker(async () => new Response('ok'));
  let pending;
  w.handlers.install({waitUntil: p => pending = p});
  await pending;
  const urls = w.accesses.find(row => row[0] === 'addAll')[1];
  assert.ok(urls.length > 0);
  for (const url of urls) {
    assert.equal(url.includes('/data/'), false);
    assert.equal(url.endsWith('index.html'), false);
    assert.ok(fs.existsSync(path.join(root, url.slice(scope.length))));
  }
});
test('financial data requests use no-store and never return cached data', async () => {
  const seen = [];
  const w = worker(async (request, options) => {seen.push([request.url, options.cache]); throw new Error('offline');});
  for (const file of ['data/latest.json', 'data/health.json?cache=1', 'data/nested/financials.json']) {
    await assert.rejects(w.request(file).result, /offline/);
  }
  assert.equal(seen.length, 3);
  assert.ok(seen.every(row => row[1] === 'no-store'));
  assert.equal(w.accesses.length, 0);
});
test('offline navigation explicitly reports unavailable current data', async () => {
  const w = worker(async () => {throw new Error('offline');});
  const response = await w.request('./', 'navigate').result;
  assert.equal(response.status, 503);
  assert.match(await response.text(), /Güncel fiyat, finansal veri ve analiz yüklenemedi/);
  assert.equal(w.accesses.length, 0);
});
test('static assets are network-first with offline cache fallback', async () => {
  const online = worker(async () => new Response('fresh asset'));
  const call = online.request('app.js');
  assert.equal(await (await call.result).text(), 'fresh asset');
  await Promise.all(call.pending);
  assert.equal(online.accesses[0][0], 'put');
  const offline = worker(async () => {throw new Error('offline');});
  assert.equal(await (await offline.request('app.js').result).text(), 'cached asset');
});
test('unlisted files and external URLs never enter asset cache', () => {
  const w = worker(async () => new Response('ok'));
  for (const file of ['financials.xlsx', 'secret.json', 'https://other.example/data.json', '../other/app.js']) {
    assert.equal(w.request(file).result, undefined);
  }
  assert.equal(w.accesses.length, 0);
});
test('versioned app scripts reuse static cache keys and never add arbitrary query URLs', async () => {
  const w = worker(async () => new Response('versioned asset'));
  const call = w.request('research.js?v=mobile-v1');
  assert.equal(await (await call.result).text(), 'versioned asset');
  await Promise.all(call.pending);
  assert.equal(w.accesses[0][1][0], new URL('research.js',scope).href);
});
