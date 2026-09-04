/**
 * Playwright coverage for the PDS dark color-scheme bridge.
 *
 * Verifies the computed html color-scheme and PDS shadow DOM rendering differ
 * between explicit dark and light theme pages. API routes are stubbed with the
 * catch-all registered before specific handlers.
 */
import { test, expect, type Page } from '@playwright/test'
import { EMPTY_WORK_ITEM_PORTFOLIO } from './support/api-fixtures'
import { trackPageErrors, waitForWorkspaceWithoutPageErrors } from './support/page-errors'

// ─── Minimal API fixtures ─────────────────────────────────────────────────────

const STATUSES = ['research', 'backlog', 'todo', 'in-progress', 'review', 'docs', 'done']
const PRIORITIES = ['critical', 'needed', 'important', 'nice-to-have', 'someday']

const BOARD = {
  statuses: STATUSES.map((name) => ({ name })),
  priorities: PRIORITIES,
  valid_transitions: {
    research: ['backlog'],
    backlog: ['research', 'todo'],
    todo: ['backlog', 'in-progress'],
    'in-progress': ['todo', 'review'],
    review: ['in-progress', 'docs'],
    docs: ['review', 'done'],
    done: [],
  } as Record<string, string[]>,
}

const TASKS = {
  tasks: [
    {
      id: 1,
      title: 'Sample Task',
      status: 'todo',
      priority: 'important',
      tags: [],
      blocked: false,
      block_reason: null,
      claimed: false,
    },
  ],
  mtime: 1713456000,
}

// ─── Shared stub helper ───────────────────────────────────────────────────────
// Routes registered first have LOWER priority (Playwright LIFO) — catch-all
// registered first ensures specific handlers always win.

async function stubApis(page: Page) {
  const pageErrors = trackPageErrors(page)

  await page.route('/api/**', (route) => route.fulfill({ status: 200, json: {} }))

  await page.route('/api/events', (route) =>
    route.fulfill({
      status: 200,
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        Connection: 'keep-alive',
      },
      body: '',
    }),
  )

  await page.route('/api/tasks', (route) => route.fulfill({ json: TASKS }))
  await page.route('/api/board', (route) => route.fulfill({ json: BOARD }))
  await page.route('/api/work-items', (route) => route.fulfill({ json: EMPTY_WORK_ITEM_PORTFOLIO }))

  return pageErrors
}

async function getRenderedPButtonTextColor(page: Page, mode: 'dark' | 'light'): Promise<string> {
  await page.evaluate(() => {
    if (document.querySelector('p-button[data-testid="pds-color-probe"]')) return

    const probe = document.createElement('p-button')
    probe.dataset.testid = 'pds-color-probe'
    probe.textContent = 'Color probe'
    document.body.append(probe)
  })

  await page.waitForFunction(() => {
    return Array.from(document.querySelectorAll('p-button[data-testid="pds-color-probe"]')).some((host) =>
      host.shadowRoot?.querySelector('button') !== null,
    )
  }, undefined, { timeout: 8_000 })

  const color = await page.evaluate(() => {
    for (const host of Array.from(document.querySelectorAll('p-button[data-testid="pds-color-probe"]'))) {
      const button = host.shadowRoot?.querySelector('button')
      if (button) {
        return window.getComputedStyle(button).color
      }
    }

    return null
  })

  expect(
    color,
    `p-button shadow root must expose a rendered <button> element in ${mode} mode — ` +
      'null means the PDS component is not initialized or shadow root is closed',
  ).not.toBeNull()

  return color!
}

// ─── AC-5: falsifiable dark-mode proof on PDS shadow DOM ─────────────────────

