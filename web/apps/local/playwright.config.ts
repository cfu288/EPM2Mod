import { defineConfig, devices } from '@playwright/test'

// The local app in a real browser, against its production build; the tests answer the API calls themselves.
export default defineConfig({
  testDir: './e2e',
  forbidOnly: !!process.env.CI,
  use: { baseURL: 'http://localhost:4320/' },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: { command: 'npx vite preview --port 4320 --strictPort', url: 'http://localhost:4320/' },
})
