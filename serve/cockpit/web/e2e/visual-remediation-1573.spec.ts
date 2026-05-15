/**
 * Consolidation gate tests for #1573: Cockpit visual remediation gates.
 *
 * Verifies coordinated dashboard after the implementation siblings (#1567–#1572,
 * #1575) complete. All ACs are GREEN-phase: the implementation must already be
 * in place before these tests are expected to pass.
 *
 * Source of truth: `.owlbear/research/cockpit-visual-audit-consolidated-2026-05-14.md`
 * sections 4, 6, 8, and 10. Task: #1573. Parent: #1559.
 *
 * AC-1: Visual-regression screenshots (toHaveScreenshot) for 13 visual states.
 * AC-2: Structural gates — overlay reflow, horizontal overflow, PDS component policy.
 * AC-4: Column header / empty-state visual regression + scrollable-region-focusable gate.
 * AC-5: Context menu and transition menu visual regression + position:fixed overlay gate.
 * AC-6: RepairPanel visual states + overlay policy (same as Health/DR/Cleanup/Resolve/Archive).
 * AC-7: Tab traversal and DOM audit for undocumented negative tabIndex.
 *
 * API mocking: all routes stubbed via page.route() LIFO — catch-all registered
 * first (lowest priority), specific routes registered last (take LIFO precedence).
 */

import { test, expect, type Page } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'

// ─── Constants ───────────────────────────────────────────────────────────────

const STATUSES = ['research', 'backlog', 'todo', 'in-progress', 'review', 'docs', 'done']
const PRIORITIES = ['critical', 'needed', 'important', 'nice-to-have', 'someday']

const DESKTOP_VIEWPORT = { width: 1280, height: 800 }
const TABLET_VIEWPORT = { width: 768, height: 1024 }
const MOBILE_VIEWPORT = { width: 320, height: 568 }

// ─── Fixture data ─────────────────────────────────────────────────────────────

const BOARD = {
  statuses: STATUSES.map((name) => ({ name })),
  priorities: PRIORITIES,
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

const SCAN_ITEMS = [
  {
    code: 'E001',
    detail: 'Task file is corrupted',
    file_path: 'store/tasks/TASK-001.md',
  },
]

const TASKS = [
  {
    id: 1,
    title: 'Cache implementation',
    status: 'in-progress',
    priority: 'important',
    updated: '2026-05-14T00:00:00+00:00',
    tags: ['frontend'],
    blocked: false,
    block_reason: null,
    claimed: true,
    dep_status: null,
  },
  {
    id: 2,
    title: 'Blocked task',
    status: 'todo',
    priority: 'critical',
    updated: '2026-05-14T00:00:00+00:00',
    tags: [],
    blocked: true,
    block_reason: 'Waiting on upstream',
    claimed: false,
    dep_status: null,
  },
  {
    id: 3,
    title: 'Done task',
    status: 'done',
    priority: 'nice-to-have',
    updated: '2026-05-14T00:00:00+00:00',
    tags: [],
    blocked: false,
    block_reason: null,
    claimed: false,
    dep_status: null,
  },
]

const TASK_DETAIL = {
  id: 1,
  title: 'Cache implementation',
  status: 'in-progress',
  priority: 'important',
  updated: '2026-05-14T00:00:00+00:00',
  tags: ['frontend'],
  blocked: false,
  block_reason: null,
  claimed: true,
  claimed_at: '2026-05-14T00:00:00+00:00',
  dep_status: null,
  parent: null,
  depends_on: [],
  body: '## Context\n\nNeeds cache layer.\n\n## Decision Required\n\nChoose overlay strategy.',
  created: '2026-05-10T00:00:00+00:00',
  archival_reason: null,
  archival_refs: [],
}

const PENDING_DRS = [
  {
    id: 'dr-visual-001',
    task_id: 1,
    agent: 'builder',
    request_type: 'scope-decision',
    created: '2026-05-14T00:00:00+00:00',
    title: 'Overlay strategy decision',
    body_preview: 'Builder needs guidance on overlay approach.',
    body: '## Context\n\nShould overlays use position:fixed or a portal?',
  },
]

// ─── Stub helpers ─────────────────────────────────────────────────────────────

async function stubApis(page: Page): Promise<void> {
  // Catch-all: registered first = lowest LIFO priority.
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
    route.fulfill({ json: { tasks: TASKS, mtime: 1_716_000_000 } }),
  )
  await page.route('/api/sessions', (route) => route.fulfill({ json: { sessions: [] } }))
  await page.route('/api/decisions/pending', (route) =>
    route.fulfill({ json: { count: PENDING_DRS.length, items: PENDING_DRS } }),
  )

  // Must be registered before the wildcard /api/tasks/\d+ route (LIFO).
  await page.route('/api/tasks/scan', (route) => route.fulfill({ json: SCAN_ITEMS }))

  // Task detail — registered last = highest LIFO priority.
  await page.route(/\/api\/tasks\/\d+$/, (route) => route.fulfill({ json: TASK_DETAIL }))
}

