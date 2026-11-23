// Jarvis v1 abgeschaltet: dieser Service Worker löscht den alten Offline-Cache und meldet sich ab.
self.addEventListener('install',()=>self.skipWaiting());
self.addEventListener('activate',e=>{e.waitUntil(caches.keys().then(k=>Promise.all(k.map(c=>caches.delete(c)))).then(()=>self.registration.unregister()).then(()=>self.clients.matchAll()).then(l=>l.forEach(c=>c.navigate(c.url))))});
