const CACHE_NAME = 'nutritionvqa-cache-v6';
const ASSETS_TO_CACHE = [
  './',
  './index.html',
  './signin.html',
  './signup.html',
  './css/style.css',
  './css/signin.css',
  './js/app.js',
  './js/auth.js',
  './assets/salad-bowl.png',
  './assets/salad-bowl-dark.png',
  './assets/icon-192.png',
  './assets/icon-512.png'
];

// Install Event: Cache essential assets
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      console.log('[Service Worker] Pre-caching offline asset shell');
      return cache.addAll(ASSETS_TO_CACHE);
    })
  );
  self.skipWaiting();
});

// Activate Event: Cleanup old caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cache) => {
          if (cache !== CACHE_NAME) {
            console.log('[Service Worker] Clearing old cache store', cache);
            return caches.delete(cache);
          }
        })
      );
    })
  );
  self.clients.claim();
});

// Fetch Event: Cache first for static assets, network only for API and OCR uploads
self.addEventListener('fetch', (event) => {
  const requestUrl = new URL(event.request.url);

  // Bypass service worker caching for all API endpoints, auth endpoints, ask, and upload routes
  if (
    requestUrl.pathname.includes('/api/') || 
    requestUrl.pathname.includes('/upload-image') || 
    requestUrl.pathname.includes('/ask') ||
    requestUrl.pathname.includes('/uploads/')
  ) {
    // Network-only strategy for API calls and dynamic assets
    event.respondWith(fetch(event.request));
    return;
  }

  // Cache-first strategy for static assets
  event.respondWith(
    caches.match(event.request).then((cachedResponse) => {
      if (cachedResponse) {
        return cachedResponse;
      }
      
      // Fallback to network fetch if not in pre-cache
      return fetch(event.request).then((networkResponse) => {
        // Cache external static libraries like Google fonts or marked library dynamically
        if (
          networkResponse.status === 200 &&
          (event.request.url.includes('fonts.googleapis.com') ||
           event.request.url.includes('fonts.gstatic.com') ||
           event.request.url.includes('cdn.jsdelivr.net'))
        ) {
          const responseToCache = networkResponse.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(event.request, responseToCache);
          });
        }
        return networkResponse;
      }).catch(() => {
        // Offline fallback for html pages
        if (event.request.headers.get('accept') && event.request.headers.get('accept').includes('text/html')) {
          return caches.match('./index.html');
        }
      });
    })
  );
});
