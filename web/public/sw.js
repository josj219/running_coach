/* 러닝 코치 PWA 서비스 워커 — 셸 precache + 정적 자산 캐시.
   /api/* 는 절대 캐시하지 않는다(항상 네트워크). */
const CACHE = 'coach-shell-v1';
const SHELL = ['/', '/manifest.webmanifest', '/icons/icon-192.png', '/icons/icon-512.png'];

self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== 'GET' || url.pathname.startsWith('/api/')) return;

  if (e.request.mode === 'navigate') {
    // 셸: 네트워크 우선, 오프라인이면 캐시된 '/'
    e.respondWith(fetch(e.request).catch(() => caches.match('/')));
    return;
  }
  // 정적 자산: 캐시 우선 + 백그라운드 갱신
  e.respondWith(
    caches.match(e.request).then((cached) => {
      const fetched = fetch(e.request).then((res) => {
        if (res.ok && url.origin === location.origin) {
          const clone = res.clone();
          caches.open(CACHE).then((c) => c.put(e.request, clone));
        }
        return res;
      }).catch(() => cached);
      return cached || fetched;
    })
  );
});
