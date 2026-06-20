// 最小限のサービスワーカー。静的ファイルは stale-while-revalidate、
// API（/api）はキャッシュせず常にネットワークから取得する。
const CACHE = 'stock-pulse-v1'

self.addEventListener('install', () => {
  self.skipWaiting()
})

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))),
  )
  self.clients.claim()
})

self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url)
  // GET 以外・API・同一オリジン以外はそのまま通す
  if (event.request.method !== 'GET' || url.pathname.startsWith('/api') || url.origin !== self.location.origin) {
    return
  }
  event.respondWith(
    caches.open(CACHE).then(async (cache) => {
      const cached = await cache.match(event.request)
      const network = fetch(event.request)
        .then((res) => {
          if (res && res.status === 200) cache.put(event.request, res.clone())
          return res
        })
        .catch(() => cached)
      return cached || network
    }),
  )
})
