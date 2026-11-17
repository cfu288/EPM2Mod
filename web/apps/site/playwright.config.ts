import { defineConfig, devices } from '@playwright/test'

// End-to-end checks in a real browser (drag and drop cannot be tested in jsdom), against the production build.
export default defineConfig({
  testDir: './e2e',
  use: { baseURL: 'http://localhost:4319/EPM2Mod/' },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: { command: 'npx vite preview --port 4319 --strictPort', url: 'http://localhost:4319/EPM2Mod/' },
})
