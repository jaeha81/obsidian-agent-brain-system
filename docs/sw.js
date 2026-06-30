const CACHE = 'bucky-v3';
const STATIC = [
  '/offline.html',
  '/manifest.json',
  '/icons/icon-192.svg',
  '/icons/icon-512.svg',
  '/icons/icon-maskable.svg',
];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(STATIC)));
  self.skipWaiting();
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);
  if (url.origin !== self.location.origin) return;

  // Network-first for HTML pages — keeps data fresh
  if (e.request.mode === 'navigate' || url.pathname.endsWith('.html') || url.pathname === '/') {
    e.respondWith(
      fetch(e.request)
        .then(res => {
          const clone = res.clone();
          caches.open(CACHE).then(c => c.put(e.request, clone));
          return res;
        })
        .catch(() =>
          caches.match(e.request).then(hit => hit || caches.match('/offline.html'))
        )
    );
    return;
  }

  // Cache-first only for immutable static assets
  if (/\.(svg|png|jpg|jpeg|ico|css|woff2?)$/.test(url.pathname)) {
    e.respondWith(
      caches.match(e.request).then(hit => {
        if (hit) return hit;
        return fetch(e.request).then(res => {
          const clone = res.clone();
          caches.open(CACHE).then(c => c.put(e.request, clone));
          return res;
        });
      })
    );
    return;
  }

  // Everything else (APIs like /os/*, live JSON) — network only, never cached.
  // Caching these replayed stale multi-MB graph payloads and bypassed
  // the server's Cache-Control: no-store.
});
