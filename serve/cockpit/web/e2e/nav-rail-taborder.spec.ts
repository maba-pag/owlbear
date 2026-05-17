/**
 * Playwright coverage for nav-rail keyboard reachability.
 *
 * Ensures Tab traversal can reach the nav-rail PButton at a desktop viewport.
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
  await page.route('/api/decisions/pending', (route) =>
    route.fulfill({ json: { count: 0, items: [] } }),
  )
  await page.route('/api/tasks/scan', (route) => route.fulfill({ json: [] }))
}

// ─── AC-2: Nav-rail keyboard reachability ─────────────────────────────────────
//
// RED target: PButton inside <nav class="shell__nav-rail"> has tabIndex={-1}, which
// removes it from the Tab focus sequence entirely. After the builder removes the
// attribute, the button must appear in the Tab traversal of the page.

test.describe('TestFromAC_NavRailTabReachability', () => {
  test.use({ viewport: { width: 1280, height: 800 } })

  test('nav-rail PButton is keyboard-reachable via Tab — RED: tabIndex={-1} excludes from tab order', async ({
    page,
  }) => {
    // AC-2: The nav-rail PButton ([data-surface="kanban"]) must be focusable via Tab.
    //
    // RED: Shell.tsx:168 has `tabIndex={-1}` on the PButton, which marks it as
    // programmatically focusable (via .focus()) but EXCLUDED from sequential Tab order.
    // Tab traversal will skip the button entirely — the loop below never finds it
    // focused, so `reached` stays false → the final expect(reached).toBe(true) fails.
    //
    // After the builder removes tabIndex={-1}, normal Tab traversal will include the
    // button, and one of the Tab presses in the loop will land on it.
    await stubApis(page)
    await page.goto('/')
    await page.waitForSelector('[data-column]', { timeout: 10_000 })

    // Reset focus to the document root before probing tab order.
    await page.locator('body').click()

    // Tab through up to 30 focusable elements looking for the nav-rail PButton.
    let reached = false
    for (let i = 0; i < 30; i++) {
      await page.keyboard.press('Tab')
      const isNavRailFocused = await page.evaluate(() => {
        const el = document.activeElement
        if (!el) return false
        // PDS PButton renders as <p-button> custom element.
        // Check host element attribute; also check for a shadow-root button host.
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
      'Nav-rail PButton [data-surface="kanban"] must be reachable via sequential Tab navigation.',
      'RED: Shell.tsx:168 has tabIndex={-1} on the PButton inside <nav class="shell__nav-rail">,',
      'which removes it from the natural tab order. Builder must remove tabIndex={-1}.',
    ].join(' ')).toBe(true)
  })

  test('nav-rail PButton has no tabindex attribute in the DOM — RED: tabIndex={-1} rendered on element', async ({
    page,
  }) => {
    // AC-2: DOM assertion variant — the rendered PButton host element ([data-surface="kanban"])
    // must not have a tabindex="-1" attribute in the live DOM.
    //
    // RED: Shell.tsx renders tabIndex={-1} → the host <p-button> element has
    // tabindex="-1" in the DOM → toHaveAttribute('tabindex', '-1') passes →
    // the following assertion (not having tabindex="-1") fails.
    //
    // This test does NOT use the Tab-traversal loop — it directly inspects the DOM
    // attribute, providing a fast, low-flake alternative proof for AC-2.
    await stubApis(page)
    await page.goto('/')
    await page.waitForSelector('[data-column]', { timeout: 10_000 })

    const navRailButton = page.locator('[data-region="nav-rail"] [data-surface="kanban"]')
    await expect(navRailButton).toBeVisible()

    // Assert the rendered DOM element does NOT have tabindex="-1".
    // After the builder removes `tabIndex={-1}` from Shell.tsx, the rendered element
    // will have no tabindex attribute (or tabindex="0" for explicit tab-order inclusion).
    await expect(navRailButton).not.toHaveAttribute('tabindex', '-1')
  })
})
