/**
 * WCAG 2.1 AA Playwright accessibility sweep for Cockpit surfaces.
 *
 * Covers the board, task detail modal, DR and health popovers, FilterPanel,
 * ResolveModal, ArchivalModal, ConfirmDialog, CleanupPanel, and RepairPanel.
 * Route mocks use Playwright LIFO ordering: catch-all first, specific routes last.
 */

import { test, expect, type Page } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'

// ─── Constants ────────────────────────────────────────────────────────────────

/** WCAG 2.1 AA tag set for all AC1 axe scans. */
const WCAG_TAGS = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'] as const

const STATUSES = ['research', 'backlog', 'todo', 'in-progress', 'review', 'docs', 'done']
const PRIORITIES = ['critical', 'needed', 'important', 'nice-to-have', 'someday']

// ─── Fixture data ─────────────────────────────────────────────────────────────

const BOARD = {
  statuses: STATUSES.map((name) => ({ name })),
  priorities: PRIORITIES,
  /**
   * 'in-progress' includes 'archived' so ArchivalModal can be triggered from
   * the context menu transition without needing a separate "done" task.
   * 'in-progress' includes 'todo' so the backward-move ConfirmDialog is reachable.
   */
  valid_transitions: {
    research: ['backlog'],
    backlog: ['research', 'todo'],
    todo: ['backlog', 'in-progress'],
    'in-progress': ['todo', 'review', 'archived'],
    review: ['in-progress', 'docs'],
    docs: ['review', 'done'],
    done: [],
  } as Record<string, string[]>,
}

/** Single in-progress task: claimed so unclaim action is available in TaskActions. */
const TASKS = [
  {
    id: 1,
    title: 'Implement cache layer',
    status: 'in-progress',
    priority: 'important',
    updated: '2026-05-16T00:00:00+00:00',
    tags: ['backend'],
    blocked: false,
    block_reason: null,
    claimed: true,
  },
  {
    id: 2,
    title: 'Fix authentication bug',
    status: 'backlog',
    priority: 'critical',
    updated: '2026-05-16T00:00:00+00:00',
    tags: [],
    blocked: false,
    block_reason: null,
    claimed: false,
  },
]

const TASK_DETAIL = {
  id: 1,
  title: 'Implement cache layer',
  status: 'in-progress',
  priority: 'important',
  updated: '2026-05-16T00:00:00+00:00',
  tags: ['backend'],
  blocked: false,
  block_reason: null,
  claimed: true,
  claimed_at: '2026-05-16T00:00:00+00:00',
  dep_status: null,
  parent: null,
  depends_on: [],
  body: '## Context\n\nCache implementation needed.',
  created: '2026-05-10T00:00:00+00:00',
}

const PENDING_DRS = [
  {
    id: 'dr-sweep-001',
    task_id: 1,
    agent: 'builder',
    request_type: 'scope-decision',
    created: '2026-05-16T00:00:00+00:00',
    title: 'Confirm caching strategy',
    body_preview: 'Builder needs guidance on caching.',
    body: '## Context\n\nShould we use Redis or in-memory cache?',
  },
]

/** Scan items: ensure HealthBadge shows data-health="red" and RepairPanel appears. */
const SCAN_ITEMS = [
  {
    code: 'E001',
    detail: 'Task file is corrupted',
    file_path: 'store/tasks/TASK-001.md',
  },
]

// ─── Stub helpers ─────────────────────────────────────────────────────────────

/**
 * Register all API stubs via page.route().
 * LIFO: catch-all first (lowest priority), specific routes last (highest priority).
 */
async function stubApis(page: Page): Promise<void> {
  // Catch-all — lowest LIFO priority, overridden by all routes below.
  await page.route('/api/**', (route) => route.fulfill({ status: 200, json: {} }))

  // SSE stream — empty body prevents connection hang.
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
    route.fulfill({ json: { tasks: TASKS, mtime: 1_716_000_000 } }),
  )
  await page.route('/api/sessions', (route) => route.fulfill({ json: { sessions: [] } }))
  await page.route('/api/decisions/pending', (route) =>
    route.fulfill({ json: { count: PENDING_DRS.length, items: PENDING_DRS } }),
  )

  // /api/tasks/scan — provides scan items so HealthBadge renders red and RepairPanel
  // shows the "Repair" button. Must be registered before /api/tasks/:id (LIFO).
  await page.route('/api/tasks/scan', (route) => route.fulfill({ json: SCAN_ITEMS }))

  // Task detail — catch-all for /api/tasks/1, /api/tasks/2, etc.
  await page.route(/\/api\/tasks\/\d+$/, (route) => route.fulfill({ json: TASK_DETAIL }))
}

