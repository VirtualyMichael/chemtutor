// ChemTutor service worker: lets the phone app open instantly and keep the cheat sheet offline.
// Progress, problems and the tutor always come live from your computer, so nothing here can show stale answers.
const CACHE = "chemtutor-v1";
const OFFLINE = `<!doctype html><meta name=viewport content="width=device-width,initial-scale=1"><title>ChemTutor</title>
<body style="font:16px system-ui;max-width:30em;margin:14vh auto;padding:0 20px;text-align:center">
<h2>Can't reach your computer</h2>
<p>ChemTutor needs your computer to be on, running ChemTutor, and (away from home) connected to Tailscale.</p>
<p><button onclick="location.reload()" style="font:inherit;padding:10px 18px">Try again</button></p>`;

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.add("/")).catch(() => {}).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys().then((ks) => Promise.all(ks.filter((k) => k !== CACHE).map((k) => caches.delete(k)))).then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (e) => {
  const req = e.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.origin !== location.origin) return;

  if (req.mode === "navigate") {
    // network first so updates show up; fall back to the last copy of the app, then a plain message
    e.respondWith(
      fetch(req)
        .then((res) => {
          if (res.ok && url.pathname === "/") {
            const copy = res.clone();
            caches.open(CACHE).then((c) => c.put("/", copy));
          }
          return res;
        })
        .catch(() => caches.match("/").then((hit) => hit || new Response(OFFLINE, { headers: { "Content-Type": "text/html; charset=utf-8" } })))
    );
    return;
  }

  if (url.pathname === "/api/reference") {
    // the cheat sheet never changes between releases: answer from cache, refresh in the background
    e.respondWith(
      caches.open(CACHE).then((c) =>
        c.match(req).then((hit) => {
          const live = fetch(req).then((res) => {
            if (res.ok) c.put(req, res.clone());
            return res;
          });
          return hit || live;
        })
      )
    );
  }
});
