import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const backend = env.VITE_BACKEND_URL || 'http://localhost:8000';
  const wsTarget = backend.startsWith('https') ? backend.replace(/^https/, 'wss') : backend.replace(/^http/, 'ws');

  return {
    plugins: [react()],
    server: {
      port: 5173,
      proxy: {
        '/api': backend,
        '/ws': {
          target: wsTarget,
          ws: true,
        },
      },
    },
  };
});