/** Wait for at least one task card to become visible. */
async function waitForCards(page: Page): Promise<void> {
  await page
    .locator('[data-testid="task-card"]')
    .first()
    .waitFor({ state: 'visible', timeout: 8_000 })
}

/** Wait for HealthBadge to appear (requires scan poll to complete). */
async function waitForHealthBadge(page: Page): Promise<void> {
  await page
    .locator('[data-testid="health-badge"]')
    .waitFor({ state: 'visible', timeout: 8_000 })
}

async function openWorkspaceStatus(page: Page): Promise<void> {
  await waitForHealthBadge(page)
  await page.locator('[data-testid="health-badge"]').click()
  await page.locator('[data-testid="health-badge-popover"]').waitFor({ state: 'visible', timeout: 3_000 })
}

// ─── AC1: WCAG 2.1 AA axe scans on all required surfaces ─────────────────────
//
// All tests use .withTags(WCAG_TAGS) to scope axe to WCAG 2.1 AA rules only.
// Each test asserts zero violations on a distinct UI surface.
//
// RED reasons:
//   - RepairPanel span-onClick violation (interactive-supports-focus, wcag2a) is
//     reproducible and will cause that test to fail immediately.
//   - Other surfaces have not been WCAG-tag-scanned before; violations discovered
//     at runtime cause failures until the builder remediates them.

