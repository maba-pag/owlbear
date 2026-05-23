/**
 * Playwright coverage for the Cockpit desktop viewport contract.
 *
 * Covers scrollable column keyboard focusability and the supported desktop
 * contract where task detail opens in a PModal task window.
 * API mocking: all routes stubbed via page.route(); no real backend required.
 */
import { test, expect, type Page } from '@playwright/test'

// ─── Constants ─────────────────────────────────────────────────────────────────

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

/**
 * 10 tasks in 'todo' — sufficient to overflow a 100px height-constrained column-body.
 * AC-1 CSS injection uses max-height: 100px so any 2+ task cards trigger scrollHeight > clientHeight.
 */
function makeManyTasksInOneColumn(): object[] {
  return Array.from({ length: 10 }, (_, i) => ({
    id: i + 1,
    title: `Todo Task ${i + 1}`,
    status: 'todo',
    priority: PRIORITIES[i % PRIORITIES.length],
    updated: '2026-05-14T00:00:00+00:00',
    tags: [],
    blocked: false,
    block_reason: null,
    claimed: false,
  }))
}

/** Single task for AC-2 desktop card-click test. */
const ONE_TASK = [
  {
    id: 1,
    title: 'Desktop Test Task',
    status: 'todo',
    priority: 'important',
    updated: '2026-05-14T00:00:00+00:00',
    tags: [],
    blocked: false,
    block_reason: null,
    claimed: false,
  },
]

const MANY_TASKS = makeManyTasksInOneColumn()

/**
 * Complete task-detail payload for ONE_TASK[0] — returned by /api/tasks/1 after card click.
 * Required fields prevent TaskFieldsEditor from crashing on depends_on.join() when the
 * detail tab renders after task selection in the desktop modal contract.
 */
const ONE_TASK_DETAIL = {
  ...ONE_TASK[0],
  body: null,
  created: '2026-05-14T00:00:00+00:00',
  claimed_at: null,
  dep_status: null,
  parent: null,
  depends_on: [] as number[],
}

// ─── API stub helper ───────────────────────────────────────────────────────────

/**
 * Stub all API routes. Catch-all registered first (LIFO: specific routes registered
 * after take precedence per Playwright route() semantics).
 */
async function stubApis(page: Page, tasks: object[] = MANY_TASKS): Promise<void> {
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
    route.fulfill({ json: { tasks, mtime: 1_715_644_800 } }),
  )
  await page.route('/api/board', (route) => route.fulfill({ json: BOARD }))
}

// ─── AC-1: Scrollable-region keyboard focusability at 3 desktop viewports ─────
//
// Contract: any [data-testid="column-body"] with scrollHeight > clientHeight must
// carry tabIndex="0" so keyboard users can scroll it (axe scrollable-region-focusable).
//
// RED: Column.tsx has no dynamic tabIndex logic — tabIndex is never set on column-body.
//      Guard assertion (scrollableCount > 0) ensures the test is never vacuously true.

