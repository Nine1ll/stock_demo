const CACHE_NAME = "stock-value-app-v36";
const APP_FILES = [
  "./",
  "./index.html",
  "./methodology.html",
  "./styles.css",
  "./decision_ui_v35.js",
  "./app_main_v35.js",
  "./manifest.webmanifest",
];
const IS_LOCALHOST = self.location.hostname === "localhost" || self.location.hostname === "127.0.0.1";

self.addEventListener("install", (event) => {
  if (IS_LOCALHOST) {
    event.waitUntil(self.skipWaiting());
    return;
  }
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(APP_FILES)).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  if (IS_LOCALHOST) {
    event.waitUntil(
      caches.keys()
        .then((keys) => Promise.all(keys.map((key) => caches.delete(key))))
        .then(() => self.registration.unregister())
    );
    return;
  }
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((key) => key !== CACHE_NAME)
          .map((oldKey) => caches.delete(oldKey))
      )
    ).then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  if (IS_LOCALHOST) return;
  if (event.request.method !== "GET") return;
  const url = new URL(event.request.url);
  if (url.origin !== self.location.origin) return;

  event.respondWith(
    fetch(event.request)
      .then((response) => {
        const cloned = response.clone();
        caches.open(CACHE_NAME).then((cache) => cache.put(event.request, cloned));
        return response;
      })
      .catch(() => caches.match(event.request))
  );
});
