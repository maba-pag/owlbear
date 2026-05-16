/**
 * Playwright E2E tests for #1591: PDS global-styles import + CSP font relaxation.
 *
 * Proves that:
 * AC1 — PDS CSS custom properties (--p-color-canvas, --p-spacing-static-md,
 *        --p-font-porsche-next) resolve to non-empty values on document.documentElement.
 * AC2 — CSP meta tag includes font-src 'self' https://cdn.ui.porsche.com.
 * AC3 — No console errors or warnings containing 'porsche' during shell load.
 *
 * Expected to FAIL in RED phase because:
 * - AC1: global-styles/index.css (variables.css) not yet imported → --p-* props absent on :root
 *   (color-scheme.css @supports not block is skipped in Chromium 123+ because light-dark()
 *   is natively supported → no fallback vars either)
 * - AC2: vite.config.ts cspPlugin emits no font-src directive → only default-src 'self'
 * - AC3: missing font-src allows CDN font-load requests to fail with CSP violations,
 *   and browser logs blocked-URI errors containing 'porsche' to the console
 *
 * Task #1594 (builder) will fix these by importing global-styles and adding font-src.
 *
 * API isolation: all /api/* routes stubbed via page.route() — no backend required.
 */
import { test, expect, type Page } from '@playwright/test'

// ─── Minimal API fixtures ──────────────────────────────────────────────────────

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

// ─── Shared stub helper ────────────────────────────────────────────────────────
// Routes registered first have LOWER priority (Playwright LIFO) — catch-all
// registered first ensures specific handlers always win.

async function stubApis(page: Page): Promise<void> {
  // Catch-all fallback for remaining /api/* routes (decisions, scan, sessions, etc.)
  // Must be registered FIRST so specific routes (registered after) take precedence.
  await page.route('/api/**', (route) => route.fulfill({ status: 200, json: {} }))

  // SSE endpoint — return empty stream so EventSourceProvider connects cleanly
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

  // Core data routes — registered last so they take priority over catch-all
  await page.route('/api/tasks', (route) => route.fulfill({ json: TASKS }))
  await page.route('/api/board', (route) => route.fulfill({ json: BOARD }))
}

// ─── AC1: PDS CSS custom properties resolve to non-empty values on :root ───────
// After workspace is visible, getComputedStyle(document.documentElement) must
// return non-empty strings for all three named PDS v4.1.0 custom properties.
// These are defined in global-styles/variables.css (exported via index.css).
//
// Currently FAILS in RED: variables.css not imported → properties unset on :root.
// color-scheme.css @supports not block also skipped in modern Chromium.

test.describe('TestFromAC_PDSCSSCustomProperties', () => {
  test.beforeEach(async ({ page }) => {
    await stubApis(page)
    await page.goto('/')
    await page.locator('[data-region="workspace"]').waitFor({ state: 'visible' })
  })

  // Happy path: --p-color-canvas resolves to a non-empty value on :root
  test('--p-color-canvas resolves to non-empty value on document.documentElement', async ({
    page,
  }) => {
    const value = await page.evaluate(() =>
      getComputedStyle(document.documentElement).getPropertyValue('--p-color-canvas').trim(),
    )
    expect(value, '--p-color-canvas must resolve to a non-empty string on :root').not.toBe('')
  })

  // Happy path: --p-spacing-static-md resolves to a non-empty value (e.g. "16px")
  test('--p-spacing-static-md resolves to non-empty value on document.documentElement', async ({
    page,
  }) => {
    const value = await page.evaluate(() =>
      getComputedStyle(document.documentElement).getPropertyValue('--p-spacing-static-md').trim(),
    )
    expect(value, '--p-spacing-static-md must resolve to a non-empty string on :root').not.toBe('')
  })

  // Happy path: --p-font-porsche-next resolves to a non-empty value (e.g. '"Porsche Next",...')
  test('--p-font-porsche-next resolves to non-empty value on document.documentElement', async ({
    page,
  }) => {
    const value = await page.evaluate(() =>
      getComputedStyle(document.documentElement).getPropertyValue('--p-font-porsche-next').trim(),
    )
    expect(value, '--p-font-porsche-next must resolve to a non-empty string on :root').not.toBe('')
  })

  // Boundary: all three AC1 properties resolve simultaneously — guards partial import
  test('all three AC1 CSS custom properties are non-empty in a single evaluation', async ({
    page,
  }) => {
    const values = await page.evaluate(() => {
      const style = getComputedStyle(document.documentElement)
      return {
        canvas: style.getPropertyValue('--p-color-canvas').trim(),
        spacingMd: style.getPropertyValue('--p-spacing-static-md').trim(),
        fontFamily: style.getPropertyValue('--p-font-porsche-next').trim(),
      }
    })
    expect(values.canvas, '--p-color-canvas must be non-empty').not.toBe('')
    expect(values.spacingMd, '--p-spacing-static-md must be non-empty').not.toBe('')
    expect(values.fontFamily, '--p-font-porsche-next must be non-empty').not.toBe('')
  })
})

