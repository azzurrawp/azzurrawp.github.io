const C='azzurrawp-v63';const F=['./','index.html','manifest.webmanifest','icon-192.png','icon-512.png','icon-mask-192.png','icon-mask-512.png'];
// install: scarica sempre dalla rete (non dalla cache del browser, che su GitHub Pages dura 10 minuti)
self.addEventListener('install',e=>{e.waitUntil(caches.open(C).then(c=>c.addAll(F.map(u=>new Request(u,{cache:'reload'})))));self.skipWaiting()});
self.addEventListener('activate',e=>{e.waitUntil(caches.keys().then(k=>Promise.all(k.filter(x=>x!==C).map(x=>caches.delete(x)))).then(()=>self.clients.claim()))});
function fresh(req){if(req.mode==='navigate')req=new Request(req.url);return fetch(req,{cache:'no-cache'}).then(res=>{if(res&&res.ok){const cl=res.clone();caches.open(C).then(c=>c.put(req,cl))}return res})}
self.addEventListener('fetch',e=>{const req=e.request,u=new URL(req.url);
 if(req.method!=='GET'||u.origin!==self.location.origin)return;
 if(/\.enc$/.test(u.pathname)){e.respondWith(fetch(req).catch(()=>new Response('',{status:503})));return}
 const page=req.mode==='navigate'||/\/(index\.html)?$/.test(u.pathname);
 if(page){
   // pagina: prima la rete (così l'app si aggiorna appena aperta), dopo 3 secondi o senza internet la copia salvata
   e.respondWith(new Promise(ok=>{let done=false;const cached=()=>caches.match(req,{ignoreSearch:true}).then(r=>r||caches.match('index.html'));
     const t=setTimeout(()=>{cached().then(r=>{if(r&&!done){done=true;ok(r)}})},3000);
     fresh(req).then(res=>{clearTimeout(t);if(!done){done=true;ok(res)}}).catch(()=>{clearTimeout(t);cached().then(r=>{if(!done){done=true;ok(r||Response.error())}})})}));
   return}
 e.respondWith(caches.match(req,{ignoreSearch:true}).then(r=>{const n=fresh(req).catch(()=>r);return r||n}))});
