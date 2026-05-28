/**
 * Playwright coverage for nav-rail keyboard reachability.
 *
 * Ensures Tab traversal can reach the icon-only workspace nav at a desktop viewport.
 * API mocking: all routes stubbed via page.route(); no real backend required.
 */
import { test, expect, type Page } from '@playwright/test'

// ─── Minimal fixture data ──────────────────────────────────────────────────────

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

const TASKS = [
  {
    id: 1,
    title: 'Example task',
    status: 'backlog',
    priority: 'needed',
    updated: '2026-05-14T00:00:00+00:00',
    tags: [],
    blocked: false,
    block_reason: null,
    claimed: false,
  },
]

// ─── API stub helper ───────────────────────────────────────────────────────────

/**
 * Stub all API routes used by the Cockpit shell.
 * Catch-all registered first (lowest LIFO priority); specific routes after (higher priority).
 */
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
  await page.route('/api/board', (route) => route.fulfill({ json: BOARD }))
  await page.route('/api/tasks', (route) =>
    route.fulfill({ json: { tasks: TASKS, mtime: 1_713_456_000 } }),
  )
  await page.route('/api/tasks/*', (route) =>
    route.fulfill({
      json: {
        id: 1,
        title: 'Example task',
        status: 'backlog',
        priority: 'needed',
        updated: '2026-05-14T00:00:00+00:00',
        created: '2026-05-13T00:00:00+00:00',
        tags: [],
        blocked: false,
        block_reason: null,
        claimed: false,
        claimed_at: null,
        dep_status: null,
        parent: null,
        depends_on: [],
        body: '',
      },
    }),
  )
  await page.route(/\/api\/sessions(\?.*)?$/, (route) =>
    route.fulfill({ json: { sessions: [] } }),
  )
  await page.route('/api/tasks/scan', (route) => route.fulfill({ json: [] }))
}

// ─── AC-2: Nav-rail keyboard reachability ─────────────────────────────────────
//
// Contract: the active workspace button in the PCanvas start sidebar remains in
// the normal keyboard Tab sequence.

test.describe('TestFromAC_NavRailTabReachability', () => {
  test.use({ viewport: { width: 1280, height: 800 } })

  test('nav-rail workspace button is keyboard-reachable via Tab', async ({
    page,
  }) => {
    // The Kanban workspace button must be focusable via sequential keyboard navigation.
    await stubApis(page)
    await page.goto('/')
    await page.waitForSelector('[data-column]', { timeout: 10_000 })

    // Reset focus to the document root before probing tab order.
    await page.locator('body').click()

    // Tab through up to 30 focusable elements looking for the nav-rail button.
    let reached = false
    for (let i = 0; i < 30; i++) {
      await page.keyboard.press('Tab')
      const isNavRailFocused = await page.evaluate(() => {
        const el = document.activeElement
        if (!el) return false
        return (
          el.getAttribute('data-surface') === 'kanban' ||
          el.closest('[data-surface="kanban"]') !== null
        )
      })
      if (isNavRailFocused) {
        reached = true
        break
      }
    }

    expect(reached, [
      'Nav-rail workspace button [data-surface="kanban"] must be reachable via sequential Tab navigation.',
      'Icon-only workspace navigation still needs ordinary keyboard reachability.',
    ].join(' ')).toBe(true)
  })

  test('nav-rail workspace button is not removed from the tab order', async ({
    page,
  }) => {
    // Direct DOM proof paired with the behavioral Tab traversal above.
    await stubApis(page)
    await page.goto('/')
    await page.waitForSelector('[data-column]', { timeout: 10_000 })

    const navRailButton = page.locator('[data-region="nav-rail"] [data-surface="kanban"]')
    await expect(navRailButton).toBeVisible()

    await expect(navRailButton).not.toHaveAttribute('tabindex', '-1')
  })
})
