/**
 * Playwright coverage for PDS runtime loading under CSP.
 *
 * Proves that Porsche Design System custom elements register from local bundles
 * so the shell works under the script-src 'self' CSP injected by vite.config.ts.
 * API isolation: all /api/* routes stubbed via page.route(); no backend required.
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

// ─── AC1: PDS custom elements registered from local bundles ───────────────────
// After workspace is visible, customElements.get() must return defined constructors
// for p-button, p-icon, p-tabs, p-tabs-item (the elements Shell.tsx directly renders).

test.describe('TestFromAC_PDSCustomElementsRegistered', () => {
  test.beforeEach(async ({ page }) => {
    await stubApis(page)
    await page.goto('/')
    await page.locator('[data-region="workspace"]').waitFor({ state: 'visible' })
  })

  // Happy path: p-button is defined (the primary interactive PDS element in nav-rail)
  test('p-button custom element is defined after workspace renders', async ({ page }) => {
    const isDefined = await page.evaluate(() => customElements.get('p-button') !== undefined)
    expect(isDefined).toBe(true)
  })

  // Happy path: remaining Shell-rendered PDS elements are all defined
  test('p-icon, p-tabs, and p-tabs-item are defined after workspace renders', async ({ page }) => {
    const results = await page.evaluate(() => ({
      'p-icon': customElements.get('p-icon') !== undefined,
      'p-tabs': customElements.get('p-tabs') !== undefined,
      'p-tabs-item': customElements.get('p-tabs-item') !== undefined,
    }))
    expect(results['p-icon'], 'p-icon must be a registered custom element').toBe(true)
    expect(results['p-tabs'], 'p-tabs must be a registered custom element').toBe(true)
    expect(results['p-tabs-item'], 'p-tabs-item must be a registered custom element').toBe(true)
  })
})

// ─── AC2: No Porsche CDN securitypolicyviolation events during shell load ──────
// The CSP meta tag (script-src 'self') injected by cspPlugin blocks any CDN
// script. The test collects violations via addInitScript (runs before page JS)
// and fails if any blockedURI points to a Porsche CDN origin.

test.describe('TestFromAC_NoCDNCSPViolations', () => {
  test.beforeEach(async ({ page }) => {
    // Must register violation collector BEFORE goto so the listener is active
    // from the moment the page starts executing scripts.
    await page.addInitScript(() => {
      ;(window as unknown as { __cspViolations__: string[] }).__cspViolations__ = []
      document.addEventListener('securitypolicyviolation', (e: SecurityPolicyViolationEvent) => {
        ;(window as unknown as { __cspViolations__: string[] }).__cspViolations__.push(e.blockedURI)
      })
    })
    await stubApis(page)
    await page.goto('/')
    await page.locator('[data-region="workspace"]').waitFor({ state: 'visible' })
  })

  // Boundary: CDN .com origin must not appear in blockedURIs
  test('no securitypolicyviolation fires with blockedURI from cdn.ui.porsche.com', async ({
    page,
  }) => {
    const violations = await page.evaluate(
      () => (window as unknown as { __cspViolations__: string[] }).__cspViolations__,
    )
    const comViolations = violations.filter((uri) => uri.includes('cdn.ui.porsche.com'))
    expect(
      comViolations,
      `Expected no CDN violations from cdn.ui.porsche.com, got: ${JSON.stringify(comViolations)}`,
    ).toHaveLength(0)
  })

  // Boundary: CDN .cn origin must not appear in blockedURIs (China mirror)
  test('no securitypolicyviolation fires with blockedURI from cdn.ui.porsche.cn', async ({
    page,
  }) => {
    const violations = await page.evaluate(
      () => (window as unknown as { __cspViolations__: string[] }).__cspViolations__,
    )
    const cnViolations = violations.filter((uri) => uri.includes('cdn.ui.porsche.cn'))
    expect(
      cnViolations,
      `Expected no CDN violations from cdn.ui.porsche.cn, got: ${JSON.stringify(cnViolations)}`,
    ).toHaveLength(0)
  })
})

// ─── AC3: p-button shadowRoot is populated (component fully initialized) ───────
// A non-empty shadowRoot proves the custom element's internal rendering
// activated — not just the tag being present as an undefined/empty element.

test.describe('TestFromAC_PDSShadowRootActivation', () => {
  test.beforeEach(async ({ page }) => {
    await stubApis(page)
    await page.goto('/')
    await page.locator('[data-region="workspace"]').waitFor({ state: 'visible' })
  })

  // Happy path: p-button (rendered in nav-rail) has shadowRoot with child elements
  test('p-button element has non-empty shadowRoot after page stabilizes', async ({ page }) => {
    // Wait for p-button to appear in DOM (it renders in the nav-rail unconditionally)
    await page.locator('p-button').first().waitFor({ state: 'attached' })

    const shadowRootChildCount = await page.evaluate(() => {
      const el = document.querySelector('p-button')
      // Returns -1 if element not found, 0 if shadowRoot is null/empty
      if (!el) return -1
      if (!el.shadowRoot) return 0
      return el.shadowRoot.childElementCount
    })

    // shadowRoot must exist and contain at least one element
    expect(shadowRootChildCount, 'p-button.shadowRoot must be non-null and non-empty').toBeGreaterThan(0)
  })
})
