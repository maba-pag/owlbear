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

  // AC-2c-v2: Non-circular enumeration gate — supersedes the circular data-pds-exception proof.
  // Shell.tsx MutationObserver auto-stamps ALL native buttons in status-bar with data-pds-exception
  // on mount, making the NOT([data-pds-exception]) locator always return 0 (circular self-certification).
  // This v2 test enumerates ALL native <button> and <input> elements across the full rendered page
  // (base state, no overlays), excludes only true PDS internals ([data-pds]), and validates each
  // control against the known exception set by testId rather than by a marker that the app stamps
  // automatically. Any new native control without a documented testId causes failure.
  test('ac2c_v2_native_controls_match_documented_exception_set', async ({ page }) => {
    // Ensure scan-dependent controls (HealthBadge, RepairPanel) have rendered.
    await waitForHealthBadge(page)

    const controls = await page.evaluate(() => {
      const elements = document.querySelectorAll<HTMLElement>(
        'button:not([data-pds]), input:not([data-pds])',
      )
      return Array.from(elements).map((el) => ({
        tag: el.tagName.toLowerCase(),
        testId: el.getAttribute('data-testid'),
        region: el.closest('[data-region]')?.getAttribute('data-region') ?? null,
      }))
    })

    // Known documented exception set — the ONLY native controls the PDS policy allows.
    // Each entry corresponds to a component with an architectural exception record.
    const KNOWN_EXCEPTION_TEST_IDS = new Set([
      'health-badge',    // HealthBadge trigger — status-bar overlay launcher
      'dr-indicator',    // DRStatusIndicator trigger — status-bar overlay launcher
      'cleanup-button',  // CleanupPanel trigger — status-bar action launcher
      'repair-button',   // RepairPanel trigger — status-bar action launcher (visible when corruption > 0)
      'theme-toggle',    // ThemeToggle — icon-only status-bar control, no PDS icon-button equivalent
      'sidecar-collapse', // Shell sidecar toggle — layout control, no PDS equivalent
    ])

    // (a) Total count must not exceed the documented exception ceiling.
    expect(
      controls.length,
      `Native controls must not exceed the exception ceiling of ${KNOWN_EXCEPTION_TEST_IDS.size}. ` +
        `Found (${controls.length}): ${JSON.stringify(controls)}`,
    ).toBeLessThanOrEqual(KNOWN_EXCEPTION_TEST_IDS.size)

    // (b) Each native control must carry a testId from the known exception set.
    // A control without a matching testId means an undocumented native element was added.
    for (const control of controls) {
      expect(
        control.testId !== null && KNOWN_EXCEPTION_TEST_IDS.has(control.testId),
        `Native <${control.tag}> with testId="${String(control.testId)}" is not in the documented ` +
          `exception set. All native buttons/inputs must use PDS components or appear in: ` +
          `[${[...KNOWN_EXCEPTION_TEST_IDS].join(', ')}]. Full list: ${JSON.stringify(controls)}`,
      ).toBe(true)
    }
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

  // AC-4 visual: empty column placeholder — 'research' has zero tasks in the fixture.
  // 'done' was previously used but its baseline captured task id=3 (a populated card),
  // never exercising the empty-state placeholder branch. Fix: use 'research' (0 tasks).
  test('ac4_empty_column_research', async ({ page }) => {
    const researchColumn = page.locator('[data-column="research"]')
    await researchColumn.waitFor({ state: 'visible', timeout: 6_000 })
    await expect(researchColumn).toHaveScreenshot('ac4-empty-column-research.png')
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

  // AC-7 traversal: Tab navigation reaches EACH required region and control surface explicitly.
  // Previous proof only required "any 3 distinct regions" — too weak to catch regressions.
  // This test names every required surface and fails if any is unreachable.
  test('ac7_tab_traversal_reaches_required_surfaces', async ({ page }) => {
    await page.locator('body').focus()

    const reachedRegions = new Set<string>()
    const reachedTestIds = new Set<string>()

    for (let i = 0; i < 80; i++) {
      await page.keyboard.press('Tab')
      const info = await page.evaluate(() => {
        const el = document.activeElement
        if (!el || el === document.body) return null
        const region = el.closest('[data-region]')?.getAttribute('data-region') ?? null
        // Walk up from the focused element (or shadow host) to find data-testid.
        const testId =
          el.getAttribute('data-testid') ??
          el.closest('[data-testid]')?.getAttribute('data-testid') ??
          null
        return { region, testId }
      })
      if (info?.region) reachedRegions.add(info.region)
      if (info?.testId) reachedTestIds.add(info.testId)
    }

    // Each required layout region must be individually reachable by Tab.
    const REQUIRED_REGIONS = ['status-bar', 'nav-rail', 'workspace'] as const
    for (const region of REQUIRED_REGIONS) {
      expect(
        reachedRegions.has(region),
        `Tab navigation must reach layout region '${region}'. ` +
          `Reached regions: ${[...reachedRegions].join(', ')}`,
      ).toBe(true)
    }

    // Each required named interactive control must be individually reachable by Tab.
    // These surfaces are the regression targets from the visual-remediation audit:
    //   filter-toggle   — was incorrectly excluded with tabIndex={-1} (#1573 builder fix)
    //   sidecar-collapse — shell sidecar toggle button
    const REQUIRED_CONTROLS = ['filter-toggle', 'sidecar-collapse'] as const
    for (const controlId of REQUIRED_CONTROLS) {
      expect(
        reachedTestIds.has(controlId),
        `Tab navigation must reach control '${controlId}'. ` +
          `Reached controls: ${[...reachedTestIds].join(', ')}`,
      ).toBe(true)
    }
  })

  // AC-7-v2 traversal (a): Tab traversal in BASE STATE with a task selected in sidecar.
  // Strengthens the prior proof in three ways:
  //   1. Selects a task first so sidecar content (detail + decisions + activity) is populated.
  //   2. Requires ≥ 3 DISTINCT status-bar trigger testIds (not just the region) — prevents
  //      a single trigger registering multiple times and satisfying a "3 region" check.
  //   3. Requires at least one interactive element INSIDE sidecar content (decision item,
  //      activity row, or task action) beyond the sidecar-collapse toggle itself.
  test('ac7_v2_tab_traversal_base_state_with_sidecar_content', async ({ page }) => {
    // Select a task to populate sidecar with decision viewport, detail, and activity controls.
    await page.locator('[data-testid="card-title"]').first().click()
    // DecisionViewport renders pending DRs immediately (always present once Shell mounts).
    await page
      .locator('[data-testid="decision-task-ref-dr-visual-001"]')
      .waitFor({ state: 'visible', timeout: 6_000 })
    // Ensure scan-dependent status-bar controls (HealthBadge, RepairPanel) are rendered.
    await waitForHealthBadge(page)

    await page.locator('body').focus()

    const statusBarTriggers = new Set<string>()  // distinct testIds in status-bar region
    const reachedRegions = new Set<string>()
    const reachedTestIds = new Set<string>()
    // sidecarContentTestIds: testIds in sidecar region OTHER than 'sidecar-collapse'
    const sidecarContentTestIds = new Set<string>()

    for (let i = 0; i < 120; i++) {
      await page.keyboard.press('Tab')
      const info = await page.evaluate(() => {
        const el = document.activeElement
        if (!el || el === document.body) return null
        const region = el.closest('[data-region]')?.getAttribute('data-region') ?? null
        const testId =
          el.getAttribute('data-testid') ??
          el.closest('[data-testid]')?.getAttribute('data-testid') ??
          null
        return { region, testId, tag: el.tagName.toLowerCase() }
      })
      if (info?.region) reachedRegions.add(info.region)
      if (info?.testId) reachedTestIds.add(info.testId)
      if (info?.region === 'status-bar' && info.testId) {
        statusBarTriggers.add(info.testId)
      }
      if (info?.region === 'sidecar' && info.testId && info.testId !== 'sidecar-collapse') {
        sidecarContentTestIds.add(info.testId)
      }
    }

    // Require ≥ 3 distinct status-bar trigger controls (not just the region).
    expect(
      statusBarTriggers.size,
      `Tab traversal must reach ≥ 3 distinct status-bar triggers. ` +
        `Reached: ${[...statusBarTriggers].join(', ')}`,
    ).toBeGreaterThanOrEqual(3)

    for (const region of ['nav-rail', 'workspace'] as const) {
      expect(
        reachedRegions.has(region),
        `Tab must reach layout region '${region}'. Reached: ${[...reachedRegions].join(', ')}`,
      ).toBe(true)
    }

    for (const controlId of ['filter-toggle', 'sidecar-collapse'] as const) {
      expect(
        reachedTestIds.has(controlId),
        `Tab must reach control '${controlId}'. Reached: ${[...reachedTestIds].join(', ')}`,
      ).toBe(true)
    }

    // At least one interactive element inside sidecar CONTENT must be reachable
    // (decision item, activity filter button, or task action — not just sidecar-collapse).
    expect(
      sidecarContentTestIds.size,
      `Tab must reach ≥ 1 interactive element inside sidecar content (beyond sidecar-collapse). ` +
        `Sidecar content elements reached: ${[...sidecarContentTestIds].join(', ')}. ` +
        `All testIds reached: ${[...reachedTestIds].join(', ')}`,
    ).toBeGreaterThanOrEqual(1)
  })

  // AC-7-v2 traversal (b): Tab traversal with FILTER PANEL OPEN reaches filter controls.
  // The prior traversal proof ran only in base state (filter closed); filter controls were
  // absent from the DOM and therefore untested. This test opens the filter panel first
  // and asserts that Tab reaches the search input AND at least one select/checkbox control.
  test('ac7_v2_tab_traversal_filter_open_reaches_filter_controls', async ({ page }) => {
    // Open the filter panel so p-input-search, p-select, p-multi-select, p-checkbox are in the DOM.
    await page.locator('[data-testid="filter-toggle"]').first().click()
    await page
      .locator('[data-testid="filter-panel"]')
      .waitFor({ state: 'visible', timeout: 6_000 })

    await page.locator('body').focus()

    const reachedTags = new Set<string>()
    const reachedRegions = new Set<string>()

    for (let i = 0; i < 100; i++) {
      await page.keyboard.press('Tab')
      const info = await page.evaluate(() => {
        const el = document.activeElement
        if (!el || el === document.body) return null
        const region = el.closest('[data-region]')?.getAttribute('data-region') ?? null
        return { tag: el.tagName.toLowerCase(), region }
      })
      if (info?.tag) reachedTags.add(info.tag)
      if (info?.region) reachedRegions.add(info.region)
    }

    // Filter panel region must be reachable.
    expect(
      reachedRegions.has('filter-panel'),
      `Tab traversal must reach filter-panel region. Reached regions: ${[...reachedRegions].join(', ')}`,
    ).toBe(true)

    // Filter search input (p-input-search) must be reachable.
    expect(
      reachedTags.has('p-input-search'),
      `Tab traversal must reach filter search input (p-input-search host). ` +
        `Reached tags: ${[...reachedTags].join(', ')}`,
    ).toBe(true)

    // At least one filter select or checkbox control must be reachable.
    const hasSelectOrCheckbox =
      reachedTags.has('p-select') ||
      reachedTags.has('p-multi-select') ||
      reachedTags.has('p-checkbox') ||
      reachedTags.has('p-text-field-wrapper')
    expect(
      hasSelectOrCheckbox,
      `Tab traversal must reach ≥ 1 filter select/checkbox control (p-select, p-multi-select, or p-checkbox). ` +
        `Reached tags: ${[...reachedTags].join(', ')}`,
    ).toBe(true)
  })

  // AC-7-v2 DOM audit (c): audit in BASE STATE (filter panel closed).
  // The existing test (ac7_no_undocumented_negative_tabindex_including_pds_controls) opens the
  // filter panel — this test covers the complementary base state where filter controls are absent
  // from the DOM. Together they cover both states required by AC-7-v2(c).
  test('ac7_v2_dom_audit_base_state', async ({ page }) => {
    // Base state: no filter panel open. Filter controls (p-input-search, p-select, p-checkbox)
    // are not in the DOM and do not participate in this audit pass.

    const violations = await page.evaluate(() => {
      const nativeSelectors =
        'a, button, input, select, textarea, [role="button"], [role="link"], [role="menuitem"], [role="tab"]'
      const pdsSelectors =
        'p-button, p-input-search, p-select, p-multi-select, p-checkbox, p-text-field-wrapper'

      const allElements = [
        ...Array.from(document.querySelectorAll<HTMLElement>(nativeSelectors)),
        ...Array.from(document.querySelectorAll<HTMLElement>(pdsSelectors)),
      ]

      return allElements
        .filter((el) => {
          const tabIdx = el.tabIndex
          if (tabIdx >= 0) return false
          const hasTrapException = el.closest(
            '[data-focus-trap], [role="dialog"], [aria-modal="true"]',
          )
          const hasRovingException = el.closest('[role="menu"], [role="menubar"], [role="tablist"]')
          const hasProgrammaticException = el.hasAttribute('data-focus-target')
          return !hasTrapException && !hasRovingException && !hasProgrammaticException
        })
        .map((el) => ({
          tag: el.tagName.toLowerCase(),
          testId:
            el.getAttribute('data-testid') ??
            el.closest('[data-testid]')?.getAttribute('data-testid') ??
            '',
          tabIndex: el.tabIndex,
          text: (el.textContent ?? '').trim().slice(0, 40),
        }))
    })

    expect(
      violations,
      `Base state: Found interactive/PDS elements with undocumented negative tabIndex:\n${JSON.stringify(violations, null, 2)}`,
    ).toHaveLength(0)
  })

  // AC-7 DOM audit: no undocumented negative tabIndex on interactive elements,
  // INCLUDING PDS/custom-element hosts used by the filter panel.
  // Previous proof omitted PDS custom elements (p-button, p-input-search, p-select, etc.);
  // this test opens the filter panel so those controls are in the DOM before auditing.
  // Documented exceptions: (a) modal/sheet/popover trap, (b) menu/menubar/tablist roving-tabindex
  //   per WAI-ARIA APG, (c) programmatic focus target (data-focus-target attribute).
  test('ac7_no_undocumented_negative_tabindex_including_pds_controls', async ({ page }) => {
    // Open filter panel so p-input-search, p-select, p-multi-select, p-checkbox are in the DOM.
    const filterToggle = page.locator('[data-testid="filter-toggle"]').first()
    await filterToggle.click()
    await page.locator('[data-testid="filter-panel"]').waitFor({ state: 'visible', timeout: 6_000 })

    const violations = await page.evaluate(() => {
      // Native interactive elements.
      const nativeSelectors =
        'a, button, input, select, textarea, [role="button"], [role="link"], [role="menuitem"], [role="tab"]'
      // PDS custom-element hosts that participate in keyboard reachability.
      // Hosts with tabindex=-1 prevent their entire shadow-DOM subtree from receiving focus.
      const pdsSelectors =
        'p-button, p-input-search, p-select, p-multi-select, p-checkbox, p-text-field-wrapper'

      const allElements = [
        ...Array.from(document.querySelectorAll<HTMLElement>(nativeSelectors)),
        ...Array.from(document.querySelectorAll<HTMLElement>(pdsSelectors)),
      ]

      return allElements
        .filter((el) => {
          const tabIdx = el.tabIndex
          if (tabIdx >= 0) return false // zero or positive — in normal tab flow
          // Documented exception markers.
          const hasTrapException = el.closest(
            '[data-focus-trap], [role="dialog"], [aria-modal="true"]',
          )
          const hasRovingException = el.closest('[role="menu"], [role="menubar"], [role="tablist"]')
          const hasProgrammaticException = el.hasAttribute('data-focus-target')
          return !hasTrapException && !hasRovingException && !hasProgrammaticException
        })
        .map((el) => ({
          tag: el.tagName.toLowerCase(),
          testId:
            el.getAttribute('data-testid') ??
            el.closest('[data-testid]')?.getAttribute('data-testid') ??
            '',
          tabIndex: el.tabIndex,
          text: (el.textContent ?? '').trim().slice(0, 40),
        }))
    })

    expect(
      violations,
      `Found interactive/PDS elements with undocumented negative tabIndex:\n${JSON.stringify(violations, null, 2)}`,
    ).toHaveLength(0)
  })
})
