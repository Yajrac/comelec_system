const CACHE = 'applicant-public-offline-v1-{{ offline_version }}';
const SHELLS = {'/': '/offline/shell/home/', '/new-registration/': '/offline/shell/registration/', '/offline/': '/offline/shell/saved/'};
const OFFLINE = '<!doctype html><html lang="en"><meta name="viewport" content="width=device-width,initial-scale=1"><title>You are offline</title><body style="font:16px system-ui;padding:32px;color:#142b54"><h1>Page unavailable offline</h1><p>This page needs an internet connection. Your saved drafts remain on this device.</p><a href="/">Back to Home and saved submissions</a></body></html>';
self.addEventListener('install', event => {
    event.waitUntil((async () => {
        const cache = await caches.open(CACHE);
        const assets = new Set();
        for (const [path, shell] of Object.entries(SHELLS)) {
            const response = await fetch(shell, {credentials: 'omit', cache: 'no-store'});
            if (!response.ok || response.redirected) throw new Error('Offline page unavailable');
            const html = await response.text();
            for (const match of html.matchAll(/(?:src|href)="([^"]+)"/g)) {
                const url = new URL(match[1].replaceAll('&amp;', '&'), self.location.origin);
                if (url.pathname.startsWith('/static/') && url.origin === self.location.origin ||
                    url.origin === 'https://cdn.jsdelivr.net' && url.pathname.endsWith('/bootstrap.min.css')) assets.add(url.href);
            }
            await cache.put(path, new Response(html, {headers: {'Content-Type': 'text/html; charset=utf-8'}}));
        }
        for (const asset of assets) {
            const response = await fetch(asset, {credentials: 'omit', cache: 'reload'});
            if (!response.ok) throw new Error('Offline resource unavailable');
            await cache.put(asset, response);
        }
        await self.skipWaiting();
    })());
});
self.addEventListener('activate', event => event.waitUntil((async () => {
    for (const key of await caches.keys()) {
        if (key.startsWith('applicant-public-offline-') && key !== CACHE) await caches.delete(key);
    }
    await self.clients.claim();
})()));
self.addEventListener('fetch', event => {
    if (event.request.method !== 'GET') return;
    const url = new URL(event.request.url);
    if (event.request.mode === 'navigate' && url.origin === self.location.origin) {
        event.respondWith((async () => {
            try { return await fetch(event.request); }
            catch {
                const cached = Object.hasOwn(SHELLS, url.pathname) && await (await caches.open(CACHE)).match(url.pathname);
                return cached || new Response(OFFLINE, {status: 503, headers: {'Content-Type': 'text/html; charset=utf-8'}});
            }
        })());
    } else if (['script', 'style', 'image', 'font'].includes(event.request.destination)) {
        event.respondWith((async () => {
            const cached = await (await caches.open(CACHE)).match(event.request);
            return cached || fetch(event.request);
        })());
    }
});