test.describe('TestFromAC_ScrollableRegionFocusability', () => {
  // ── 1280x800 ─────────────────────────────────────────────────────────────────
  test.describe('at 1280x800 viewport', () => {
    test.use({ viewport: { width: 1280, height: 800 } })

    test.beforeEach(async ({ page }) => {
      await stubApis(page)
      await page.goto('/')
      // Wait for at least one task card in DOM — ensures task data is rendered
      // before CSS injection.
      await page
        .locator('[data-testid="task-card"]')
        .first()
        .waitFor({ state: 'attached', timeout: 10_000 })
    })

    // AC-4 both-branch: scrollable → tabIndex="0", non-scrollable → no tabIndex.
    test('column-body with scrollHeight > clientHeight has tabIndex="0" at 1280x800 (scrollable-region-focusable)', async ({
      page,
    }) => {
      // Scope injection: todo column-body forced to 100px (overflow) while other column-bodies
      // are forced to 200px so their 120px content (min-height from .column-empty) fits without
      // scrolling — guarantees both states are observed at all viewport sizes.
      await page.addStyleTag({
        content:
          '[data-column="todo"] [data-testid="column-body"] { max-height: 100px !important; overflow-y: auto !important; } ' +
          '[data-column]:not([data-column="todo"]) [data-testid="column-body"] { min-height: 200px !important; max-height: 200px !important; height: 200px !important; }',
      })

      const result = await page.evaluate(() => {
        const bodies = Array.from(document.querySelectorAll('[data-testid="column-body"]'))
        const scrollable = bodies.filter((el) => el.scrollHeight > el.clientHeight)
        const nonScrollable = bodies.filter((el) => el.scrollHeight <= el.clientHeight)
        const scrollableFocusable = scrollable.filter((el) => el.getAttribute('tabIndex') === '0')
        const nonScrollableWithTabIndex = nonScrollable.filter(
          (el) => el.getAttribute('tabIndex') !== null,
        )
        return {
          totalColumnBodies: bodies.length,
          scrollableCount: scrollable.length,
          nonScrollableCount: nonScrollable.length,
          scrollableFocusableCount: scrollableFocusable.length,
          nonScrollableWithTabIndexCount: nonScrollableWithTabIndex.length,
          scrollableTabIndexValues: scrollable.map((el) => el.getAttribute('tabIndex')),
          nonScrollableTabIndexValues: nonScrollable.map((el) => el.getAttribute('tabIndex')),
        }
      })

      expect(
        result.totalColumnBodies,
        '[data-testid="column-body"] elements must be in DOM',
      ).toBeGreaterThan(0)
      // Guard: both states must be observed in the same test run (AC-4 dual-branch)
      expect(
        result.scrollableCount,
        'After scoped max-height injection on todo column, at least one column-body must be scrollable',
      ).toBeGreaterThan(0)
      expect(
        result.nonScrollableCount,
        'Empty columns must remain non-scrollable after scoped injection (AC-4 both-branch guard)',
      ).toBeGreaterThan(0)
      // Positive branch: scrollable column-bodies must carry tabIndex="0"
      expect(
        result.scrollableFocusableCount,
        `All scrollable column-bodies must have tabIndex="0" for keyboard access; ` +
          `found ${result.scrollableCount} scrollable, ${result.scrollableFocusableCount} focusable. ` +
          `Actual tabIndex values: ${JSON.stringify(result.scrollableTabIndexValues)}`,
      ).toBe(result.scrollableCount)
      // Negative branch: non-scrollable column-bodies must NOT carry tabIndex
      expect(
        result.nonScrollableWithTabIndexCount,
        `Non-scrollable column-bodies must not carry tabIndex; ` +
          `found ${result.nonScrollableWithTabIndexCount} with tabIndex out of ${result.nonScrollableCount} non-scrollable. ` +
          `Actual values: ${JSON.stringify(result.nonScrollableTabIndexValues)}`,
      ).toBe(0)
    })
  })

  // ── 1440x900 ─────────────────────────────────────────────────────────────────
  test.describe('at 1440x900 viewport', () => {
    test.use({ viewport: { width: 1440, height: 900 } })

    test.beforeEach(async ({ page }) => {
      await stubApis(page)
      await page.goto('/')
      await page
        .locator('[data-testid="task-card"]')
        .first()
        .waitFor({ state: 'attached', timeout: 10_000 })
    })

    // AC-4 both-branch: scrollable → tabIndex="0", non-scrollable → no tabIndex.
    test('column-body with scrollHeight > clientHeight has tabIndex="0" at 1440x900 (scrollable-region-focusable)', async ({
      page,
    }) => {
      await page.addStyleTag({
        content:
          '[data-column="todo"] [data-testid="column-body"] { max-height: 100px !important; overflow-y: auto !important; } ' +
          '[data-column]:not([data-column="todo"]) [data-testid="column-body"] { min-height: 200px !important; max-height: 200px !important; height: 200px !important; }',
      })

      const result = await page.evaluate(() => {
        const bodies = Array.from(document.querySelectorAll('[data-testid="column-body"]'))
        const scrollable = bodies.filter((el) => el.scrollHeight > el.clientHeight)
        const nonScrollable = bodies.filter((el) => el.scrollHeight <= el.clientHeight)
        const scrollableFocusable = scrollable.filter((el) => el.getAttribute('tabIndex') === '0')
        const nonScrollableWithTabIndex = nonScrollable.filter(
          (el) => el.getAttribute('tabIndex') !== null,
        )
        return {
          totalColumnBodies: bodies.length,
          scrollableCount: scrollable.length,
          nonScrollableCount: nonScrollable.length,
          scrollableFocusableCount: scrollableFocusable.length,
          nonScrollableWithTabIndexCount: nonScrollableWithTabIndex.length,
          scrollableTabIndexValues: scrollable.map((el) => el.getAttribute('tabIndex')),
          nonScrollableTabIndexValues: nonScrollable.map((el) => el.getAttribute('tabIndex')),
        }
      })

      expect(
        result.totalColumnBodies,
        '[data-testid="column-body"] elements must be in DOM',
      ).toBeGreaterThan(0)
      expect(
        result.scrollableCount,
        'After scoped max-height injection on todo column, at least one column-body must be scrollable',
      ).toBeGreaterThan(0)
      expect(
        result.nonScrollableCount,
        'Empty columns must remain non-scrollable after scoped injection (AC-4 both-branch guard)',
      ).toBeGreaterThan(0)
      expect(
        result.scrollableFocusableCount,
        `All scrollable column-bodies must have tabIndex="0" for keyboard access; ` +
          `found ${result.scrollableCount} scrollable, ${result.scrollableFocusableCount} focusable. ` +
          `Actual tabIndex values: ${JSON.stringify(result.scrollableTabIndexValues)}`,
      ).toBe(result.scrollableCount)
      expect(
        result.nonScrollableWithTabIndexCount,
        `Non-scrollable column-bodies must not carry tabIndex; ` +
          `found ${result.nonScrollableWithTabIndexCount} with tabIndex out of ${result.nonScrollableCount} non-scrollable. ` +
          `Actual values: ${JSON.stringify(result.nonScrollableTabIndexValues)}`,
      ).toBe(0)
    })
  })

  // ── 2560x1440 ────────────────────────────────────────────────────────────────
  test.describe('at 2560x1440 viewport', () => {
    test.use({ viewport: { width: 2560, height: 1440 } })

    test.beforeEach(async ({ page }) => {
      await stubApis(page)
      await page.goto('/')
      await page
        .locator('[data-testid="task-card"]')
        .first()
        .waitFor({ state: 'attached', timeout: 10_000 })
    })

    // AC-4 both-branch: scrollable → tabIndex="0", non-scrollable → no tabIndex.
    test('column-body with scrollHeight > clientHeight has tabIndex="0" at 2560x1440 (scrollable-region-focusable)', async ({
      page,
    }) => {
      await page.addStyleTag({
        content:
          '[data-column="todo"] [data-testid="column-body"] { max-height: 100px !important; overflow-y: auto !important; } ' +
          '[data-column]:not([data-column="todo"]) [data-testid="column-body"] { min-height: 200px !important; max-height: 200px !important; height: 200px !important; }',
      })

      const result = await page.evaluate(() => {
        const bodies = Array.from(document.querySelectorAll('[data-testid="column-body"]'))
        const scrollable = bodies.filter((el) => el.scrollHeight > el.clientHeight)
        const nonScrollable = bodies.filter((el) => el.scrollHeight <= el.clientHeight)
        const scrollableFocusable = scrollable.filter((el) => el.getAttribute('tabIndex') === '0')
        const nonScrollableWithTabIndex = nonScrollable.filter(
          (el) => el.getAttribute('tabIndex') !== null,
        )
        return {
          totalColumnBodies: bodies.length,
          scrollableCount: scrollable.length,
          nonScrollableCount: nonScrollable.length,
          scrollableFocusableCount: scrollableFocusable.length,
          nonScrollableWithTabIndexCount: nonScrollableWithTabIndex.length,
          scrollableTabIndexValues: scrollable.map((el) => el.getAttribute('tabIndex')),
          nonScrollableTabIndexValues: nonScrollable.map((el) => el.getAttribute('tabIndex')),
        }
      })

      expect(
        result.totalColumnBodies,
        '[data-testid="column-body"] elements must be in DOM',
      ).toBeGreaterThan(0)
      expect(
        result.scrollableCount,
        'After scoped max-height injection on todo column, at least one column-body must be scrollable',
      ).toBeGreaterThan(0)
      expect(
        result.nonScrollableCount,
        'Empty columns must remain non-scrollable after scoped injection (AC-4 both-branch guard)',
      ).toBeGreaterThan(0)
      expect(
        result.scrollableFocusableCount,
        `All scrollable column-bodies must have tabIndex="0" for keyboard access; ` +
          `found ${result.scrollableCount} scrollable, ${result.scrollableFocusableCount} focusable. ` +
          `Actual tabIndex values: ${JSON.stringify(result.scrollableTabIndexValues)}`,
      ).toBe(result.scrollableCount)
      expect(
        result.nonScrollableWithTabIndexCount,
        `Non-scrollable column-bodies must not carry tabIndex; ` +
          `found ${result.nonScrollableWithTabIndexCount} with tabIndex out of ${result.nonScrollableCount} non-scrollable. ` +
          `Actual values: ${JSON.stringify(result.nonScrollableTabIndexValues)}`,
      ).toBe(0)
    })
  })
})

