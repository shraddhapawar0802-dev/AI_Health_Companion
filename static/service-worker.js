/*
 * Deliberately caches only same-origin app-shell files (this page, manifest,
 * icons) — not the third-party CDN scripts (Tesseract.js/pdf.js/jsPDF).
 * That keeps the service worker simple and safe, and it is still an honest
 * offline story: everything that runs on plain inline JS — manual vitals
 * entry, the red-flag/lab explainer, the risk calculator, sample presets,
 * and voice output (Web Speech API is built into the browser) — works with
 * zero network. Only "scan a photo" and "download PDF" need internet once
 * per session, to fetch those CDN libraries.
 */
const CACHE_NAME = 'ahc-shell-v2';
const APP_SHELL = [
  '/',
  '/static/manifest.json',
  '/static/icons/icon-192.png',
  '/static/icons/icon-512.png',
];

// Read-only reference data the prescription scanner needs — safe to serve
// from cache when offline, since it rarely changes and never depends on the
// user's own data.
const CACHEABLE_API_PREFIXES = ['/api/medicines', '/api/interactions-data', '/api/lab-ranges'];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(APP_SHELL))
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // Never intercept cross-origin CDN library fetches (Tesseract.js/pdf.js/
  // jsPDF) — a caching bug here must never be able to break those.
  if (event.request.method !== 'GET' || url.origin !== self.location.origin) {
    return;
  }

  const isCacheableApi = CACHEABLE_API_PREFIXES.some((p) => url.pathname.startsWith(p));
  if (isCacheableApi) {
    // Network-first so the data stays fresh, falling back to the last
    // successful copy when there's no connection to the backend.
    event.respondWith(
      fetch(event.request)
        .then((res) => {
          const clone = res.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
          return res;
        })
        .catch(() => caches.match(event.request))
    );
    return;
  }

  // App shell: cache-first for instant, offline-capable loads. Everything
  // else (including /api/ocr, /api/analyze-vitals, /api/risk-screen) is
  // intentionally left alone here — those need a live backend response.
  event.respondWith(
    caches.match(event.request).then((cached) => cached || fetch(event.request))
  );
});
