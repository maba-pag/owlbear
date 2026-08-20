import { constants } from 'node:fs'
import { access } from 'node:fs/promises'
import { resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium, firefox, webkit } from '@playwright/test'

const browserTypes = { chromium, firefox, webkit }

export async function checkBrowser(browserName) {
  const browserType = browserTypes[browserName]
  if (!browserType) {
    console.error(`Unsupported Playwright browser: ${browserName}`)
    return false
  }

  const executablePath = browserType.executablePath()
  try {
    await access(executablePath, constants.X_OK)
    return true
  } catch {
    console.error([
      `Playwright ${browserName} is unavailable.`,
      `Expected executable: ${executablePath}`,
      'Install it from serve/cockpit/web with:',
      `  npx playwright install ${browserName}`,
    ].join('\n'))
    return false
  }
}

export async function checkChromium() {
  return checkBrowser('chromium')
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const requestedBrowsers = process.argv.slice(2)
  const browsers = requestedBrowsers.length > 0 ? requestedBrowsers : ['chromium']
  let available = true
  for (const browserName of browsers) {
    if (!(await checkBrowser(browserName))) {
      available = false
    }
  }
  process.exitCode = available ? 0 : 1
}
