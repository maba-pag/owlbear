/**
 * AC-5 behavioral Playwright E2E for #1555 (RETRY v4 — explicit light addInitScript)
 *
 * BUILDER INSTRUCTION (#1555 retry v4):
 *   Replace the tracked spec with this file:
 *     cp .owlbear/scratch/1555-pds-scheme-dark-v4.spec.ts serve/cockpit/web/e2e/pds-scheme-dark-1555.spec.ts
 *     git add serve/cockpit/web/e2e/pds-scheme-dark-1555.spec.ts
 *     cd serve/cockpit/web && npm run test:e2e -- pds-scheme-dark-1555
 *
 * Root cause analysis (v2 and v3 failures):
 *   v2 failure: used page.reload() to switch dark→light. addInitScript fires on every
 *   navigation, so reload re-applied dark override even after localStorage was set to light.
 *
 *   v3 failure: used page.context().newPage() with NO init script, assuming light is the
 *   default. But on macOS in dark mode, prefersDark() returns true → auto theme resolves
 *   to dark → new page also loaded in dark mode → both captures returned rgb(255,255,255).
 *
 * Fix (v4): the light-mode page uses its OWN addInitScript that explicitly forces 'light'.
 *   - addInitScript is page-scoped — dark page's script does not bleed to the new page.
 *   - addInitScript on the light page fires on its initial navigation only (no reload).
 *   - The explicit 'light' localStorage value overrides the OS prefers-dark signal.
 *
 * Test 1 (unchanged) — computed color-scheme property on <html>:
 *   Checks getComputedStyle(html).colorScheme contains 'dark' when .scheme-dark is active.
 *   Falsifiable: FAILS if color-scheme.css is not imported or .scheme-dark does not set
 *   the CSS color-scheme property (class presence alone is not enough).
 *
 * Test 2 (v4 fix) — PDS shadow DOM visual rendering:
 *   Captures p-button shadow inner-button computed text color for dark and light using
 *   SEPARATE pages, each with its own addInitScript forcing the theme explicitly.
 *   Falsifiable: FAILS if PDS color-scheme bridge is not active → darkColor === lightColor.
 *
 * API isolation: all /api/* routes stubbed — no backend required.
 * LIFO route registration: catch-all first, specific routes last (highest priority).
 */
import { test, expect, type Page } from '@playwright/test'

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

async function stubApis(page: Page): Promise<void> {
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
      await stubApis(page)
      await page.goto('/')
      await page.locator('[data-region="workspace"]').waitFor({ state: 'visible' })

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
      await stubApis(page)
      await page.goto('/')
      await page.locator('[data-region="workspace"]').waitFor({ state: 'visible' })

      const darkColor = await page.evaluate(() => {
        const host = document.querySelector('p-button')
        if (!host?.shadowRoot) return null
        const btn = host.shadowRoot.querySelector('button')
        if (!btn) return null
        return window.getComputedStyle(btn).color
      })

      expect(
        darkColor,
        'p-button shadow root must expose a rendered <button> element in dark mode — ' +
          'null means the PDS component is not initialized or shadow root is closed',
      ).not.toBeNull()

      // ── Step 2: capture light-mode computed color (separate page, explicit 'light') ─
      // A new page has no registered init scripts. We register a 'light' init script on
      // the new page to override the system color-scheme preference — without this, a
      // macOS dark-mode OS setting causes auto theme to resolve to dark on the new page.
      const lightPage = await page.context().newPage()
      try {
        await lightPage.addInitScript(() => {
          localStorage.setItem('owlbear-theme', 'light')
        })
        await stubApis(lightPage)
        await lightPage.goto('/')
        await lightPage.locator('[data-region="workspace"]').waitFor({ state: 'visible' })

        const lightColor = await lightPage.evaluate(() => {
          const host = document.querySelector('p-button')
          if (!host?.shadowRoot) return null
          const btn = host.shadowRoot.querySelector('button')
          if (!btn) return null
          return window.getComputedStyle(btn).color
        })

        expect(
          lightColor,
          'p-button shadow root must expose a rendered <button> element in light mode — ' +
            'null means the PDS component is not initialized or shadow root is closed',
        ).not.toBeNull()

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