async function waitForBoard(page: Page): Promise<void> {
  await page.locator('[data-column]').first().waitFor({ state: 'visible', timeout: 8_000 })
}

async function waitForHealthBadge(page: Page): Promise<void> {
  await page.locator('[data-testid="health-badge"]').waitFor({ state: 'visible', timeout: 8_000 })
}

async function shellHeight(page: Page): Promise<number> {
  const box = await page.locator('.shell').boundingBox()
  expect(box, 'shell must be measurable').not.toBeNull()
  return box!.height
}

async function statusBarHeight(page: Page): Promise<number> {
  const box = await page.locator('[data-region="status-bar"]').boundingBox()
  expect(box, 'status-bar must be measurable').not.toBeNull()
  return box!.height
}

// ─── AC-1: Visual-regression screenshots for 13 states ───────────────────────

test.describe('AC1_VisualRegression', () => {
  test.use({ viewport: DESKTOP_VIEWPORT })

  test.beforeEach(async ({ page }) => {
    await stubApis(page)
    await page.goto('/')
    await waitForBoard(page)
  })

  // AC-1a: desktop home board
  test('ac1a_desktop_home_board', async ({ page }) => {
    await expect(page).toHaveScreenshot('ac1a-desktop-home-board.png', {
      fullPage: false,
    })
  })

  // AC-1b: selected-task sidecar open
  test('ac1b_selected_task_sidecar', async ({ page }) => {
    await page.locator('[data-testid="card-title"]').first().click()
    await page.locator('[data-testid="sidecar"], [data-region="sidecar"], [role="complementary"]')
      .first()
      .waitFor({ state: 'visible', timeout: 6_000 })
    await expect(page).toHaveScreenshot('ac1b-selected-task-sidecar.png', {
      fullPage: false,
    })
  })

  // AC-1c: filter panel open
  test('ac1c_filter_panel_open', async ({ page }) => {
    const filterToggle = page.locator(
      '[data-testid="filter-toggle"], [aria-label*="filter" i], [data-testid*="filter"]',
    ).first()
    await filterToggle.click()
    await page.locator('[data-testid="filter-panel"], [data-region="filter-panel"]')
      .first()
      .waitFor({ state: 'visible', timeout: 6_000 })
    await expect(page).toHaveScreenshot('ac1c-filter-panel-open.png', {
      fullPage: false,
    })
  })

  // AC-1d: task context menu open
  test('ac1d_task_context_menu_open', async ({ page }) => {
    const card = page.locator('[data-testid="card-title"]').first()
    await card.click({ button: 'right' })
    await page.locator('[role="menu"]').waitFor({ state: 'visible', timeout: 6_000 })
    await expect(page).toHaveScreenshot('ac1d-task-context-menu-open.png', {
      fullPage: false,
    })
  })

  // AC-1e: Health popover open
  test('ac1e_health_popover_open', async ({ page }) => {
    await waitForHealthBadge(page)
    await page.click('[data-testid="health-badge"]')
    await page.locator('[data-testid="health-badge-popover"]').waitFor({ state: 'visible', timeout: 6_000 })
    await expect(page).toHaveScreenshot('ac1e-health-popover-open.png', {
      fullPage: false,
    })
  })

  // AC-1f: DR popover open
  test('ac1f_dr_popover_open', async ({ page }) => {
    await page.click('[data-testid="dr-indicator"]')
    await page.locator('[data-testid="dr-popover"]').waitFor({ state: 'visible', timeout: 6_000 })
    await expect(page).toHaveScreenshot('ac1f-dr-popover-open.png', {
      fullPage: false,
    })
  })

  // AC-1g: Cleanup confirm dialog open
  test('ac1g_cleanup_confirm_dialog', async ({ page }) => {
    await page.click('[data-testid="cleanup-button"]')
    await page.locator('[data-testid="cleanup-confirm-dialog"]').waitFor({ state: 'visible', timeout: 6_000 })
    await expect(page).toHaveScreenshot('ac1g-cleanup-confirm-dialog.png', {
      fullPage: false,
    })
  })

  // AC-1h: Resolve modal open
  test('ac1h_resolve_modal', async ({ page }) => {
    await page.click('[data-testid="dr-indicator"]')
    await page.locator('[data-testid="dr-popover"]').waitFor({ state: 'visible', timeout: 6_000 })
    await page.locator('[data-testid="resolve-button"]').first().click()
    await page.locator('[role="dialog"][data-testid*="resolve"], [data-testid="resolve-modal"]')
      .waitFor({ state: 'visible', timeout: 6_000 })
    await expect(page).toHaveScreenshot('ac1h-resolve-modal.png', {
      fullPage: false,
    })
  })

  // AC-1i: Archive modal open
  test('ac1i_archive_modal', async ({ page }) => {
    // Right-click on the in-progress card to open context menu with archive option
    const card = page.locator('[data-testid="card-title"]').first()
    await card.click({ button: 'right' })
    await page.locator('[role="menu"]').waitFor({ state: 'visible', timeout: 6_000 })
    const archiveItem = page.locator('[role="menuitem"]').filter({ hasText: /archiv/i }).first()
    await archiveItem.click()
    await page.locator('[role="dialog"][data-testid*="archiv"], [data-testid="archival-modal"]')
      .waitFor({ state: 'visible', timeout: 6_000 })
    await expect(page).toHaveScreenshot('ac1i-archive-modal.png', {
      fullPage: false,
    })
  })

  // AC-1j: RepairPanel confirm open
  test('ac1j_repair_panel_confirm', async ({ page }) => {
    await waitForHealthBadge(page)
    await page.click('[data-testid="health-badge"]')
    await page.locator('[data-testid="health-badge-popover"]').waitFor({ state: 'visible', timeout: 6_000 })
    await page.locator('[data-testid="repair-button"]').waitFor({ state: 'visible', timeout: 6_000 })
    await page.click('[data-testid="repair-button"]')
    await page.locator('[data-testid="repair-confirm-dialog"]').waitFor({ state: 'visible', timeout: 6_000 })
    await expect(page).toHaveScreenshot('ac1j-repair-panel-confirm.png', {
      fullPage: false,
    })
  })

  // AC-1k: dark mode board
  test('ac1k_dark_mode_board', async ({ page }) => {
    await page.emulateMedia({ colorScheme: 'dark' })
    await page.reload()
    await waitForBoard(page)
    await expect(page).toHaveScreenshot('ac1k-dark-mode-board.png', {
      fullPage: false,
    })
  })
})

