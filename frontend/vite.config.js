import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'
import { VitePWA } from 'vite-plugin-pwa'

// The frontend calls the API at /api/* on its own origin and Vite proxies
// it to the FastAPI backend. That way a phone on the same Wi-Fi only needs
// http://<laptop-ip>:5173 -- no second address to configure, no CORS.
const apiProxy = {
  '/api': {
    target: process.env.API_PROXY_TARGET || 'http://127.0.0.1:8000',
    changeOrigin: true,
    rewrite: (path) => path.replace(/^\/api/, ''),
  },
}

// https://vite.dev/config/
export default defineConfig({
  server: { host: true, proxy: apiProxy },
  preview: { host: true, proxy: apiProxy },
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['icons/apple-touch-icon.png'],
      // Only precache the built app shell (JS/CSS/HTML/icons). API calls
      // go to a different origin (the FastAPI backend) and are
      // deliberately NOT cached here -- this is a live demo, not an
      // offline-data app, and stale cached benefit numbers would be a
      // real bug mid-demo.
      workbox: {
        globPatterns: ['**/*.{js,css,html,ico,png,svg}'],
        navigateFallbackDenylist: [/^\/api\//],
      },
      manifest: {
        name: 'LetterLens',
        short_name: 'LetterLens',
        description: 'Multilingual mail assistant for older New Yorkers',
        start_url: '/',
        scope: '/',
        display: 'standalone',
        background_color: '#f2f2f7',
        theme_color: '#007aff',
        icons: [
          { src: 'icons/icon-192.png', sizes: '192x192', type: 'image/png' },
          { src: 'icons/icon-512.png', sizes: '512x512', type: 'image/png' },
          {
            src: 'icons/icon-512-maskable.png',
            sizes: '512x512',
            type: 'image/png',
            purpose: 'maskable',
          },
        ],
      },
    }),
  ],
})
