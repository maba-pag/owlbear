import { defineConfig, devices } from '@playwright/test'

const compatibilitySpecs = /(?:smoke|pds-runtime-csp|pds-scheme-dark)\.spec\.ts/

export default defineConfig({
  testDir: 'e2e',
  use: {
    baseURL: 'http://localhost:4173',
    headless: true,
    trace: 'retain-on-failure',
  },
  reporter: [
    ['line'],
    ['html', { outputFolder: 'playwright-report', open: 'never' }],
  ],
  projects: [
    {
      name: 'compatibility-chromium',
      testMatch: compatibilitySpecs,
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'compatibility-firefox',
      testMatch: compatibilitySpecs,
      use: { ...devices['Desktop Firefox'] },
    },
    {
      name: 'compatibility-webkit',
      testMatch: compatibilitySpecs,
      use: { ...devices['Desktop Safari'] },
    },
  ],
  webServer: {
    command: 'npm run build && npm run preview',
    url: 'http://localhost:4173',
    reuseExistingServer: !process.env['CI'],
    timeout: 120_000,
  },
})
