// İsim (cache-xx gibi herhangi bir şey olabilir)
var staticCacheName = "nextsefer-v1";

// Önbelleğe alınacak dosyalar
var filesToCache = [
    '/',
    '/static/css/*',
    '/static/js/*',
    '/static/img/*',
];

// Service Worker Kurulum
self.addEventListener("install", event => {
    event.waitUntil(
        caches.open(staticCacheName).then(cache => {
            return cache.addAll(filesToCache);
        })
    );
});

// Service Worker içerik alma
self.addEventListener("fetch", event => {
    event.respondWith(
        caches.match(event.request).then(response => {
            // Önbellekte varsa bu öğeyi döndür
            if (response) {
                return response;
            }
            
            // İstek klonlama
            // Kullanıldıktan sonra akış tüketildiği için
            var fetchRequest = event.request.clone();
            
            // İçeriği ağdan alma
            return fetch(fetchRequest).then(response => {
                // Yanıt geçersizse veya başarısızsa, sadece yanıtı döndür
                if (!response || response.status !== 200 || response.type !== "basic") {
                    return response;
                }
                
                // Yanıtı önbelleğe ekle ve döndür
                var responseToCache = response.clone();
                caches.open(staticCacheName).then(cache => {
                    cache.put(event.request, responseToCache);
                });
                return response;
            });
        })
    );
});

// Service Worker aktivasyon ve eski önbellekleri temizleme
self.addEventListener("activate", event => {
    var cacheWhitelist = [staticCacheName];
    
    event.waitUntil(
        caches.keys().then(cacheNames => {
            return Promise.all(
                cacheNames.map(cacheName => {
                    if (cacheWhitelist.indexOf(cacheName) === -1) {
                        return caches.delete(cacheName);
                    }
                })
            );
        })
    );
}); 