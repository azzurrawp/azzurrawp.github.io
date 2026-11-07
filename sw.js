const C='azzurrawp-v26';const F=['./','index.html','manifest.webmanifest','icon-192.png','icon-512.png','icon-mask-192.png','icon-mask-512.png'];
self.addEventListener('install',e=>{e.waitUntil(caches.open(C).then(c=>c.addAll(F)));self.skipWaiting()});
self.addEventListener('activate',e=>{e.waitUntil(caches.keys().then(k=>Promise.all(k.filter(x=>x!==C).map(x=>caches.delete(x)))).then(()=>self.clients.claim()))});
self.addEventListener('fetch',e=>{const u=new URL(e.request.url);
 if(e.request.method!=='GET'||u.origin!==self.location.origin)return;
 if(/\.enc$/.test(u.pathname)){e.respondWith(fetch(e.request).catch(()=>new Response('',{status:503})));return}
 e.respondWith(caches.match(e.request,{ignoreSearch:true}).then(r=>{const n=fetch(e.request).then(res=>{if(res&&res.ok){const cl=res.clone();caches.open(C).then(c=>c.put(e.request,cl))}return res}).catch(()=>r);return r||n}))});
