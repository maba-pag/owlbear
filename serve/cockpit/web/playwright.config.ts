// Browser binaries are NOT bundled with @playwright/test.
// Run once after install: npx playwright install chromium
import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: 'e2e',
  use: {
    baseURL: 'http://localhost:4173',
    headless: true,
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'memory-purge-assembled',
      testMatch: /memory-purge-assembled\.spec\.ts/,
      use: { ...devices['Desktop Chrome'], baseURL: 'http://127.0.0.1:8421' },
    },
    {
      name: 'memory-lifecycle-assembled',
      testMatch: /memory-lifecycle-assembled\.spec\.ts/,
      use: { ...devices['Desktop Chrome'], baseURL: 'http://127.0.0.1:8422' },
    },
    {
      name: 'work-portfolio',
      testMatch: /work-portfolio\.spec\.ts/,
      use: { ...devices['Desktop Chrome'], baseURL: 'http://127.0.0.1:4175' },
    },
  ],
  webServer: process.env['WORK_PORTFOLIO_E2E']
    ? {
        command: 'npm run build && node e2e/support/start-work-portfolio-stack.mjs',
        url: 'http://127.0.0.1:4175/health/live',
        reuseExistingServer: false,
        timeout: 120_000,
      }
    : process.env['LIFECYCLE_E2E']
    ? {
        command: 'npm run build && node e2e/support/start-memory-lifecycle-stack.mjs',
        url: 'http://127.0.0.1:8422/health',
        reuseExistingServer: false,
        timeout: 120_000,
      }
    : process.env['PURGE_E2E']
    ? {
        command: 'npm run build && node e2e/support/start-memory-purge-stack.mjs',
        url: 'http://127.0.0.1:8421/health',
        reuseExistingServer: false,
        timeout: 120_000,
      }
    : {
        command: 'npm run build && npm run preview',
        url: 'http://localhost:4173',
        reuseExistingServer: !process.env['CI'],
      },
})