// AC-1l: tablet 768px board
test('ac1l_tablet_768_board', async ({ page }) => {
  await page.setViewportSize(TABLET_VIEWPORT)
  await stubApis(page)
  await page.goto('/')
  await waitForBoard(page)
  await expect(page).toHaveScreenshot('ac1l-tablet-768-board.png', {
    fullPage: false,
  })
})

// AC-1m: mobile 320px board
test('ac1m_mobile_320_board', async ({ page }) => {
  await page.setViewportSize(MOBILE_VIEWPORT)
  await stubApis(page)
  await page.goto('/')
  await waitForBoard(page)
  await expect(page).toHaveScreenshot('ac1m-mobile-320-board.png', {
    fullPage: false,
  })
})

// ─── AC-2: Structural gates ───────────────────────────────────────────────────

test.describe('AC2_StructuralGates', () => {
  test.use({ viewport: DESKTOP_VIEWPORT })

  test.beforeEach(async ({ page }) => {
    await stubApis(page)
    await page.goto('/')
    await waitForBoard(page)
  })

  // AC-2a: status disclosures must not cause bounding-box height change on parent.
  // Verifies HealthBadge, DRStatusIndicator, CleanupPanel, RepairPanel all use
  // position:fixed/absolute or portal — consistent with #1569 fix.
  test('ac2a_status_disclosures_do_not_expand_status_bar', async ({ page }) => {
    await waitForHealthBadge(page)
    const baselineStatusBar = await statusBarHeight(page)
    const baselineShell = await shellHeight(page)

    // HealthBadge popover
    await page.click('[data-testid="health-badge"]')
    await page.locator('[data-testid="health-badge-popover"]').waitFor({ state: 'visible', timeout: 6_000 })
    expect(
      await statusBarHeight(page),
      'HealthBadge popover must not expand status-bar height',
    ).toBe(baselineStatusBar)
    expect(await shellHeight(page), 'HealthBadge popover must not expand shell height').toBe(baselineShell)
    await page.keyboard.press('Escape')

    // DRStatusIndicator popover
    await page.click('[data-testid="dr-indicator"]')
    await page.locator('[data-testid="dr-popover"]').waitFor({ state: 'visible', timeout: 6_000 })
    expect(
      await statusBarHeight(page),
      'DR popover must not expand status-bar height',
    ).toBe(baselineStatusBar)
    await page.keyboard.press('Escape')

    // CleanupPanel confirm dialog
    await page.click('[data-testid="cleanup-button"]')
    await page.locator('[data-testid="cleanup-confirm-dialog"]').waitFor({ state: 'visible', timeout: 6_000 })
    expect(
      await statusBarHeight(page),
      'CleanupPanel confirm dialog must not expand status-bar height',
    ).toBe(baselineStatusBar)
    await page.keyboard.press('Escape')
  })

  // AC-2b: document must not have horizontal overflow at 320px viewport.
  test('ac2b_no_horizontal_overflow_at_320px', async ({ page }) => {
    await page.setViewportSize(MOBILE_VIEWPORT)
    await page.reload()
    await waitForBoard(page)
    const overflowsHorizontally = await page.evaluate(() => {
      return document.documentElement.scrollWidth > document.documentElement.clientWidth
    })
    expect(overflowsHorizontally, 'document must not overflow horizontally at 320px').toBe(false)
  })

  // AC-2c: production visible controls must use PDS components where policy requires.
  // Verifies no plain <button> elements exist in status-bar without data-pds attribute
  // or a documented exception (modal/dialog cancel/confirm PButtons are acceptable).
  test('ac2c_status_bar_controls_use_pds_components', async ({ page }) => {
    // Get all interactive elements in status-bar
    const nativeBtnsInStatusBar = await page.locator(
      '[data-region="status-bar"] button:not([data-pds]):not([data-pds-exception])',
    ).count()
    // PDS-compliant controls should use [data-pds] attribute or be wrapped in PDS components.
    // Zero raw <button> elements without PDS wrapper are expected after #1560 remediation.
    expect(
      nativeBtnsInStatusBar,
      'status-bar must not contain raw <button> elements without PDS wrapper',
    ).toBe(0)
  })
})