test.describe('TestFromAC_PdsSchemeClassE2E_1555', () => {
  /**
   * AC-5 Test 1 — computed color-scheme property on <html>
   *
   * Checks getComputedStyle(document.documentElement).colorScheme contains 'dark'
   * when .scheme-dark is active. This is NOT the same as checking classList — it
   * proves the CSS rule `.scheme-dark { color-scheme: dark }` from color-scheme.css
   * is actually loaded and resolved by the browser.
   *
   * Falsifiable:
   *   - FAILS if color-scheme.css is not imported → no `.scheme-dark { color-scheme: dark }`
   *     rule → computed colorScheme falls back to browser default ('normal' or 'light dark')
   *   - FAILS if .scheme-dark class is not set by theme-bootstrap.js
   */
  test(
    'AC-5: computed color-scheme on <html> is dark when .scheme-dark class is active',
    async ({ page }) => {
      await page.addInitScript(() => {
        localStorage.setItem('owlbear-theme', 'dark')
      })
      const pageErrors = await stubApis(page)
      await page.goto('/')
      await waitForWorkspaceWithoutPageErrors(page, pageErrors)

      const result = await page.evaluate(() => ({
        hasSchemeDark: document.documentElement.classList.contains('scheme-dark'),
        computedColorScheme: window.getComputedStyle(document.documentElement).colorScheme,
      }))

      expect(result.hasSchemeDark, 'html must carry .scheme-dark class').toBe(true)

      expect(
        result.computedColorScheme,
        'computed color-scheme on <html> must contain "dark" — proves color-scheme.css ' +
          'is imported and .scheme-dark sets the CSS property, not just the class name; ' +
          `actual value: "${result.computedColorScheme}"`,
      ).toContain('dark')
    },
  )

  /**
   * AC-5 Test 2 — PDS shadow DOM renders visually different in dark vs light
   *
   * Uses TWO pages with EXPLICIT theme init scripts:
   *   - Dark page: addInitScript forces localStorage('owlbear-theme', 'dark')
   *   - Light page: addInitScript forces localStorage('owlbear-theme', 'light')
   *
   * Why explicit init script on the light page:
   *   Omitting localStorage and relying on the default 'auto' theme is unsafe —
   *   on macOS in dark mode, prefersDark() returns true and auto resolves to dark,
   *   making both pages load in dark mode (observed in v3: both returned rgb(255,255,255)).
   *   Forcing 'light' via addInitScript is the only reliable way to get light mode
   *   regardless of the OS color-scheme setting.
   *
   * Why a new page (not page.reload()):
   *   addInitScript fires on every navigation of its registered page. Using reload() on
   *   the dark page after evaluate()-setting light would re-apply the dark init script,
   *   undoing the localStorage change (observed in v2 failure).
   *
   * Falsifiable:
   *   - FAILS if PDS color-scheme bridge is not active → both pages render identically
   *   - FAILS if .scheme-dark / .scheme-light are not applied correctly → CSS token swap
   *     does not occur → p-button shadow DOM computes same text color in both modes
   *   - FAILS if p-button shadow root is inaccessible (component not initialized)
   *
   * Measured property: computed text color (color) of inner <button> in p-button shadow.
   *   In light mode: PDS --p-color-primary ≈ near-black (hsl(225 66.7% 1.2%))
   *   In dark mode:  PDS --p-color-primary ≈ near-white (hsl(225 100% 99%))
   *   These values are set by color-scheme.css polyfill when light-dark() is unsupported,
   *   or resolved by the browser's native light-dark() function when supported.
   */
  test(
    'AC-5: p-button shadow DOM inner button has distinct computed text color in dark vs light',
    async ({ page }) => {
      // ── Step 1: capture dark-mode computed color ────────────────────────────
      await page.addInitScript(() => {
        localStorage.setItem('owlbear-theme', 'dark')
      })
      const pageErrors = await stubApis(page)
      await page.goto('/')
      await waitForWorkspaceWithoutPageErrors(page, pageErrors)

      const darkColor = await getRenderedPButtonTextColor(page, 'dark')

      // ── Step 2: capture light-mode computed color (separate page, explicit 'light') ─
      // A new page has no registered init scripts. We register a 'light' init script on
      // the new page to override the system color-scheme preference — without this, a
      // macOS dark-mode OS setting causes auto theme to resolve to dark on the new page.
      const lightPage = await page.context().newPage()
      try {
        await lightPage.addInitScript(() => {
          localStorage.setItem('owlbear-theme', 'light')
        })
        const lightPageErrors = await stubApis(lightPage)
        await lightPage.goto('/')
        await waitForWorkspaceWithoutPageErrors(lightPage, lightPageErrors)

        const lightColor = await getRenderedPButtonTextColor(lightPage, 'light')

        // ── Primary assertion: text colors must differ between dark and light ───
        expect(
          darkColor,
          `p-button inner button must render with a different computed text color in ` +
            `dark mode (got: ${darkColor}) vs light mode (got: ${lightColor}) — ` +
            `equal values indicate PDS color-scheme bridge is not affecting shadow DOM rendering`,
        ).not.toBe(lightColor)
      } finally {
        await lightPage.close()
      }
    },
  )
})
