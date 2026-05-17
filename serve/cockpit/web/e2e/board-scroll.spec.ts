/**
 * Playwright coverage for board horizontal scrolling.
 *
 * Ensures all board columns stay on one row and the board container overflows
 * horizontally when seven statuses are rendered at the desktop viewport.
 * API mocking: all routes stubbed via page.route(); no real backend required.
 */
import { test, expect } from '@playwright/test'

// ─── Fixture data ──────────────────────────────────────────────────────────────

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

/** One task per status so all 7 columns render with content. */
const TASKS = STATUSES.map((status, i) => ({
  id: i + 1,
  title: `Task in ${status}`,
  status,
  priority: PRIORITIES[i % PRIORITIES.length],
  updated: '2026-05-16T00:00:00+00:00',
  tags: [],
  blocked: false,
  block_reason: null,
  claimed: false,
}))

// ─── Tests ─────────────────────────────────────────────────────────────────────

test.describe('board horizontal scroll', () => {
  test.beforeEach(async ({ page }) => {
    // Register catch-all first (LIFO — specific routes registered after override it).
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
    await page.route('/api/tasks', (route) =>
      route.fulfill({ json: { tasks: TASKS, mtime: 1_716_000_000 } }),
    )
    await page.route('/api/board', (route) => route.fulfill({ json: BOARD }))

    await page.goto('/')
    // Wait until all 7 columns are attached before measuring.
    await page.locator('[data-column]').nth(6).waitFor({ state: 'attached' })
  })

  /**
   * AC-1: Board grid container scrollWidth > clientWidth when all 7 statuses are
   * rendered at default viewport (1280×720).
   *
   * RED failure: auto-fit wraps columns onto multiple rows so no horizontal overflow
   * occurs → scrollWidth ≈ clientWidth → assertion fails.
   */
  test(
    'board grid container overflows horizontally when all 7 statuses are rendered at 1280×720',
    async ({ page }) => {
      const result = await page.evaluate(() => {
        const firstCol = document.querySelector('[data-column]')
        if (!firstCol) return { hasContainer: false, scrollWidth: 0, clientWidth: 0 }
        const container = firstCol.parentElement
        if (!container) return { hasContainer: false, scrollWidth: 0, clientWidth: 0 }
        return {
          hasContainer: true,
          scrollWidth: container.scrollWidth,
          clientWidth: container.clientWidth,
        }
      })

      expect(result.hasContainer, 'board grid container must exist').toBe(true)
      expect(
        result.scrollWidth,
        `board grid container scrollWidth (${result.scrollWidth}px) must exceed clientWidth (${result.clientWidth}px) — columns must scroll horizontally, not wrap`,
      ).toBeGreaterThan(result.clientWidth)
    },
  )

  /**
   * AC-2: All rendered columns share the same offsetTop value (single-row layout,
   * no wrapping to multiple rows).
   *
   * RED failure: auto-fit wraps columns to multiple implicit grid rows → columns
   * at different vertical positions → different offsetTop values → assertion fails.
   */
  test(
    'all 7 board columns share the same offsetTop — no row wrapping at 1280×720',
    async ({ page }) => {
      const result = await page.evaluate(() => {
        const cols = Array.from(document.querySelectorAll('[data-column]'))
        if (cols.length === 0) return { count: 0, offsetTops: [], allSame: false }
        const offsetTops = cols.map((el) => (el as HTMLElement).offsetTop)
        const first = offsetTops[0]
        const allSame = offsetTops.every((t) => t === first)
        return { count: cols.length, offsetTops, allSame }
      })

      expect(
        result.count,
        `expected 7 board columns, found ${result.count}`,
      ).toBe(7)
      expect(
        result.allSame,
        `all columns must share the same offsetTop to confirm single-row layout, but got: [${result.offsetTops.join(', ')}]`,
      ).toBe(true)
    },
  )
})