// ─── AC2: CSP meta tag includes font-src with Porsche CDN origin ───────────────
// The built HTML must contain a <meta http-equiv="Content-Security-Policy"> whose
// content includes a font-src directive authorising both 'self' and
// https://cdn.ui.porsche.com (D6 user decision).
//
// Currently FAILS in RED: vite.config.ts cspPlugin emits no font-src directive.
// The built CSP is: "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline';
// img-src 'self' data:; connect-src 'self'" — font-src absent, CDN origin absent.

test.describe('TestFromAC_CSPFontSrc', () => {
  test.beforeEach(async ({ page }) => {
    await stubApis(page)
    await page.goto('/')
    await page.locator('[data-region="workspace"]').waitFor({ state: 'visible' })
  })

  // Helper: read the CSP meta tag content attribute
  async function getCspContent(page: Page): Promise<string> {
    return page.evaluate(
      () =>
        document.querySelector('meta[http-equiv="Content-Security-Policy"]')?.getAttribute('content') ?? '',
    )
  }

  // Helper: extract the font-src directive's source list from a CSP string.
  // Returns the trimmed sources string (e.g. "'self' https://cdn.ui.porsche.com")
  // or null when no font-src directive is present.
  function extractFontSrcDirective(csp: string): string | null {
    const match = /font-src\s+([^;]+)/.exec(csp)
    return match ? match[1].trim() : null
  }

  // Happy path: CSP contains a font-src directive
  test('CSP content includes a font-src directive', async ({ page }) => {
    const content = await getCspContent(page)
    expect(content, "CSP content must include 'font-src'").toContain('font-src')
  })

  // Boundary: font-src directive value contains the Porsche CDN origin (D6 decision)
  test("font-src directive value contains 'https://cdn.ui.porsche.com'", async ({ page }) => {
    const content = await getCspContent(page)
    const fontSrc = extractFontSrcDirective(content)
    expect(fontSrc, 'font-src directive must be present in CSP').not.toBeNull()
    expect(fontSrc!, "font-src directive value must include 'https://cdn.ui.porsche.com'").toContain(
      'https://cdn.ui.porsche.com',
    )
  })

  // Boundary: font-src directive value contains 'self' alongside the CDN origin
  test("font-src directive value contains 'self'", async ({ page }) => {
    const content = await getCspContent(page)
    const fontSrc = extractFontSrcDirective(content)
    expect(fontSrc, 'font-src directive must be present in CSP').not.toBeNull()
    expect(fontSrc!, "font-src directive value must include 'self'").toContain("'self'")
  })
})

// ─── AC3: No console errors/warnings containing 'porsche' during shell load ────
// Covers font-load failures (CDN requests blocked by CSP), PDS runtime errors, and
// any other Porsche-related console output. The listener is registered before
// page.goto() to capture every console event from page start.
//
// This is a retained regression guard: if font-src is removed from CSP (AC2
// regression), the browser blocks cdn.ui.porsche.com font loads and emits a
// console error whose message contains 'porsche' — causing this test to fail.

test.describe('TestFromAC_PDSConsoleClean', () => {
  // Happy path: shell load produces no console errors or warnings mentioning 'porsche'
  test('no console errors or warnings containing "porsche" during shell load', async ({ page }) => {
    const porschemessages: string[] = []
    // Register BEFORE stubApis/goto — listener must be active from the first page event.
    page.on('console', (msg) => {
      if (
        (msg.type() === 'error' || msg.type() === 'warning') &&
        msg.text().toLowerCase().includes('porsche')
      ) {
        porschemessages.push(`[${msg.type()}] ${msg.text()}`)
      }
    })
    await stubApis(page)
    await page.goto('/')
    await page.locator('[data-region="workspace"]').waitFor({ state: 'visible' })
    expect(
      porschemessages,
      'No console errors or warnings containing "porsche" must appear during shell load',
    ).toHaveLength(0)
  })
})
