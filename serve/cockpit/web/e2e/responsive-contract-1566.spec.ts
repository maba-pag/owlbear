/**
 * RED-phase Playwright E2E tests for #1566: P2-12 Cockpit responsive contract delta.
 *
 * BUILDER INSTRUCTION (#1572): Copy this file to the tracked E2E directory before implementing:
 *   cp .owlbear/scratch/1566-responsive-contract.spec.ts serve/cockpit/web/e2e/responsive-contract-1566.spec.ts
 *   git add serve/cockpit/web/e2e/responsive-contract-1566.spec.ts
 *   cd serve/cockpit/web && npm run test:e2e -- responsive-contract-1566  # must show failures
 *
 * Covers the post-#1560 responsive contract delta after the older responsive-layout proof:
 *   AC-1: scrollable-region keyboard focusability — [data-testid="column-body"] tabIndex="0"
 *         when scrollHeight > clientHeight, at 320x800, 768x1024, and 1024x768.
 *   AC-2: 320px mobile board-first contract — task detail appears inside a p-sheet custom
 *         element after card click, NOT in fixed [data-region="sidecar"] aside.
 *
 * Expected to FAIL against current implementation:
 *   AC-1: Column.tsx renders column-body with no dynamic tabIndex logic →
 *         scrollable column-bodies lack tabIndex="0" (axe scrollable-region-focusable).
 *   AC-2: Shell.tsx has no p-sheet — task detail always renders in fixed-sidecar aside →
 *         p-sheet locator finds nothing after card click.
 *
 * Technique (AC-1): page.addStyleTag injects max-height: 100px after board load so
 * column-body is forcibly scrollable regardless of viewport layout. This guarantees the
 * test is never vacuously true (scrollableCount > 0 guard assertion). The GREEN builder
 * must detect scrollable state at runtime (e.g. ResizeObserver) and set tabIndex="0".
 *
 * Viewport note (AC-2): at 320px the current Shell.css grid (56px 1fr 360px) makes
 * workspace = -96px → clamped to 0px → cards are in DOM but not visible. click({ force: true })
 * dispatches the event via Playwright without visibility check; this tests the p-sheet
 * contract rather than re-running the deleted click-reachability proof.
 *
 * API mocking: all routes stubbed via page.route() — no real backend required.
 * Proof bundle: behavioral.
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

/** Single task for AC-2 mobile card-click test. */
const ONE_TASK = [
  {
    id: 1,
    title: 'Mobile Test Task',
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
 * detail tab renders after task selection at 320px (AC-5 mobile-sheet contract).
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

// ─── AC-1: Scrollable-region keyboard focusability at 3 viewports ─────────────
//
// Contract: any [data-testid="column-body"] with scrollHeight > clientHeight must
// carry tabIndex="0" so keyboard users can scroll it (axe scrollable-region-focusable).
//
// RED: Column.tsx has no dynamic tabIndex logic — tabIndex is never set on column-body.
//      Guard assertion (scrollableCount > 0) ensures the test is never vacuously true.

test.describe('TestFromAC_ScrollableRegionFocusability', () => {
  // ── 320x800 ──────────────────────────────────────────────────────────────────
  test.describe('at 320x800 viewport', () => {
    test.use({ viewport: { width: 320, height: 800 } })

    test.beforeEach(async ({ page }) => {
      await stubApis(page)
      await page.goto('/')
      // Wait for at least one task card in DOM — ensures task data is rendered
      // before CSS injection (state: 'attached' because workspace is 0px wide at 320px)
      await page
        .locator('[data-testid="task-card"]')
        .first()
        .waitFor({ state: 'attached', timeout: 10_000 })
    })

    // AC-4 both-branch: scrollable → tabIndex="0", non-scrollable → no tabIndex.
    test('column-body with scrollHeight > clientHeight has tabIndex="0" at 320x800 (scrollable-region-focusable)', async ({
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

  // ── 768x1024 ─────────────────────────────────────────────────────────────────
  test.describe('at 768x1024 viewport', () => {
    test.use({ viewport: { width: 768, height: 1024 } })

    test.beforeEach(async ({ page }) => {
      await stubApis(page)
      await page.goto('/')
      await page
        .locator('[data-testid="task-card"]')
        .first()
        .waitFor({ state: 'attached', timeout: 10_000 })
    })

    // AC-4 both-branch: scrollable → tabIndex="0", non-scrollable → no tabIndex.
    test('column-body with scrollHeight > clientHeight has tabIndex="0" at 768x1024 (scrollable-region-focusable)', async ({
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

  // ── 1024x768 ─────────────────────────────────────────────────────────────────
  test.describe('at 1024x768 viewport', () => {
    test.use({ viewport: { width: 1024, height: 768 } })

    test.beforeEach(async ({ page }) => {
      await stubApis(page)
      await page.goto('/')
      await page
        .locator('[data-testid="task-card"]')
        .first()
        .waitFor({ state: 'attached', timeout: 10_000 })
    })

    // AC-4 both-branch: scrollable → tabIndex="0", non-scrollable → no tabIndex.
    test('column-body with scrollHeight > clientHeight has tabIndex="0" at 1024x768 (scrollable-region-focusable)', async ({
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

// ─── AC-2: Mobile board-first contract — task detail in p-sheet at 320px ───────
//
// Contract: at 320x800, after a task card is clicked, task detail must appear inside
// a p-sheet custom element. The fixed [data-region="sidecar"] aside must NOT be the
// primary detail container in mobile board-first mode.
//
// RED: Shell.tsx has no p-sheet element — task detail always renders in sidecar.
//      Both tests fail because page.locator('p-sheet') finds nothing.
//
// Builder note (AC-2): if GREEN builder (#1572) implements a controlled
// unsupported/narrow-view state instead of p-sheet, they must update this assertion
// and document the reason in #1572 task body.

test.describe('TestFromAC_MobileSheetContract', () => {
  test.use({ viewport: { width: 320, height: 800 } })

  test.beforeEach(async ({ page }) => {
    await stubApis(page, ONE_TASK)
    // Stub /api/tasks/1 detail route so task selection doesn't crash on depends_on.join().
    // Registered after stubApis() catch-all so LIFO gives this route precedence.
    await page.route('/api/tasks/1', (route) => route.fulfill({ json: ONE_TASK_DETAIL }))
    await page.goto('/')
    // Wait for task card to be in DOM (state: 'attached' — card is 0px wide at 320px
    // because workspace is 0px with current Shell.css grid)
    await page
      .locator('[data-testid="task-card"]')
      .first()
      .waitFor({ state: 'attached', timeout: 10_000 })
  })

  // RED: no p-sheet in Shell.tsx → toBeVisible() times out.
  // force: true is required because workspace is 0px wide at 320px (current broken layout)
  // and the card element is not considered visible/actionable by Playwright without it.
  test('p-sheet custom element is visible after task card click at 320x800 (mobile board-first contract)', async ({
    page,
  }) => {
    await page.locator('[data-testid="task-card"]').first().click({ force: true })

    // Mobile board-first contract (#1560): task detail must render in p-sheet,
    // NOT in the fixed [data-region="sidecar"] aside.
    // FAIL: Shell.tsx has no p-sheet — locator never resolves.
    await expect(
      page.locator('p-sheet'),
      'p-sheet custom element must be present and visible after task card click at 320px — ' +
        'mobile board-first contract requires sheet-based detail, not the fixed sidecar aside',
    ).toBeVisible()
  })

  // RED: p-sheet does not exist → toBeAttached() fails immediately.
  // Verifies that task detail panel content area is rooted inside p-sheet.
  test('task detail content area is inside p-sheet after card click at 320x800', async ({
    page,
  }) => {
    await page.locator('[data-testid="task-card"]').first().click({ force: true })

    const pSheet = page.locator('p-sheet')
    // First: p-sheet must exist — FAIL: Shell.tsx has no p-sheet.
    await expect(
      pSheet,
      'p-sheet must be attached to DOM after task card click at 320px',
    ).toBeAttached()

    // Second: task detail content area must be inside p-sheet, not in fixed sidecar.
    // FAIL: previous assertion already fails (unreachable in RED state).
    await expect(
      pSheet.locator('[data-tab-content="detail"]'),
      'task detail content area [data-tab-content="detail"] must be inside p-sheet at 320px, ' +
        'not in fixed [data-region="sidecar"] — mobile board-first contract (#1560)',
    ).toBeAttached()
  })

  // RETRY: detail-placeholder is present before click and absent after click.
  // Proves the click caused selectedTaskId to change — not static p-sheet structure.
  test('detail-placeholder inside p-sheet disappears after task card click at 320x800 (click-dependent selection signal)', async ({
    page,
  }) => {
    // Before click: selectedTaskId === null -> placeholder present inside p-sheet.
    await expect(
      page.locator('p-sheet [data-testid="detail-placeholder"]'),
      'detail-placeholder must be present inside p-sheet before any card click (selectedTaskId === null)',
    ).toBeAttached()

    // Trigger selection - force:true bypasses 0px-workspace visibility constraint.
    await page.locator('[data-testid="task-card"]').first().click({ force: true })

    // After click: selectedTaskId === 1 -> placeholder removed from DOM.
    // FAILS if the click did not propagate to onSelectTask / if selectedTaskId stays null.
    await expect(
      page.locator('p-sheet [data-testid="detail-placeholder"]'),
      'detail-placeholder must be removed from p-sheet DOM after card click - ' +
        'proves click set selectedTaskId (click-dependent, not static structure)',
    ).not.toBeAttached()
  })

  // RETRY: p-sheet heading changes from "No task selected" after card click.
  // Proves the selected-task signal propagated to the mobile sheet heading.
  test('p-sheet heading changes from "No task selected" after task card click at 320x800 (click-dependent selection signal)', async ({
    page,
  }) => {
    const heading = page.locator('p-sheet [data-region="sidecar-header"] h2')

    // Before click: default heading text when no task is selected.
    await expect(
      heading,
      'p-sheet heading must show "No task selected" before any card click',
    ).toHaveText('No task selected')

    // Trigger selection - force:true bypasses 0px-workspace visibility constraint.
    await page.locator('[data-testid="task-card"]').first().click({ force: true })

    // After click: selectedTaskId === 1 -> heading derives from selected task title.
    // FAILS if click did not set selectedTaskId or heading is not task-identity-specific.
    await expect(
      heading,
      'p-sheet heading must display selected task title "Mobile Test Task" after card click — ' +
        'proves exact task identity propagated to mobile sheet, not just state change from placeholder',
    ).toHaveText('Mobile Test Task')
  })
})
