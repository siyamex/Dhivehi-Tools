/* Dhivehi Tools service worker.
 * HTML: network-first (so UI updates always appear; cache is the offline
 * fallback). Static assets (js/font/icon): cache-first. API: never cached. */
var CACHE = "dhivehi-tools-v2";
var SHELL = ["/", "/dhivehi.js", "/fonts/mvtyper.ttf", "/icon.svg",
             "/manifest.json"];

self.addEventListener("install", function (e) {
  e.waitUntil(
    caches.open(CACHE).then(function (c) { return c.addAll(SHELL); })
      .then(function () { return self.skipWaiting(); }));
});

self.addEventListener("activate", function (e) {
  e.waitUntil(caches.keys().then(function (keys) {
    return Promise.all(keys.filter(function (k) { return k !== CACHE; })
      .map(function (k) { return caches.delete(k); }));
  }).then(function () { return self.clients.claim(); }));
});

self.addEventListener("fetch", function (e) {
  var url = new URL(e.request.url);
  if (e.request.method !== "GET" ||
      url.pathname.indexOf("/api/") === 0 || url.pathname === "/v2/check")
    return;                                    // API: always network

  var isHTML = e.request.mode === "navigate" ||
               url.pathname === "/" || url.pathname === "/index.html";

  if (isHTML) {
    // network-first: fresh UI whenever the server is reachable
    e.respondWith(
      fetch(e.request).then(function (resp) {
        var copy = resp.clone();
        caches.open(CACHE).then(function (c) { c.put(e.request, copy); });
        return resp;
      }).catch(function () { return caches.match(e.request); }));
  } else {
    // cache-first for immutable-ish assets
    e.respondWith(
      caches.match(e.request).then(function (hit) {
        return hit || fetch(e.request).then(function (resp) {
          if (resp.ok) {
            var copy = resp.clone();
            caches.open(CACHE).then(function (c) { c.put(e.request, copy); });
          }
          return resp;
        });
      }));
  }
});
