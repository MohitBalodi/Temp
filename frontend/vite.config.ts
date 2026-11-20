import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

// Declared locally rather than pulling in @types/node: this file is type-checked
// by `npm run lint` with `types: ["vite/client"]`, which has no Node globals.
declare const process: { env: Record<string, string | undefined> };

// Where the dev server forwards /api to. Compose sets this to the `api` service;
// a bare `npm run dev` on the host falls back to the published port.
const apiTarget = process.env.API_PROXY_TARGET ?? 'http://localhost:8000';

export default defineConfig({
  plugins: [react()],
  resolve: {
    // Root-relative so no Node types are needed; mirrors `paths` in tsconfig.
    alias: { '@': '/src' },
  },
  server: {
    host: true,
    port: 5173,
    // Bind mounts on Windows/Docker don't emit inotify events.
    watch: { usePolling: true, interval: 300 },
    // The app calls the API at a relative /api/v1, so the browser only ever
    // talks to this origin. That keeps CORS out of it and means exposing the
    // stack (VS Code port forwarding, a tunnel) needs this one port, not two.
    proxy: {
      '/api': { target: apiTarget, changeOrigin: true },
    },
  },
});
