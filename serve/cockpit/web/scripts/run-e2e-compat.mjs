import { spawnSync } from 'node:child_process'
import { checkBrowser } from './check-playwright-browser.mjs'

const configuredBrowsers = process.env['E2E_COMPAT_BROWSERS'] || 'chromium'
const browsers = configuredBrowsers.split(/[,\s]+/).filter(Boolean)
const projects = browsers.map((browser) => `compatibility-${browser}`)
const compatibilitySpecs = [
  'e2e/smoke.spec.ts',
  'e2e/pds-runtime-csp.spec.ts',
  'e2e/pds-scheme-dark.spec.ts',
]

let browsersAvailable = true
for (const browser of browsers) {
  if (!(await checkBrowser(browser))) {
    browsersAvailable = false
  }
}

if (!browsersAvailable) {
  process.exit(1)
}

const forwardedArgs = process.argv.slice(2)
const result = spawnSync(
  'playwright',
  [
    'test',
    '--config=playwright.compat.config.ts',
    ...projects.map((project) => `--project=${project}`),
    ...(forwardedArgs.length > 0 ? forwardedArgs : compatibilitySpecs),
  ],
  {
    shell: process.platform === 'win32',
    stdio: 'inherit',
  },
)

if (result.error) {
  console.error(result.error.message)
  process.exit(1)
}

process.exit(result.status ?? 1)
