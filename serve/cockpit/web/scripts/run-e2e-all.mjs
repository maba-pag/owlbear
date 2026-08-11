import { spawnSync } from 'node:child_process'
import { checkChromium } from './check-playwright-browser.mjs'

const suites = [
  { name: 'chromium', environment: {} },
  { name: 'work-portfolio', environment: { WORK_PORTFOLIO_E2E: '1' } },
  { name: 'memory-purge-assembled', environment: { PURGE_E2E: '1' } },
  { name: 'memory-lifecycle-assembled', environment: { LIFECYCLE_E2E: '1' } },
]

if (!(await checkChromium())) {
  process.exit(1)
}

const forwardedArgs = process.argv.slice(2)
let failed = false

for (const suite of suites) {
  console.log(`\nRunning E2E project: ${suite.name}`)
  const result = spawnSync('playwright', ['test', `--project=${suite.name}`, ...forwardedArgs], {
    env: { ...process.env, CI: '1', ...suite.environment },
    shell: process.platform === 'win32',
    stdio: 'inherit',
  })

  if (result.error) {
    console.error(result.error.message)
    failed = true
    continue
  }
  if ((result.status ?? 1) !== 0) {
    failed = true
  }
}

process.exit(failed ? 1 : 0)
