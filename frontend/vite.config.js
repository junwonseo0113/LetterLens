import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'
import { VitePWA } from 'vite-plugin-pwa'

// https://vite.dev/config/
export default defineConfig({
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
