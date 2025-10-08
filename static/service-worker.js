const CACHE_NAME = "tool-inventory-cache-v1";
const urlsToCache = [
  "/",
  "/static/style.css",
  "/static/fonts/B-NAZANIN.TTF",
  "/static/icons/icon-192.png",
  "/static/icons/icon-512.png",
  "/static/manifest.json"
];

// نصب Service Worker
self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(urlsToCache);
    })
  );
});

// فعال‌سازی و پاکسازی کش‌های قدیمی
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cache) => {
          if (cache !== CACHE_NAME) {
            return caches.delete(cache);
          }
        })
      );
    })
  );
});

// واکشی فایل‌ها از کش در صورت آفلاین بودن
self.addEventListener("fetch", (event) => {
  event.respondWith(
    caches.match(event.request).then((response) => {
      return response || fetch(event.request);
    })
  );
});
