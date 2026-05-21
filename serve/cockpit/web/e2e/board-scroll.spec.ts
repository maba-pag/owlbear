/**
 * Playwright coverage for the board lane strip.
 *
 * The current morning dashboard has six operational lanes and should fit at a
 * wide desktop viewport. Denser boards still stay on one row and scroll
 * horizontally instead of wrapping.
 * API mocking: all routes stubbed via page.route(); no real backend required.
 */
import { test, expect, type Page } from '@playwright/test'

// ─── Fixture data ──────────────────────────────────────────────────────────────

const STATUSES = ['research', 'backlog', 'todo', 'in-progress', 'review', 'docs', 'done']
const DASHBOARD_STATUSES = ['todo', 'in-progress', 'review', 'docs', 'done', 'archived']
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

const DASHBOARD_BOARD = {
  statuses: DASHBOARD_STATUSES.map((name) => ({ name })),
  priorities: PRIORITIES,
  valid_transitions: {
    todo: ['in-progress'],
    'in-progress': ['todo', 'review'],
    review: ['in-progress', 'docs'],
    docs: ['review', 'done'],
    done: ['archived'],
    archived: [],
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

const DASHBOARD_TASKS = DASHBOARD_STATUSES.slice(0, 3).map((status, i) => ({
  id: i + 1,
  title: `Dashboard task in ${status}`,
  status,
  priority: PRIORITIES[i % PRIORITIES.length],
  updated: '2026-05-16T00:00:00+00:00',
  tags: [],
  blocked: false,
  block_reason: null,
  claimed: false,
}))

async function mockBoardApi(page: Page, board: typeof BOARD, tasks: typeof TASKS) {
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
    route.fulfill({ json: { tasks, mtime: 1_716_000_000 } }),
  )
  await page.route('/api/board', (route) => route.fulfill({ json: board }))
}

// ─── Tests ─────────────────────────────────────────────────────────────────────

test.describe('board horizontal scroll', () => {
  test.beforeEach(async ({ page }) => {
    await mockBoardApi(page, BOARD, TASKS)

    await page.goto('/')
    // Wait until all 7 columns are attached before measuring.
    await page.locator('[data-column]').nth(6).waitFor({ state: 'attached' })
  })

  /**
   * Seven lanes at 1280×720 are intentionally horizontally scrollable.
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
   * Dense boards remain a single lane strip instead of wrapping into rows.
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

test.describe('board wide desktop fit', () => {
  test('six-lane dashboard board fits fully at 1920×1080', async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 })
    await mockBoardApi(page, DASHBOARD_BOARD, DASHBOARD_TASKS)

    await page.goto('/')
    await page.locator('[data-column]').nth(5).waitFor({ state: 'attached' })

    const result = await page.evaluate(() => {
      const columns = Array.from(document.querySelectorAll('[data-column]')) as HTMLElement[]
      const lastColumn = columns.at(-1)
      const firstCol = columns[0]
      const container = firstCol?.parentElement
      if (!lastColumn || !container) {
        return {
          count: columns.length,
          hasContainer: false,
          scrollWidth: 0,
          clientWidth: 0,
          lastColumnRight: 0,
          viewportWidth: window.innerWidth,
        }
      }
      const lastRect = lastColumn.getBoundingClientRect()
      return {
        count: columns.length,
        hasContainer: true,
        scrollWidth: container.scrollWidth,
        clientWidth: container.clientWidth,
        lastColumnRight: Math.ceil(lastRect.right),
        viewportWidth: window.innerWidth,
      }
    })

    expect(result.count, `expected 6 dashboard columns, found ${result.count}`).toBe(6)
    expect(result.hasContainer, 'board grid container must exist').toBe(true)
    expect(
      result.scrollWidth,
      `six-lane dashboard should fit without horizontal overflow at 1920×1080: scrollWidth=${result.scrollWidth}, clientWidth=${result.clientWidth}`,
    ).toBeLessThanOrEqual(result.clientWidth)
    expect(
      result.lastColumnRight,
      `last dashboard column must stay inside the viewport at 1920×1080: right=${result.lastColumnRight}, viewport=${result.viewportWidth}`,
    ).toBeLessThanOrEqual(result.viewportWidth)
  })
})
