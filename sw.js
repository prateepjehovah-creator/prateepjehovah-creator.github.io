/* Page shell only. Large books, audio, and video are not cached. */
var CACHE = "neelam-shell-v2";
var PRECACHE = [
  "/",
  "/index.html",
  "/about/",
  "/about/index.html",
  "/contact/",
  "/contact/index.html",
  "/contact/thanks/",
  "/contact/thanks/index.html",
  "/privacy/",
  "/privacy/index.html",
  "/icons/icon-maskable-192.png",
  "/css/style.css",
  "/js/site.js",
  "/manifest.json",
  "/favicon.svg",
  "/feed.xml",
  "/icons/icon-192.png",
  "/icons/icon-512.png",
  "/icons/icon-maskable-512.png",
  "/404.html",
  "/books/uppu-petti/",
  "/books/uppu-petti/index.html",
  "/books/adiyogi/",
  "/books/adiyogi/index.html",
  "/books/bible-to-quran/",
  "/books/bible-to-quran/index.html",
  "/books/peniel/",
  "/books/peniel/index.html",
  "/books/tireless-machine/",
  "/books/tireless-machine/index.html",
  "/books/francisco/",
  "/books/francisco/index.html",
  "/books/haetaron/",
  "/books/haetaron/index.html",
  "/books/hakai/",
  "/books/hakai/index.html",
  "/books/jathikkummi/",
  "/books/jathikkummi/index.html",
  "/books/las-casas-indies/",
  "/books/las-casas-indies/index.html",
  "/books/layali-satih/",
  "/books/layali-satih/index.html",
  "/books/multan/",
  "/books/multan/index.html",
  "/books/prugavin-monastery-prisons/",
  "/books/prugavin-monastery-prisons/index.html",
  "/books/rauschenbusch/",
  "/books/rauschenbusch/index.html",
  "/books/rettaimalai-srinivasan/",
  "/books/rettaimalai-srinivasan/index.html",
  "/books/southern-horrors/",
  "/books/southern-horrors/index.html"
];

self.addEventListener("install", function (event) {
  event.waitUntil(
    caches.open(CACHE).then(function (cache) {
      return cache.addAll(PRECACHE);
    })
  );
  self.skipWaiting();
});

self.addEventListener("activate", function (event) {
  event.waitUntil(
    caches.keys().then(function (keys) {
      return Promise.all(
        keys.filter(function (key) { return key !== CACHE; }).map(function (key) {
          return caches.delete(key);
        })
      );
    })
  );
  self.clients.claim();
});

self.addEventListener("fetch", function (event) {
  var req = event.request;
  if (req.method !== "GET") return;
  var url = new URL(req.url);
  if (url.origin !== self.location.origin) return;
  if (/\.(pdf|mp3|mp4|zip)$/i.test(url.pathname)) return;
  if (req.mode === "navigate") {
    event.respondWith(
      fetch(req).then(function (res) {
        var copy = res.clone();
        caches.open(CACHE).then(function (cache) { cache.put(req, copy); });
        return res;
      }).catch(function () {
        return caches.match(req).then(function (hit) {
          return hit || caches.match("/index.html");
        });
      })
    );
    return;
  }
  event.respondWith(
    caches.match(req).then(function (hit) {
      if (hit) return hit;
      return fetch(req).then(function (res) {
        if (res.ok && /\.(css|js|svg|png|xml|json)$/i.test(url.pathname)) {
          var copy = res.clone();
          caches.open(CACHE).then(function (cache) { cache.put(req, copy); });
        }
        return res;
      });
    })
  );
});
