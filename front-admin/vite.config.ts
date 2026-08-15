/// <reference types="vitest/config" />
import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  // Falls back to process.env explicitly: inside Docker Compose there's no .env
  // file mounted, only the environment: block, which lands in process.env.
  const backendTarget = env.API_PROXY_TARGET || process.env.API_PROXY_TARGET || 'http://localhost:18000'

  return {
    plugins: [react(), tailwindcss()],
    server: {
      // host:true binds 0.0.0.0 so the dev server is reachable from outside a
      // Docker container, not just from inside it. Harmless for local (non-Docker) dev.
      host: true,
      // Dev-only fix for the backend having no CORS middleware (it's never had a
      // browser-based consumer before this front). Proxies /admin/* same-origin so
      // requests never leave localhost:5173 from the browser's point of view.
      // Override the target with API_PROXY_TARGET in .env (not VITE_-prefixed,
      // so it's Node/Vite-config-only and never bundled into client code).
      proxy: {
        '/admin': {
          target: backendTarget,
          changeOrigin: true,
        },
      },
    },
    test: {
      environment: 'jsdom',
      setupFiles: ['./src/test/setup.ts'],
      globals: true,
    },
  }
})
