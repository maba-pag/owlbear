/**
 * RED phase Playwright E2E tests for #1395: P3-05 Cockpit accessibility and PDS verification gate
 *
 * BUILDER INSTRUCTION (#1396): Copy this file to the tracked E2E directory and verify tests FAIL:
 *   cp .owlbear/scratch/1395-accessibility.spec.ts serve/cockpit/web/e2e/accessibility-1395.spec.ts
 *   git add serve/cockpit/web/e2e/accessibility-1395.spec.ts
 *   npm run test:e2e -- accessibility-1395  # must show failures before implementing
 *
 * AC1 (td:2): @axe-core/playwright checks on board view, task detail edit,
 *             decision resolution, and repair flow pages at 1024px viewport.
 *             @axe-core/playwright must be added as a devDependency.
 * AC5 (td:2): Accessibility-specific viewport checks at 320px, 768px, 1024px, and 1440px.
 *             Verifies task cards are keyboard-reachable and landmark regions are present.
 *             Does NOT duplicate layout/geometry/sidecar tests from responsive-layout-1391.spec.ts.
 *
 * RED reasons:
 *   1. @axe-core/playwright is not yet a devDependency — all tests fail at import resolution.
 *   2. When installed: Card divs have no tabIndex or ARIA role → axe flags violations.
 *   3. Card keyboard reachability tests fail: Card has no tabIndex → Tab skips all cards.
 *
 * Counterpart implementation task: #1396.
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

const TASKS = [
  {
    id: 1,
    title: 'Implement cache layer',
    status: 'backlog',
    priority: 'important',
    updated: '2026-05-10T00:00:00+00:00',
    tags: ['backend'],
    blocked: false,
    block_reason: null,
    claimed: false,
  },
  {
    id: 2,
    title: 'Fix authentication bug',
    status: 'in-progress',
    priority: 'critical',
    updated: '2026-05-10T00:00:00+00:00',
    tags: [],
    blocked: false,
    block_reason: null,
    claimed: true,
  },
]

const TASK_DETAIL = {
  id: 1,
  title: 'Implement cache layer',
  status: 'backlog',
  priority: 'important',
  updated: '2026-05-10T00:00:00+00:00',
  tags: ['backend'],
  blocked: false,
  block_reason: null,
  claimed: false,
  body: '## Context\n\nCache implementation needed.',
  depends_on: [],
  parent: null,
}

const PENDING_DRS = [
  {
    id: 'dr-a11y-001',
    task_id: 1,
    agent: 'builder',
    request_type: 'scope-decision',
    created: '2026-05-10T00:00:00+00:00',
    title: 'Confirm caching strategy',
    body_preview: 'Builder needs guidance on caching.',
    body: '## Context\n\nShould we use Redis or in-memory cache?',
  },
]

const SCAN_ITEMS = [
  {
    code: 'E001',
    detail: 'Missing required field',
    file_path: 'store/tasks/TASK-001.md',
  },
]

// ─── API stub helpers ─────────────────────────────────────────────────────────

async function stubApis(page: Page): Promise<void> {
  // Catch-all registered first (lowest priority in Playwright LIFO matching).
  // Specific routes below override it for their paths.
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
  await page.route('/api/tasks/*', (route) => route.fulfill({ json: TASK_DETAIL }))
  await page.route('/api/sessions', (route) =>
    route.fulfill({ json: { sessions: [] } }),
  )
  // Live endpoint: /api/decisions/pending (GET) → {count, items}
  await page.route('/api/decisions/pending', (route) =>
    route.fulfill({ json: { count: PENDING_DRS.length, items: PENDING_DRS } }),
  )
  // Live endpoint: /api/tasks/scan (POST) → ScanItem[]
  // Registered last so it takes LIFO priority over /api/tasks/* for the /scan path.
  await page.route('/api/tasks/scan', (route) => route.fulfill({ json: SCAN_ITEMS }))
}

// ─── AC1: axe-core accessibility scans at 1024px ─────────────────────────────
//
// Each test runs an axe scan on a distinct workflow page and asserts 0 violations.
// All tests fail until:
//   a) @axe-core/playwright is installed (import currently fails = module not found)
//   b) #1396 adds keyboard semantics so axe reports 0 violations

test.describe('TestFromAC_AxeA11y', () => {
  test.use({ viewport: { width: 1024, height: 768 } })

  test.beforeEach(async ({ page }) => {
    await stubApis(page)
    await page.goto('/')
    await page.locator('[data-region="workspace"]').waitFor({ state: 'visible', timeout: 8_000 })
  })

  // AC1: board view — primary surface with all task columns and cards
  test('board view has zero axe accessibility violations at 1024px (AC1)', async ({ page }) => {
    await page
      .locator('[data-testid="task-card"]')
      .first()
      .waitFor({ state: 'attached', timeout: 5_000 })
      .catch(() => {})
    const results = await new AxeBuilder({ page }).analyze()
    expect(results.violations).toEqual([])
  })

  // AC1: task detail edit — sidecar detail panel with editable fields
  test('task detail edit view has zero axe accessibility violations at 1024px (AC1)', async ({
    page,
  }) => {
    const card = page.locator('[data-testid="task-card"]').first()
    await card.waitFor({ state: 'visible', timeout: 5_000 })
    await card.click()
    // Prove task-detail surface rendered: sidecar must show task data, not placeholder.
    // Test must fail if the sidecar cannot be rendered from stub data.
    await expect(
      page.locator('[data-testid="detail-placeholder"]'),
      'sidecar must show task data before axe scan — placeholder must not be visible',
    ).not.toBeVisible({ timeout: 5_000 })
    const results = await new AxeBuilder({ page }).analyze()
    expect(results.violations).toEqual([])
  })

  // AC1: decision resolution — ResolveModal open with DR body visible
  test('decision resolution view has zero axe accessibility violations at 1024px (AC1)', async ({
    page,
  }) => {
    // Prove DR surface rendered: DR indicator must be visible and show count > 0.
    // Test must fail if /api/decisions/pending did not return items.
    const drIndicator = page.locator('[data-testid="dr-indicator"]')
    await drIndicator.waitFor({ state: 'visible', timeout: 5_000 })
    await expect(
      drIndicator,
      'DR indicator must show attention status — /api/decisions/pending must have returned items',
    ).toHaveAttribute('data-status', 'attention')
    // Open DR popover and click the first DR item to open ResolveModal.
    await drIndicator.click()
    await page.locator('[data-testid="dr-popover"]').waitFor({ state: 'visible', timeout: 3_000 })
    const drItem = page.locator(`[data-testid="dr-item-${PENDING_DRS[0].id}"]`)
    await drItem.waitFor({ state: 'visible', timeout: 3_000 })
    await drItem.click()
    // ResolveModal must be open before scanning — no conditional skip allowed.
    await page.locator('[data-testid="resolve-modal"]').waitFor({ state: 'visible', timeout: 3_000 })
    const results = await new AxeBuilder({ page }).analyze()
    expect(results.violations).toEqual([])
  })

  // AC1: repair flow — HealthBadge popover open with repair panel visible
  test('repair flow view has zero axe accessibility violations at 1024px (AC1)', async ({
    page,
  }) => {
    // Prove repair surface rendered: HealthBadge must be visible and show issues.
    // Test must fail if /api/tasks/scan did not return scan items.
    const badge = page.locator('[data-testid="health-badge"]')
    await badge.waitFor({ state: 'visible', timeout: 5_000 })
    await expect(
      badge,
      'HealthBadge must show data-health=red — /api/tasks/scan must have returned scan items',
    ).toHaveAttribute('data-health', 'red')
    // Open the popover — no conditional skip allowed.
    await badge.click()
    await page.locator('[data-testid="health-badge-popover"]').waitFor({ state: 'visible', timeout: 3_000 })
    const results = await new AxeBuilder({ page }).analyze()
    expect(results.violations).toEqual([])
  })
})

// ─── AC5: Accessibility-specific viewport checks ──────────────────────────────
//
// Tests keyboard reachability (tabIndex) and landmark presence at four breakpoints.
// Layout, geometry, overflow, and sidecar proportion tests are in responsive-layout-1391.spec.ts.
//
// All card-keyboard tests fail: Card is a <div> with no tabIndex → Tab skips it entirely.
// Landmark tests fail if Shell only uses data-region attrs (no semantic HTML landmarks).

test.describe('TestFromAC_A11yViewport', () => {
  // ─── 320px ─────────────────────────────────────────────────────────────────

  test.describe('at 320px viewport (AC5)', () => {
    test.use({ viewport: { width: 320, height: 800 } })

    test.beforeEach(async ({ page }) => {
      await stubApis(page)
      await page.goto('/')
      await page
        .locator('[data-region="status-bar"]')
        .waitFor({ state: 'attached', timeout: 8_000 })
    })

    // Tab through the page 20 times; a task card must receive focus at some point.
    // Fails: Card <div> has no tabIndex → browser Tab order skips it.
    test('task cards are reachable via Tab key at 320px (AC5)', async ({ page }) => {
      await page
        .locator('[data-testid="task-card"]')
        .first()
        .waitFor({ state: 'attached', timeout: 5_000 })
        .catch(() => {})
      for (let i = 0; i < 20; i++) {
        await page.keyboard.press('Tab')
      }
      await expect(
        page.locator('[data-testid="task-card"]:focus'),
        'at least one task card must be tab-reachable at 320px',
      ).toBeVisible()
    })

    test('at least one ARIA landmark region exists at 320px (AC5)', async ({ page }) => {
      // WCAG 2.1 SC 1.3.6: landmark regions required for screen-reader orientation.
      const landmark = page.locator(
        '[role="main"], main, [role="navigation"], nav, [role="banner"], header[role], [role="complementary"], aside',
      )
      await expect(
        landmark.first(),
        'at least one semantic landmark region must be present at 320px',
      ).toBeAttached()
    })
  })

  // ─── 768px ─────────────────────────────────────────────────────────────────

  test.describe('at 768px viewport (AC5)', () => {
    test.use({ viewport: { width: 768, height: 1024 } })

    test.beforeEach(async ({ page }) => {
      await stubApis(page)
      await page.goto('/')
      await page
        .locator('[data-region="status-bar"]')
        .waitFor({ state: 'attached', timeout: 8_000 })
    })

    test('task cards are reachable via Tab key at 768px (AC5)', async ({ page }) => {
      await page
        .locator('[data-testid="task-card"]')
        .first()
        .waitFor({ state: 'attached', timeout: 5_000 })
        .catch(() => {})
      for (let i = 0; i < 20; i++) {
        await page.keyboard.press('Tab')
      }
      await expect(
        page.locator('[data-testid="task-card"]:focus'),
        'at least one task card must be tab-reachable at 768px',
      ).toBeVisible()
    })

    test('at least one ARIA landmark region exists at 768px (AC5)', async ({ page }) => {
      const landmark = page.locator(
        '[role="main"], main, [role="navigation"], nav, [role="banner"], header[role], [role="complementary"], aside',
      )
      await expect(landmark.first()).toBeAttached()
    })
  })

  // ─── 1024px ────────────────────────────────────────────────────────────────

  test.describe('at 1024px viewport (AC5)', () => {
    test.use({ viewport: { width: 1024, height: 768 } })

    test.beforeEach(async ({ page }) => {
      await stubApis(page)
      await page.goto('/')
      await page
        .locator('[data-region="workspace"]')
        .waitFor({ state: 'visible', timeout: 8_000 })
    })

    test('task cards are reachable via Tab key at 1024px (AC5)', async ({ page }) => {
      await page
        .locator('[data-testid="task-card"]')
        .first()
        .waitFor({ state: 'visible', timeout: 5_000 })
        .catch(() => {})
      for (let i = 0; i < 20; i++) {
        await page.keyboard.press('Tab')
      }
      await expect(
        page.locator('[data-testid="task-card"]:focus'),
        'at least one task card must be tab-reachable at 1024px',
      ).toBeVisible()
    })

    test('at least one ARIA landmark region exists at 1024px (AC5)', async ({ page }) => {
      const landmark = page.locator(
        '[role="main"], main, [role="navigation"], nav, [role="banner"], header[role], [role="complementary"], aside',
      )
      await expect(landmark.first()).toBeAttached()
    })
  })

  // ─── 1440px ────────────────────────────────────────────────────────────────

  test.describe('at 1440px viewport (AC5)', () => {
    test.use({ viewport: { width: 1440, height: 900 } })

    test.beforeEach(async ({ page }) => {
      await stubApis(page)
      await page.goto('/')
      await page
        .locator('[data-region="workspace"]')
        .waitFor({ state: 'visible', timeout: 8_000 })
    })

    test('task cards are reachable via Tab key at 1440px (AC5)', async ({ page }) => {
      await page
        .locator('[data-testid="task-card"]')
        .first()
        .waitFor({ state: 'visible', timeout: 5_000 })
        .catch(() => {})
      for (let i = 0; i < 20; i++) {
        await page.keyboard.press('Tab')
      }
      await expect(
        page.locator('[data-testid="task-card"]:focus'),
        'at least one task card must be tab-reachable at 1440px',
      ).toBeVisible()
    })

    test('at least one ARIA landmark region exists at 1440px (AC5)', async ({ page }) => {
      const landmark = page.locator(
        '[role="main"], main, [role="navigation"], nav, [role="banner"], header[role], [role="complementary"], aside',
      )
      await expect(landmark.first()).toBeAttached()
    })
  })
})