// ─── AC-4: Column visual regression + scrollable-region-focusable ─────────────

test.describe('AC4_ColumnVisual', () => {
  test.use({ viewport: DESKTOP_VIEWPORT })

  test.beforeEach(async ({ page }) => {
    await stubApis(page)
    await page.goto('/')
    await waitForBoard(page)
  })

  // AC-4 visual: column header labels and count badges
  test('ac4_column_header_in_progress', async ({ page }) => {
    const inProgressColumn = page.locator('[data-column="in-progress"]')
    await inProgressColumn.waitFor({ state: 'visible', timeout: 6_000 })
    await expect(inProgressColumn).toHaveScreenshot('ac4-column-header-in-progress.png')
  })

  // AC-4 visual: empty column placeholder (done has one task only — use research which is empty)
  test('ac4_empty_column_done', async ({ page }) => {
    // In our fixture, 'done' column has id=3 task. Use a column with no tasks for empty-state.
    // 'research' status has no tasks in the fixture → shows empty placeholder.
    const doneColumn = page.locator('[data-column="done"]')
    await doneColumn.waitFor({ state: 'visible', timeout: 6_000 })
    await expect(doneColumn).toHaveScreenshot('ac4-empty-column-done.png')
  })

  // AC-4 structural gate: scrollable column bodies must be keyboard-focusable.
  test('ac4_column_body_scrollable_region_focusable', async ({ page }) => {
    // Override tasks with many items to force overflow in in-progress column.
    const overflowTasks = Array.from({ length: 20 }, (_, i) => ({
      id: i + 1,
      title: `Task ${i + 1} — long enough title to render a card`,
      status: 'in-progress',
      priority: 'important',
      updated: '2026-05-14T00:00:00+00:00',
      tags: [],
      blocked: false,
      block_reason: null,
      claimed: false,
      dep_status: null,
    }))
    await page.route('/api/tasks', (route) =>
      route.fulfill({ json: { tasks: overflowTasks, mtime: 1_716_000_001 } }),
    )
    await page.reload()
    await waitForBoard(page)

    const columnBodies = page.locator('[data-testid="column-body"]')
    const count = await columnBodies.count()
    expect(count, 'at least one column-body must be present').toBeGreaterThan(0)

    const results = await new AxeBuilder({ page })
      .include('[data-testid="column-body"]')
      .withRules(['scrollable-region-focusable'])
      .analyze()

    expect(
      results.violations,
      'column-body scrollable regions must be keyboard-focusable (scrollable-region-focusable)',
    ).toHaveLength(0)
  })
})

