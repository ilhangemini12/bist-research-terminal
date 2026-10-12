/* App assets only. Financial data must never enter Cache Storage. */
'use strict';
const BASE = new URL('./', self.registration.scope);
const PREFIX = 'bist-terminal-' + BASE.pathname + '-';
const CACHE = PREFIX + 'v2';
const ASSETS = ['styles.css', 'app.js', 'formula.js', 'research.js', 'install.js',
  'manifest.webmanifest', 'icons/icon.svg', 'icons/icon-192.png', 'icons/icon-512.png'];
const ALLOWED = new Set(ASSETS.map(path => new URL(path, BASE).href));
const OFFLINE = '<!doctype html><html lang="tr"><meta charset="utf-8">' +
  '<meta name="viewport" content="width=device-width,initial-scale=1">' +
  '<title>BIST Terminal — çevrimdışı</title><body style="font:18px system-ui;padding:24px;background:#101827;color:#fff">' +
  '<h1>İnternet bağlantısı gerekli</h1><p>Çevrimdışısınız. Güncel fiyat, finansal veri ve analiz yüklenemedi.</p>' +
  '<p>Önceki veriler güncel veri olarak gösterilmez. Bağlantınız geldiğinde tekrar açın.</p>' +
  '<a href="./" style="color:#56ddba">Yeniden dene</a></body></html>';
self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(ASSETS.map(path => new URL(path, BASE).href)))
    .then(() => self.skipWaiting()));
});
self.addEventListener('activate', event => {
  event.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(key => key.startsWith(PREFIX) && key !== CACHE)
    .map(key => caches.delete(key)))).then(() => self.clients.claim()));
});
self.addEventListener('fetch', event => {
  const request = event.request;
  const url = new URL(request.url);
  if (request.method !== 'GET' || url.origin !== BASE.origin || !url.pathname.startsWith(BASE.pathname)) return;
  // Network only: no cache match or fallback, including cache-busting query strings.
  if (url.pathname.startsWith(new URL('data/', BASE).pathname)) {
    event.respondWith(self.navigator && self.navigator.onLine === false
      ? Promise.reject(new Error('Internet connection required'))
      : fetch(request, {cache: 'no-store'}));
    return;
  }
  if (request.mode === 'navigate') {
    const unavailable = () => new Response(OFFLINE,
      {status: 503, headers: {'Content-Type': 'text/html; charset=utf-8', 'Cache-Control': 'no-store'}});
    event.respondWith(self.navigator && self.navigator.onLine === false
      ? Promise.resolve(unavailable())
      : fetch(request, {cache: 'no-store'}).catch(unavailable));
    return;
  }
  const assetURL = new URL(url);
  assetURL.search = '';
  if (!ALLOWED.has(assetURL.href)) return;
  event.respondWith(fetch(request, {cache: 'no-cache'}).then(response => {
    if (response.ok && response.type !== 'opaque') {
      const copy = response.clone();
      event.waitUntil(caches.open(CACHE).then(cache => cache.put(assetURL.href, copy)));
    }
    return response;
  }).catch(async () => {
    const cached = await caches.match(assetURL.href);
    if (cached) return cached;
    throw new Error('Uygulama dosyası çevrimdışıyken kullanılamıyor');
  }));
});