// ─── AC-2: Desktop contract — task detail in PModal at 1280px ────────────────
//
// Cockpit is a desktop-only work surface. The minimum supported proof width is
// 1200px, and task detail opens in a PModal task window instead of a phone-only
// p-sheet or a persistent PCanvas end sidebar.

test.describe('TestFromAC_DesktopTaskModalContract', () => {
  test.use({ viewport: { width: 1280, height: 800 } })

  test.beforeEach(async ({ page }) => {
    await stubApis(page, ONE_TASK)
    // Stub /api/tasks/1 detail route so task selection doesn't crash on depends_on.join().
    // Registered after stubApis() catch-all so LIFO gives this route precedence.
    await page.route('/api/tasks/1', (route) => route.fulfill({ json: ONE_TASK_DETAIL }))
    await page.goto('/')
    await page
      .locator('[data-testid="task-card"]')
      .first()
      .waitFor({ state: 'visible', timeout: 10_000 })
  })

  test('PModal task detail is visible after task card click at 1280px', async ({
    page,
  }) => {
    await page.locator('[data-testid="task-card"]').first().click()

    await expect(page.locator('p-sheet')).toHaveCount(0)
    await expect(page.locator('[data-region="sidecar"]')).toHaveCount(0)
    await expect(
      page.locator('[data-testid="task-detail-modal"]'),
      'PModal must be the visible task-detail container at the supported desktop viewport',
    ).toBeVisible()
  })

  test('task detail content area is inside the PModal after card click at 1280px', async ({
    page,
  }) => {
    await page.locator('[data-testid="task-card"]').first().click()

    const taskModal = page.locator('[data-testid="task-detail-modal"]')
    await expect(
      taskModal,
      'PModal task detail must be attached to DOM after task card click at 1280px',
    ).toBeAttached()

    await expect(
      taskModal.locator('[data-region="task-detail-content"]'),
      'task detail content area must stay inside the PModal at 1280px',
    ).toBeAttached()
  })

  test('task detail modal is absent before selection and opens after card click at 1280px', async ({
    page,
  }) => {
    await expect(
      page.locator('[data-testid="task-detail-modal"]'),
      'task detail modal must not be present before task selection',
    ).toHaveCount(0)

    await page.locator('[data-testid="task-card"]').first().click()

    await expect(
      page.locator('[data-testid="task-detail-modal"]'),
      'task detail modal must open after card click - proves click set selectedTaskId',
    ).toBeVisible()
  })

  test('PModal heading contains selected task title after task card click at 1280px', async ({
    page,
  }) => {
    await page.locator('[data-testid="task-card"]').first().click()

    await expect(
      page.locator('[data-testid="task-detail-modal"]'),
      'PModal must display selected task title "Desktop Test Task" after card click — ' +
        'proves exact task identity propagated to the modal',
    ).toContainText('Desktop Test Task')
  })

  test('task detail summary chips stay clear of the title at 1280px', async ({ page }) => {
    await page.locator('[data-testid="task-card"]').first().click()

    const summary = page.locator('[data-testid="task-detail-modal-summary"]')
    await expect(summary).toBeVisible()

    const summaryBox = await summary.boundingBox()
    const headingBox = await summary.locator('p-heading').boundingBox()
    const firstChipBox = await summary.locator('p-tag').first().boundingBox()

    expect(summaryBox).not.toBeNull()
    expect(headingBox).not.toBeNull()
    expect(firstChipBox).not.toBeNull()
    const chipClearsTitleHorizontally = firstChipBox!.x >= headingBox!.x + headingBox!.width - 2
    const chipClearsTitleVertically = firstChipBox!.y >= headingBox!.y + headingBox!.height - 2
    expect(
      chipClearsTitleHorizontally || chipClearsTitleVertically,
      'status chips must not overlap the task title at the desktop modal width',
    ).toBe(true)
    expect(firstChipBox!.x + firstChipBox!.width).toBeLessThanOrEqual(summaryBox!.x + summaryBox!.width)
  })
})
