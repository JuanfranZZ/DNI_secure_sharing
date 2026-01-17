const CACHE_NAME = 'streamlit-pwa-v1';
const ASSETS = [
  '/',
  '/manifest.json',
  // Agrega aquí las URLs de tus iconos si los tienes
];

// Instalación del Service Worker y almacenamiento en caché
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(ASSETS);
    })
  );
});

// Estrategia de respuesta: Primero caché, luego red
self.addEventListener('fetch', (event) => {
  event.respondWith(
    caches.match(event.request).then((response) => {
      return response || fetch(event.request);
    })
  );
});