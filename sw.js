/* Overhead service worker.
 *
 * Scope: packaging only. It makes the app open and run offline. It never
 * touches, rewrites or caches orbit data -- see the CelesTrak note below.
 *
 * Bump VERSION whenever the app shell changes; old caches are then dropped.
 */
const VERSION = '2026-11-24a';
const SHELL = 'overhead-shell-' + VERSION;
const FONTS = 'overhead-fonts-' + VERSION;
const KEEP = [SHELL, FONTS];

/* Everything needed to open the app with no network at all. index.html is the
 * whole app: the star catalog, Astronomy Engine and satellite.js are inlined
 * in it, so this short list really is the entire offline payload. */
const CORE = [
  './',
  './index.html',
  './manifest.webmanifest',
  './icons/icon-192.png',
  './icons/icon-512.png',
  './icons/icon-maskable-512.png',
  './icons/apple-touch-icon.png',
  './icons/favicon-32.png'
];

const isFont = (url) =>
  url.hostname === 'fonts.googleapis.com' || url.hostname === 'fonts.gstatic.com';

self.addEventListener('install', (e) => {
  e.waitUntil((async () => {
    const cache = await caches.open(SHELL);
    // addAll is all-or-nothing; add one at a time so a single 404 can't leave
    // the app with no offline copy at all.
    await Promise.all(CORE.map(async (u) => {
      try { await cache.add(new Request(u, { cache: 'reload' })); }
      catch (err) { console.warn('[sw] could not precache', u, err); }
    }));
    await self.skipWaiting();
  })());
});

self.addEventListener('activate', (e) => {
  e.waitUntil((async () => {
    const names = await caches.keys();
    await Promise.all(names
      .filter((n) => n.startsWith('overhead-') && !KEEP.includes(n))
      .map((n) => caches.delete(n)));
    await self.clients.claim();
  })());
});

/* Serve from cache at once, refresh in the background for next time. */
async function staleWhileRevalidate(req, cacheName, fallbackReq) {
  const cache = await caches.open(cacheName);
  const cached = await cache.match(req, { ignoreSearch: false })
    || (fallbackReq ? await cache.match(fallbackReq) : undefined);

  const network = fetch(req).then((res) => {
    // Opaque responses (cross-origin fonts) report status 0 but are still usable.
    if (res && (res.ok || res.type === 'opaque')) cache.put(req, res.clone()).catch(() => {});
    return res;
  }).catch(() => undefined);

  if (cached) { network.catch(() => {}); return cached; }
  const res = await network;
  if (res) return res;
  throw new Error('offline and not cached: ' + req.url);
}

self.addEventListener('fetch', (e) => {
  const req = e.request;
  if (req.method !== 'GET') return;

  let url;
  try { url = new URL(req.url); } catch (err) { return; }
  if (url.protocol !== 'http:' && url.protocol !== 'https:') return;

  /* ---- Orbit data is deliberately NOT handled here. ----
   * CelesTrak (and its CORS proxies) go straight to the network, untouched.
   * The app already keeps the last successful download in localStorage with
   * the time it was fetched, and falls back to it when offline. If this
   * worker replayed a cached CelesTrak response instead, the app would stamp
   * it with the current time and report hours-old orbits as fresh. */
  if (/celestrak|allorigins|corsproxy|codetabs/i.test(url.hostname)) return;

  if (isFont(url)) {
    e.respondWith(staleWhileRevalidate(req, FONTS));
    return;
  }

  if (url.origin !== self.location.origin) return;  // anything else: untouched

  // App navigations always resolve to the one page this app has.
  if (req.mode === 'navigate') {
    e.respondWith(staleWhileRevalidate(req, SHELL, './index.html'));
    return;
  }

  e.respondWith(staleWhileRevalidate(req, SHELL));
});
