// design_doc §3 — Vite dev server, proxies /api and /media to Django backend
// BACKEND_URL: set to http://api:8000 inside Docker (service name), defaults to
//              http://localhost:8000 for bare `npm run dev` outside Docker.
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const backendUrl = process.env.BACKEND_URL ?? 'http://localhost:8000'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    host: true,   // bind 0.0.0.0 so Docker port mapping works
    // Windows Docker: inotify events don't cross the host→container boundary,
    // so HMR won't fire without polling.
    watch: {
      usePolling: true,
      interval: 1000,
    },
    proxy: {
      '/api':   { target: backendUrl, changeOrigin: true },
      '/media': { target: backendUrl, changeOrigin: true },
    },
  },
})
