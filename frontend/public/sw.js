/* LodgeFlow service worker: app shell/public content only. Private /api data is deliberately NOT cached here. */
const VERSION = 'lodgeflow-shell-v4';
const STATIC = `${VERSION}-static`;
const PUBLIC = `${VERSION}-public`;
const SHELL = ['/', '/login', '/offline', '/manifest.webmanifest'];
self.addEventListener('install', event => {
  event.waitUntil(caches.open(STATIC).then(cache => cache.addAll(SHELL)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', event => {
  event.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(k => !k.startsWith(VERSION)).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});
async function networkFirst(request, cacheName, fallback) {
  const cache = await caches.open(cacheName);
  try {
    const response = await fetch(request);
    if (response.ok) cache.put(request, response.clone());
    return response;
  } catch {
    return (await cache.match(request)) || (fallback ? await caches.match(fallback) : Response.error());
  }
}
self.addEventListener('fetch', event => {
  const req = event.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;
  if (url.pathname.startsWith('/api/') && !url.pathname.startsWith('/api/public/')) return; // private API lives in encrypted IndexedDB via the app, never CacheStorage
  if (url.pathname.startsWith('/_next/static/')) {
    event.respondWith(caches.open(STATIC).then(async cache => (await cache.match(req)) || fetch(req).then(r => { if (r.ok) cache.put(req, r.clone()); return r; })));
    return;
  }
  if (url.pathname.startsWith('/api/public/')) {
    event.respondWith(networkFirst(req, PUBLIC));
    return;
  }
  if (req.mode === 'navigate') {
    event.respondWith(networkFirst(req, STATIC, '/offline'));
  }
});
self.addEventListener('message', event => {
  if (event.data?.type === 'SKIP_WAITING') self.skipWaiting();
  if (event.data?.type === 'PURGE_SHELL') event.waitUntil(caches.keys().then(keys => Promise.all(keys.map(k => caches.delete(k)))));
});