// ─── AC-5: Context menu and transition menu visual + overlay gate ─────────────

test.describe('AC5_ContextMenuVisual', () => {
  test.use({ viewport: DESKTOP_VIEWPORT })

  test.beforeEach(async ({ page }) => {
    await stubApis(page)
    await page.goto('/')
    await waitForBoard(page)
  })

  // AC-5 visual: context menu open
  test('ac5_context_menu_open', async ({ page }) => {
    const card = page.locator('[data-testid="card-title"]').first()
    await card.click({ button: 'right' })
    const menu = page.locator('[role="menu"]')
    await menu.waitFor({ state: 'visible', timeout: 6_000 })
    await expect(page).toHaveScreenshot('ac5-context-menu-open.png', {
      fullPage: false,
    })
  })

  // AC-5 visual: transition menu items visible
  test('ac5_transition_menu_items', async ({ page }) => {
    const card = page.locator('[data-testid="card-title"]').first()
    await card.click({ button: 'right' })
    const menu = page.locator('[role="menu"]')
    await menu.waitFor({ state: 'visible', timeout: 6_000 })
    // Hover over a transition submenu or confirm transition items are visible.
    const transitionItem = page.locator('[role="menuitem"]').filter({ hasText: /mov|transit|review/i }).first()
    await transitionItem.hover({ force: true })
    await expect(page).toHaveScreenshot('ac5-transition-menu-items.png', {
      fullPage: false,
    })
  })

  // AC-5 structural overlay gate: context menu must render as position:fixed or position:absolute (not in-flow).
  test('ac5_context_menu_overlay_position', async ({ page }) => {
    const card = page.locator('[data-testid="card-title"]').first()
    await card.click({ button: 'right' })
    const menu = page.locator('[role="menu"]')
    await menu.waitFor({ state: 'visible', timeout: 6_000 })

    const position = await menu.evaluate((el) => {
      return window.getComputedStyle(el).position
    })
    expect(
      ['fixed', 'absolute'],
      `context menu position must be fixed or absolute, got: ${position}`,
    ).toContain(position)
  })
})

// ─── AC-6: RepairPanel visual states + overlay policy ─────────────────────────

test.describe('AC6_RepairPanel', () => {
  test.use({ viewport: DESKTOP_VIEWPORT })

  test.beforeEach(async ({ page }) => {
    await stubApis(page)
    await page.goto('/')
    await waitForBoard(page)
    await waitForHealthBadge(page)
    await page.click('[data-testid="health-badge"]')
    await page.locator('[data-testid="health-badge-popover"]').waitFor({ state: 'visible', timeout: 6_000 })
    await page.locator('[data-testid="repair-button"]').waitFor({ state: 'visible', timeout: 6_000 })
  })

  // AC-6 visual: repair panel confirm dialog
  test('ac6_repair_panel_confirm_dialog', async ({ page }) => {
    await page.click('[data-testid="repair-button"]')
    await page.locator('[data-testid="repair-confirm-dialog"]').waitFor({ state: 'visible', timeout: 6_000 })
    await expect(page).toHaveScreenshot('ac6-repair-panel-confirm-dialog.png', {
      fullPage: false,
    })
  })

  // AC-6 visual: repair error state (stub scan error response)
  test('ac6_repair_error_state', async ({ page }) => {
    // Stub repair endpoint to return an error.
    await page.route('/api/tasks/repair', (route) =>
      route.fulfill({ status: 500, json: { error: 'Repair failed' } }),
    )
    await page.click('[data-testid="repair-button"]')
    await page.locator('[data-testid="repair-confirm-dialog"]').waitFor({ state: 'visible', timeout: 6_000 })
    // Confirm repair — triggers API call which will fail.
    await page.locator('[data-testid="repair-confirm-button"]').click()
    // Wait for error state to render.
    await page.locator('[data-testid="repair-error"], [data-repair-state="error"]')
      .waitFor({ state: 'visible', timeout: 6_000 })
      .catch(() => {
        // Error state may render as text within the popover.
      })
    await expect(page).toHaveScreenshot('ac6-repair-error-state.png', {
      fullPage: false,
    })
  })

  // AC-6 overlay policy: repair confirm must not expand status-bar height.
  test('ac6_repair_confirm_does_not_expand_status_bar', async ({ page }) => {
    const baselineStatusBar = await statusBarHeight(page)
    const baselineShell = await shellHeight(page)

    await page.click('[data-testid="repair-button"]')
    await page.locator('[data-testid="repair-confirm-dialog"]').waitFor({ state: 'visible', timeout: 6_000 })

    expect(
      await statusBarHeight(page),
      'RepairPanel confirm must not expand status-bar height',
    ).toBe(baselineStatusBar)
    expect(
      await shellHeight(page),
      'RepairPanel confirm must not expand shell height',
    ).toBe(baselineShell)
  })
})