test.describe('TestFromAC_WcagSweep', () => {
  test.use({ viewport: { width: 1024, height: 768 } })

  test.beforeEach(async ({ page }) => {
    await stubApis(page)
    await page.goto('/')
    await waitForCards(page)
  })

  // ── Surface 1: board view ──────────────────────────────────────────────────
  // The board view is the primary surface. Cards, columns, status-bar controls,
  // and the filter toggle must all pass WCAG 2.1 AA at 1024px.
  test('board view passes wcag2.1 aa axe scan (AC1)', async ({ page }) => {
    // Assert at least one card is rendered — no silent empty-board false-green.
    await expect(
      page.locator('[data-testid="task-card"]').first(),
      'at least one task card must be visible before scanning board view',
    ).toBeVisible()

    const results = await new AxeBuilder({ page }).withTags(WCAG_TAGS).analyze()
    expect(results.violations, formatViolations(results.violations)).toEqual([])
  })

  // ── Surface 2: task detail modal ──────────────────────────────────────────
  // The modal opens when a task card is clicked. The detail panel includes
  // TaskFieldsEditor, TaskActions, and the metadata accordion.
  test('task detail modal passes wcag2.1 aa axe scan (AC1)', async ({ page }) => {
    const card = page.locator('[data-testid="task-card"]').first()
    await card.waitFor({ state: 'visible', timeout: 5_000 })
    await card.click()

    // Prove modal rendered by asserting the title field is visible.
    await expect(
      page.locator('[data-field="title"]'),
      'task detail modal [data-field="title"] must be visible before axe scan',
    ).toBeVisible({ timeout: 5_000 })

    const results = await new AxeBuilder({ page }).withTags(WCAG_TAGS).analyze()
    expect(results.violations, formatViolations(results.violations)).toEqual([])
  })

  // ── Surface 3: Decisions workspace ────────────────────────────────────────
  // Decisions are route-owned; pending DRs resolve from the Decisions workspace.
  test('decisions workspace passes wcag2.1 aa axe scan (AC1)', async ({ page }) => {
    await page.goto('/decisions')
    await expect(page.locator('[data-testid="decisions-page"]')).toBeVisible({ timeout: 8_000 })
    await expect(page.locator(`[data-testid="dr-item-${PENDING_DRS[0].id}"]`)).toBeVisible({ timeout: 8_000 })

    const results = await new AxeBuilder({ page }).withTags(WCAG_TAGS).analyze()
    expect(results.violations, formatViolations(results.violations)).toEqual([])
  })

  // ── Surface 4: Workspace Status popover ───────────────────────────────────
  // The Workspace Status popover lists scan issues and exposes care actions.
  test('workspace status popover passes wcag2.1 aa axe scan (AC1)', async ({ page }) => {
    await waitForHealthBadge(page)

    const badge = page.locator('[data-testid="health-badge"]')
    await expect(
      badge,
      'health-badge must have data-health="red" — /api/tasks/scan must have returned scan items',
    ).toHaveAttribute('data-health', 'red')

    await badge.click()
    await page.locator('[data-testid="health-badge-popover"]').waitFor({ state: 'visible', timeout: 3_000 })

    const results = await new AxeBuilder({ page }).withTags(WCAG_TAGS).analyze()
    expect(results.violations, formatViolations(results.violations)).toEqual([])
  })

  // ── Surface 5: FilterPanel (open) ─────────────────────────────────────────
  // The FilterPanel is visible when panelOpen=true. It contains PDS search,
  // select, and multi-select inputs. The panel is toggled by filter-toggle.
  test('filter panel open state passes wcag2.1 aa axe scan (AC1)', async ({ page }) => {
    const filterToggle = page.locator('[data-testid="filter-toggle"]')
    await filterToggle.waitFor({ state: 'visible', timeout: 5_000 })
    await filterToggle.click()

    // Assert the filter panel is visible before scanning.
    await expect(
      page.locator('[data-testid="filter-panel"]'),
      'filter-panel must be visible after clicking filter-toggle',
    ).toBeVisible({ timeout: 3_000 })

    const results = await new AxeBuilder({ page }).withTags(WCAG_TAGS).analyze()
    expect(results.violations, formatViolations(results.violations)).toEqual([])
  })

  // ── Surface 6: ResolveModal ───────────────────────────────────────────────
  // ResolveModal opens when a DR item is clicked from the Decisions workspace.
  // The modal renders as a custom div with role="dialog" in the Shell.
  test('resolve modal passes wcag2.1 aa axe scan (AC1)', async ({ page }) => {
    await page.goto('/decisions')
    await expect(page.locator('[data-testid="decisions-page"]')).toBeVisible({ timeout: 8_000 })

    const drItem = page.locator(`[data-testid="dr-item-${PENDING_DRS[0].id}"]`)
    await drItem.waitFor({ state: 'visible', timeout: 3_000 })
    await drItem.click()

    // ResolveModal must be open — no conditional skip.
    await page.locator('[data-testid="resolve-modal"]').waitFor({ state: 'visible', timeout: 3_000 })

    const results = await new AxeBuilder({ page }).withTags(WCAG_TAGS).analyze()
    expect(results.violations, formatViolations(results.violations)).toEqual([])
  })

  // ── Surface 7: ArchivalModal ──────────────────────────────────────────────
  // ArchivalModal opens when the user selects "archived" from the task context menu.
  // The context menu appears on right-click of a task card.
  test('archival modal passes wcag2.1 aa axe scan (AC1)', async ({ page }) => {
    const card = page.locator('[data-testid="task-card"][data-id="1"]')
    await card.waitFor({ state: 'visible', timeout: 8_000 })

    // Right-click the task card to open the context menu.
    await card.click({ button: 'right' })
    const contextMenu = page.locator('[data-testid="context-menu"]')
    await contextMenu.waitFor({ state: 'visible', timeout: 5_000 })

    // Click the 'archived' transition item — triggers ArchivalModal.
    await page.locator('[data-testid="transition-item"][data-status="archived"]').click()

    // ArchivalModal must be open — assert submit button is visible.
    await page
      .locator('[data-testid="archival-modal"]')
      .waitFor({ state: 'attached', timeout: 5_000 })
    await page
      .locator('[data-testid="archival-submit"]')
      .waitFor({ state: 'visible', timeout: 5_000 })

    const results = await new AxeBuilder({ page }).withTags(WCAG_TAGS).analyze()
    expect(results.violations, formatViolations(results.violations)).toEqual([])
  })

  // ── Surface 8: ConfirmDialog ──────────────────────────────────────────────
  // ConfirmDialog opens from the TaskActions component when "Move Backward" is clicked.
  // The task must be in-progress with a valid backward transition (todo ∈ valid_transitions).
  test('confirm dialog passes wcag2.1 aa axe scan (AC1)', async ({ page }) => {
    const card = page.locator('[data-testid="task-card"][data-id="1"]')
    await card.waitFor({ state: 'visible', timeout: 8_000 })
    await card.click()

    // Wait for task detail modal to open.
    await expect(
      page.locator('[data-field="title"]'),
      'task detail modal [data-field="title"] must be visible before clicking move-backward',
    ).toBeVisible({ timeout: 5_000 })

    // Click "Move Backward" to open ConfirmDialog.
    const moveBackwardBtn = page.locator('[data-testid="move-backward"]')
    await moveBackwardBtn.waitFor({ state: 'visible', timeout: 5_000 })
    await moveBackwardBtn.click()

    // ConfirmDialog must be open — no conditional skip.
    await page
      .locator('[data-testid="confirm-dialog"]')
      .waitFor({ state: 'attached', timeout: 5_000 })

    const results = await new AxeBuilder({ page }).withTags(WCAG_TAGS).analyze()
    expect(results.violations, formatViolations(results.violations)).toEqual([])
  })

  // ── Surface 9: CleanupPanel confirm dialog ────────────────────────────────
  // CleanupPanel's confirm dialog opens from Workspace Status.
  test('cleanup panel confirm dialog passes wcag2.1 aa axe scan (AC1)', async ({ page }) => {
    await openWorkspaceStatus(page)

    const cleanupButton = page.locator('[data-testid="cleanup-button"]')
    await cleanupButton.waitFor({ state: 'visible', timeout: 5_000 })
    await cleanupButton.click()

    // CleanupPanel confirm dialog must be visible.
    await expect(
      page.locator('[data-testid="cleanup-confirm-dialog"]'),
      'cleanup-confirm-dialog must be visible after clicking cleanup-button',
    ).toBeVisible({ timeout: 3_000 })

    const results = await new AxeBuilder({ page }).withTags(WCAG_TAGS).analyze()
    expect(results.violations, formatViolations(results.violations)).toEqual([])
  })

  // ── Surface 10: RepairPanel confirm dialog ────────────────────────────────
  // RepairPanel confirm dialog opens from Workspace Status after scan issues load.
  //
  // KNOWN RED: `<span data-testid="repair-confirm-btn" onClick>` in RepairPanel.tsx
  // carries a click handler on a non-interactive <span> element. Axe flags this as
  // an `interactive-supports-focus` violation under wcag2a:
  //   SC 2.1.1 (keyboard): click target not keyboard reachable.
  // Test fails until the span is replaced with a proper interactive element.
  test('repair panel confirm dialog passes wcag2.1 aa axe scan (AC1)', async ({ page }) => {
    await waitForHealthBadge(page)

    const badge = page.locator('[data-testid="health-badge"]')
    await expect(
      badge,
      'health-badge must have data-health="red" before clicking to expose repair-button',
    ).toHaveAttribute('data-health', 'red')

    await openWorkspaceStatus(page)

    const repairButton = page.locator('[data-testid="repair-button"]')
    await repairButton.waitFor({ state: 'visible', timeout: 3_000 })
    await repairButton.click()

    // RepairPanel confirm dialog must be visible — no conditional skip.
    await expect(
      page.locator('[data-testid="repair-confirm-dialog"]'),
      'repair-confirm-dialog must be visible after clicking repair-button',
    ).toBeVisible({ timeout: 3_000 })

    // AC1: KNOWN FAILING — <span onClick> on repair-confirm-btn violates
    // interactive-supports-focus (wcag2a / SC 2.1.1). Builder must remediate.
    const results = await new AxeBuilder({ page }).withTags(WCAG_TAGS).analyze()
    expect(results.violations, formatViolations(results.violations)).toEqual([])
  })
})

// ─── Violation formatter ──────────────────────────────────────────────────────

/**
 * Format axe violations into a human-readable string for assertion messages.
 * Makes test failure output actionable — shows rule ID, impact, and element.
 */
function formatViolations(violations: Array<{
  id: string
  impact?: string | null
  help: string
  nodes: Array<{ html: string }>
}>): string {
  if (violations.length === 0) {
    return 'no violations'
  }
  return violations
    .map(
      (v) =>
        `[${v.impact ?? 'unknown'} — ${v.id}] ${v.help}\n  ${v.nodes.map((n) => n.html).join('\n  ')}`,
    )
    .join('\n\n')
}
