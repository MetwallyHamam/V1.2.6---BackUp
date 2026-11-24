const CACHE = "support-assistant-shell-v3";
const BASE = "/SupportHub/";
const ASSISTANT = `${BASE}support-assistant-app`;
const SHELL = [ASSISTANT, `${BASE}manifest.webmanifest`, `${BASE}support-hub-login.webp`];

self.addEventListener("install", event => {
  event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", event => {
  event.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(key => key !== CACHE).map(key => caches.delete(key)))).then(() => self.clients.claim()));
});

self.addEventListener("fetch", event => {
  const request = event.request;
  if (request.method !== "GET") return;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin || url.pathname.includes("/backend/api/")) return;
  if (request.mode === "navigate") {
    if (!url.pathname.startsWith(ASSISTANT)) return;
    event.respondWith(fetch(request).then(response => {
      const copy = response.clone();
      void caches.open(CACHE).then(cache => cache.put(request, copy));
      return response;
    }).catch(() => caches.match(request).then(cached => cached || caches.match(ASSISTANT)).then(response => response || Response.error())));
    return;
  }
  event.respondWith(caches.match(request).then(cached => cached || fetch(request).then(response => {
    if (response.ok) {
      const copy = response.clone();
      void caches.open(CACHE).then(cache => cache.put(request, copy));
    }
    return response;
  })));
});
