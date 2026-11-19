import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// The local app. `epm2mod serve` serves the build from the Python package (cli/src/epm2mod/app, not in git).
// Development against a running server: uv run epm2mod serve --no-browser --port 8765, then
// EPM2MOD_API=http://127.0.0.1:8765 npm run dev:app, and open the dev address with the server's #token=...
const api = process.env.EPM2MOD_API ?? 'http://127.0.0.1:8765'

export default defineConfig({
  base: '/',
  plugins: [react(), tailwindcss()],
  build: { outDir: '../../../cli/src/epm2mod/app', emptyOutDir: true, assetsInlineLimit: 0 },
  server: {
    proxy: {
      '/api': {
        target: api,
        changeOrigin: true,
        // the server refuses a request whose Origin is another address; the proxy's own requests carry none
        configure: (proxy) => {
          proxy.on('proxyReq', (request) => {
            request.removeHeader('origin')
          })
        },
      },
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['@epm2mod/ui/test/setup'],
    include: ['src/**/*.test.{ts,tsx}'],
  },
})
