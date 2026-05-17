/**
 * Playwright accessibility coverage for column-body keyboard focusability.
 *
 * Uses axe scoped to [data-testid="column-body"] so scrollable-region-focusable
 * violations are attributed to overflowing column bodies, not unrelated card UI.
 */
import { test, expect, type Page } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'

// ─── Board / task fixtures ────────────────────────────────────────────────────

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

// 20 tasks in "in-progress" to ensure the column body actually scrolls
// (scrollHeight > clientHeight at 1024x600) so the scrollable-region-focusable rule fires.
const OVERFLOW_TASKS = Array.from({ length: 20 }, (_, i) => ({
  id: i + 1,
  title: `In-Progress Task ${i + 1} — long enough title to render a full card`,
  status: 'in-progress',
  priority: 'important',
  updated: '2026-05-14T00:00:00+00:00',
  tags: [],
  blocked: false,
  block_reason: null,
  claimed: false,
}))

const TASK_DETAIL = {
  id: 1,
  title: 'In-Progress Task 1',
  status: 'in-progress',
  priority: 'important',
  updated: '2026-05-14T00:00:00+00:00',
  tags: [],
  blocked: false,
  block_reason: null,
  claimed: false,
  body: '## Context\n\nColumn body focusability test task.',
  depends_on: [],
  parent: null,
}

// ─── API stub helpers ─────────────────────────────────────────────────────────

async function stubApis(page: Page): Promise<void> {
  // Catch-all registered first (lowest priority in Playwright LIFO matching).
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
    route.fulfill({ json: { tasks: OVERFLOW_TASKS, mtime: 1_747_180_800 } }),
  )
  await page.route('/api/decisions/pending', (route) =>
    route.fulfill({ json: { count: 0, items: [] } }),
  )
  await page.route('/api/sessions', (route) =>
    route.fulfill({ json: { sessions: [] } }),
  )
  // /api/tasks/scan registered last (LIFO priority over /api/tasks/* catch-all).
  await page.route('/api/tasks/scan', (route) => route.fulfill({ json: [] }))
  await page.route('/api/tasks/*', (route) => route.fulfill({ json: TASK_DETAIL }))
}

// ─── AC-3: scrollable-region-focusable scoped to column-body ─────────────────
//
// Axe scan scoped to [data-testid="column-body"] with rule scrollable-region-focusable.
// Must assert zero violations — currently FAILS because .column-body has overflow-y: auto
// but no tabindex, so keyboard users cannot reach overflowing card content.
//
// Builder fix (#1575): add tabIndex={0} to the column-body div in Column.tsx.

test.describe('TestFromAC_ColumnBodyFocusability', () => {
  test.use({ viewport: { width: 1024, height: 600 } })

  test.beforeEach(async ({ page }) => {
    await stubApis(page)
    await page.goto('/')
    await page.locator('[data-region="workspace"]').waitFor({ state: 'visible', timeout: 8_000 })
  })

  // AC-3: all column-body scrollable regions must be keyboard-accessible (zero violations).
  // FAIL: .column-body has overflow-y: auto but no tabindex attribute in DOM.
  // The in-progress column overflows at 1024x600 with 20 tasks → axe flags the violation.
  test('all [data-testid="column-body"] scrollable regions have zero scrollable-region-focusable violations (AC-3)', async ({
    page,
  }) => {
    // Confirm the in-progress column has rendered at least one task card before scanning.
    await page
      .locator('[data-column="in-progress"] [data-testid="task-card"]')
      .first()
      .waitFor({ state: 'visible', timeout: 8_000 })

    // Scope axe to column-body elements only; check only scrollable-region-focusable rule.
    // This prevents conflation with card-level or shell-level violations.
    const results = await new AxeBuilder({ page })
      .include('[data-testid="column-body"]')
      .withRules(['scrollable-region-focusable'])
      .analyze()

    expect(
      results.violations,
      `Expected zero scrollable-region-focusable violations on [data-testid="column-body"] elements. ` +
        `Found ${results.violations.length} violation(s): ` +
        results.violations.map((v) => `${v.id} — ${v.description}`).join('; '),
    ).toEqual([])
  })

  // AC-3 scope guard (non-vacuous): at least one column-body must be provably scrollable
  // before the axe scan runs — prevents false-green where axe reports zero violations
  // trivially because no scanned element has scrollHeight > clientHeight (non-scrollable
  // regions never trigger scrollable-region-focusable).
  //
  // Pattern from responsive-contract.spec.ts: inject max-height CSS to force
  // overflow, then evaluate DOM scrollHeight vs clientHeight, then assert scrollableCount > 0.
  // The axe scan then runs on regions that are provably scrollable.
  // FAIL: in-progress column body has no tabindex → axe flags the violation.
  test('at least one [data-testid="column-body"] is scrollable before axe scan — non-vacuous AC-3 scope guard', async ({
    page,
  }) => {
    await page
      .locator('[data-testid="column-body"]')
      .first()
      .waitFor({ state: 'visible', timeout: 8_000 })

    const count = await page.locator('[data-testid="column-body"]').count()
    expect(
      count,
      'at least one [data-testid="column-body"] must be present for axe scope to be non-empty',
    ).toBeGreaterThanOrEqual(1)

    // Force overflow via CSS injection so scrollability check is reliable regardless
    // of viewport rendering and natural content height.
    await page.addStyleTag({
      content:
        '[data-testid="column-body"] { max-height: 100px !important; overflow-y: auto !important; }',
    })

    // Evaluate actual DOM scrollability: at least one column-body must have
    // scrollHeight > clientHeight — guards against vacuous zero-violation axe result.
    const scrollableCount = await page.evaluate(() => {
      const bodies = Array.from(document.querySelectorAll('[data-testid="column-body"]'))
      return bodies.filter((el) => el.scrollHeight > el.clientHeight).length
    })

    expect(
      scrollableCount,
      'After max-height CSS injection, at least one [data-testid="column-body"] must ' +
        'have scrollHeight > clientHeight — ensures axe scrollable-region-focusable ' +
        'rule has actual scrollable targets and zero violations cannot be vacuously true (AC-3)',
    ).toBeGreaterThan(0)

    // Scoped axe scan on provably-scrollable column-bodies.
    // FAIL: in-progress column body has overflow but no tabindex → axe violation.
    const results = await new AxeBuilder({ page })
      .include('[data-testid="column-body"]')
      .withRules(['scrollable-region-focusable'])
      .analyze()

    expect(
      results.violations,
      `scrollable-region-focusable scoped to ${count} column-body element(s) ` +
        `(${scrollableCount} scrollable after CSS injection): ` +
        `${results.violations.length} violation(s) found`,
    ).toEqual([])
  })
})
