/* Bucky Voice PWA — Service Worker */
const CACHE = 'bucky-voice-v1';
const SHELL = ['/bucky-voice.html', '/bucky-voice-manifest.json'];

self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open(CACHE).then(c => c.addAll(SHELL)).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (e) => {
  const url = new URL(e.request.url);

  // API calls — network only, no cache
  if (url.pathname.startsWith('/chat') || url.pathname.startsWith('/health')) {
    return;
  }

  // App shell — cache-first
  if (SHELL.includes(url.pathname) || url.pathname === '/') {
    e.respondWith(
      caches.match(e.request).then(cached => {
        if (cached) {
          // Refresh cache in background
          fetch(e.request).then(r => {
            if (r.ok) caches.open(CACHE).then(c => c.put(e.request, r));
          }).catch(() => {});
          return cached;
        }
        return fetch(e.request).then(r => {
          if (r.ok) {
            const clone = r.clone();
            caches.open(CACHE).then(c => c.put(e.request, clone));
          }
          return r;
        });
      })
    );
  }
});
