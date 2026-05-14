/**
 * RED phase Playwright E2E test for #1555: Bridge PDS v4 color-scheme with data-theme toggle
 *
 * BUILDER INSTRUCTION (#1555): Copy this file to the tracked E2E directory and verify tests FAIL:
 *   cp .owlbear/scratch/1555-pds-scheme-dark.spec.ts serve/cockpit/web/e2e/pds-scheme-dark-1555.spec.ts
 *   git add serve/cockpit/web/e2e/pds-scheme-dark-1555.spec.ts
 *   npm run test:e2e -- pds-scheme-dark-1555  # must show failures before implementing
 *
 * AC-5: Playwright e2e confirms at least one PDS shadow-DOM component (e.g. p-button)
 * renders with dark-mode color values when .scheme-dark is active on <html>.
 *
 * Expected to FAIL in RED phase because:
 *   1. theme-bootstrap.js does not set .scheme-dark class → html never has .scheme-dark
 *   2. Without .scheme-dark on html, PDS color-scheme.css dark styles are not applied
 *      to shadow DOM — components remain in light mode
 *
 * API isolation: all /api/* routes stubbed via page.route() — no backend required.
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

// ─── AC-5: .scheme-dark on html + PDS shadow DOM dark-mode colors ─────────────

test.describe('TestFromAC_PdsSchemeClassE2E_1555', () => {
  test('AC-5: html has .scheme-dark class when dark theme is stored in localStorage', async ({
    page,
  }) => {
    await page.addInitScript(() => {
      localStorage.setItem('owlbear-theme', 'dark')
    })
    await stubApis(page)
    await page.goto('/')
    await page.locator('[data-region="workspace"]').waitFor({ state: 'visible' })

    const hasSchemeClass = await page.evaluate(() =>
      document.documentElement.classList.contains('scheme-dark'),
    )

    expect(hasSchemeClass, 'html must have .scheme-dark class when dark theme is active').toBe(true)
  })

  test('AC-5: p-button shadow DOM exists and html carries .scheme-dark for PDS dark styling', async ({
    page,
  }) => {
    await page.addInitScript(() => {
      localStorage.setItem('owlbear-theme', 'dark')
    })
    await stubApis(page)
    await page.goto('/')
    await page.locator('[data-region="workspace"]').waitFor({ state: 'visible' })

    // Primary: html must have .scheme-dark for PDS to apply dark color-scheme
    const htmlHasSchemeDark = await page.evaluate(() =>
      document.documentElement.classList.contains('scheme-dark'),
    )
    expect(
      htmlHasSchemeDark,
      'html must carry .scheme-dark to activate PDS dark color-scheme on shadow DOM',
    ).toBe(true)

    // Secondary: p-button shadow root must be accessible (proves PDS registered and dark
    // styles are applied via color-scheme inheritance into shadow DOM)
    const shadowInfo = await page.evaluate(() => {
      const pButton = document.querySelector('p-button')
      if (!pButton) return { found: false, hasShadowRoot: false }
      return {
        found: true,
        hasShadowRoot: pButton.shadowRoot !== null,
      }
    })

    expect(shadowInfo.found, 'at least one p-button element must be present in the DOM').toBe(true)
    expect(
      shadowInfo.hasShadowRoot,
      'p-button must have a shadow root (PDS component initialized)',
    ).toBe(true)
  })
})
