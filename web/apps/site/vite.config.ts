import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// The public site. GitHub Pages serves it under /<repository>/
export default defineConfig({
  base: '/EPM2Mod/',
  plugins: [react(), tailwindcss()],
  // the preview pictures stay files (the tests and the browser cache name them)
  build: { assetsInlineLimit: 0 },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['@epm2mod/ui/test/setup'],
    include: ['src/**/*.test.{ts,tsx}'],
  },
})
