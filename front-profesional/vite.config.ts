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
      // Dev-only fix: the backend has no CORS middleware (same reasoning as
      // front-admin's vite.config.ts). Proxies same-origin so the browser
      // never makes a cross-origin request.
      proxy: {
        '/auth': { target: backendTarget, changeOrigin: true },
        '/profesional': { target: backendTarget, changeOrigin: true },
        '/turnos': { target: backendTarget, changeOrigin: true },
        '/pacientes': { target: backendTarget, changeOrigin: true },
      },
    },
    test: {
      environment: 'jsdom',
      setupFiles: ['./src/test/setup.ts'],
      globals: true,
      // Router tests touch several lazy-loaded chunks for the first time;
      // Vite's cold on-demand transform can exceed the 5000ms Vitest default
      // (which would otherwise race against extended findBy timeouts).
      testTimeout: 15_000,
    },
  }
})
