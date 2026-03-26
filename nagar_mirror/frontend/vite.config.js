import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['favicon.ico', 'robots.txt', 'icon-192.png', 'icon-512.png'],
      manifest: {
        name: 'Nagar Mirror',
        short_name: 'NagarMirror',
        description: 'Citizen complaint portal for Connaught Place Ward',
        theme_color: '#0f172a',
        background_color: '#080e1a',
        display: 'standalone',
        orientation: 'portrait',
        start_url: '/',
        icons: [
          { src: '/icon-192.png', sizes: '192x192', type: 'image/png' },
          { src: '/icon-512.png', sizes: '512x512', type: 'image/png' },
          { src: '/icon-512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
        ],
      },
      workbox: {
        runtimeCaching: [
          {
            urlPattern: /^https:\/\/api\.mapbox\.com\/.*/i,
            handler: 'CacheFirst',
            options: { cacheName: 'mapbox-cache', expiration: { maxEntries: 50, maxAgeSeconds: 86400 } },
          },
          {
            urlPattern: /\/api\/.*/,
            handler: 'NetworkFirst',
            options: { cacheName: 'api-cache', networkTimeoutSeconds: 5, expiration: { maxEntries: 100 } },
          },
        ],
      },
    }),
  ],
  // Fix dep resolution for mapbox-gl and react-map-gl
  build: {
    outDir: '../backend/static',
    emptyOutDir: true,
  },
  optimizeDeps: {
    include: ['maplibre-gl', 'react-map-gl/maplibre'],
    exclude: ['vite-plugin-pwa'],
  },
  server: {
    port: 5174,
    strictPort: true,
    proxy: { '/api': 'http://localhost:8000' },
  },
})