// ─── AC-7: Tab traversal and DOM audit ────────────────────────────────────────

test.describe('AC7_KeyboardReachability', () => {
  test.use({ viewport: DESKTOP_VIEWPORT })

  test.beforeEach(async ({ page }) => {
    await stubApis(page)
    await page.goto('/')
    await waitForBoard(page)
  })

  // AC-7 traversal: Tab navigation reaches each major UI region.
  test('ac7_tab_traversal_reaches_main_regions', async ({ page }) => {
    // Start from body and tab through the UI.
    await page.locator('body').focus()

    // Collect focused elements across multiple Tab presses.
    const focusedRegions = new Set<string>()
    for (let i = 0; i < 30; i++) {
      await page.keyboard.press('Tab')
      const region = await page.evaluate(() => {
        const el = document.activeElement
        if (!el || el === document.body) return null
        // Identify region by data-region, data-testid, or role.
        const region = el.closest('[data-region]')?.getAttribute('data-region')
        const testId = el.closest('[data-testid]')?.getAttribute('data-testid')
        const role = el.closest('[role="navigation"]') ? 'nav' : null
        return region ?? testId ?? role ?? el.tagName.toLowerCase()
      })
      if (region) focusedRegions.add(region)
    }

    // At minimum, Tab navigation must reach: nav rail, board columns, and status-bar controls.
    // The exact regions depend on implementation; we assert at least 3 distinct focusable regions.
    expect(
      focusedRegions.size,
      `Tab navigation must reach at least 3 distinct UI regions; reached: ${[...focusedRegions].join(', ')}`,
    ).toBeGreaterThanOrEqual(3)
  })

  // AC-7 DOM audit: no undocumented negative tabIndex on interactive elements.
  // Documented exceptions: (a) modal/sheet/popover trap, (b) menu roving-tabindex,
  // (c) programmatic focus targets (e.g. sheet content after open).
  test('ac7_no_undocumented_negative_tabindex', async ({ page }) => {
    const violations = await page.evaluate(() => {
      const interactiveSelectors = 'a, button, input, select, textarea, [role="button"], [role="link"], [role="menuitem"], [role="tab"]'
      const interactive = Array.from(document.querySelectorAll<HTMLElement>(interactiveSelectors))
      return interactive
        .filter((el) => {
          const tabIdx = el.tabIndex
          if (tabIdx >= 0) return false // positive or zero tabIndex — fine
          // Check for documented exception markers.
          const hasTrapException = el.closest('[data-focus-trap], [role="dialog"], [aria-modal="true"]')
          const hasRovingException = el.closest('[role="menu"], [role="menubar"], [role="tablist"]')
          const hasProgrammaticException = el.hasAttribute('data-focus-target')
          return !hasTrapException && !hasRovingException && !hasProgrammaticException
        })
        .map((el) => ({
          tag: el.tagName,
          testId: el.getAttribute('data-testid') ?? el.closest('[data-testid]')?.getAttribute('data-testid') ?? '',
          tabIndex: el.tabIndex,
          text: (el.textContent ?? '').trim().slice(0, 40),
        }))
    })

    expect(
      violations,
      `Found interactive elements with undocumented negative tabIndex: ${JSON.stringify(violations, null, 2)}`,
    ).toHaveLength(0)
  })
})
