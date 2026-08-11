import { constants } from 'node:fs'
import { access } from 'node:fs/promises'
import { resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium } from '@playwright/test'

export async function checkChromium() {
  const executablePath = chromium.executablePath()
  try {
    await access(executablePath, constants.X_OK)
    return true
  } catch {
    console.error([
      'Playwright Chromium is unavailable.',
      `Expected executable: ${executablePath}`,
      'Install it from serve/cockpit/web with:',
      '  npx playwright install chromium',
    ].join('\n'))
    return false
  }
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  process.exitCode = (await checkChromium()) ? 0 : 1
}
