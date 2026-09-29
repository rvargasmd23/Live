const CACHE='mastertv-v1';
self.addEventListener('install',e=>e.waitUntil(caches.open(CACHE).then(c=>c.addAll(['./','styles.css','app.js','manifest.webmanifest']))));
self.addEventListener('fetch',e=>{if(e.request.url.includes('/output/')||e.request.url.includes('.m3u8'))return; e.respondWith(caches.match(e.request).then(r=>r||fetch(e.request)))})
