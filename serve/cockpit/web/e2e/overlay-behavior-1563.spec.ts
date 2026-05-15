/**
 * RED-phase Playwright E2E tests for #1563: P2-06 Specify Cockpit overlay behavior.
 *
 * BUILDER INSTRUCTION (#1569): Copy this file to the tracked E2E directory and
 * verify tests FAIL before implementing:
 *   cp .owlbear/scratch/1563-overlay-behavior.spec.ts serve/cockpit/web/e2e/overlay-behavior-1563.spec.ts
 *   git add serve/cockpit/web/e2e/overlay-behavior-1563.spec.ts
 *   npm run test:e2e -- overlay-behavior-1563  # must show at least 9 failures before implementing
 *
 * AC-1: Shell and status-bar bounding-box height unchanged before and after
 *       opening each overlay surface at desktop viewport (≥1024px).
 *       Covered surfaces: HealthBadge popover, DRStatusIndicator popover,
 *       CleanupPanel confirm dialog, RepairPanel confirm dialog,
 *       ResolveModal, and ArchivalModal (all six AC-1 surfaces).
 *
 * AC-2: Blocking dialog semantics for ConfirmDialog, ResolveModal, ArchivalModal:
 *       - Tab focus must cycle within the dialog (focus trap).
 *       - Focus must be returned to the triggering element after close.
 *       Existing green behaviors (aria-modal="true" on all three, keyboard nav in
 *       ArchivalModal, Escape-closes on all) are documented in Test-Writer Notes
 *       but intentionally not re-tested here — they pass against current code.
 *
 * AC-3: Failing evidence for in-flow expansion of HealthBadge, DRStatusIndicator,
 *       CleanupPanel, and RepairPanel is provided by the AC-1 tests.
 *
 * AC-4: Task context menu overlay behavior: focus returned to the originating card
 *       on Escape. Existing green behaviors (position:fixed overlay, role="menu" /
 *       role="menuitem" structure, ArrowDown/Up/Home/End navigation, Escape
 *       closes) are documented in notes only — they pass against current code.
 *
 * RED reasons:
 *   AC-1 (4 failing): HealthBadge, DRStatusIndicator, CleanupPanel, and RepairPanel
 *     render their disclosure panels as inline flex children of .shell__status-bar.
 *     Opening each panel expands the flex row vertically, increasing the status-bar
 *     bounding-box height. No position:fixed/absolute or portal is used.
 *
 *   AC-2 (4 failing):
 *     - ConfirmDialog: no Tab key handler — Tab escapes the dialog after cycling
 *       through the Cancel and Confirm PButtons.
 *     - ResolveModal: no Tab focus-trap and no previous-focus tracking — focus is
 *       not returned to the DR item button after the modal closes.
 *     - ArchivalModal: no previous-focus tracking — focus is not returned to the
 *       task card after the modal closes (Tab trap via handleKeyDown exists but
 *       focus-return on close is definitely absent).
 *
 *   AC-4 (1 failing): context menu close via Escape calls setContextMenu(null) but
 *     does not restore focus to the task card that was right-clicked.
 *
 * Counterpart implementation task: #1569.
 *
 * API mocking: all routes stubbed via page.route() LIFO — catch-all registered
 * first (lowest priority), specific routes registered last (take LIFO precedence).
 */

import { test, expect, type Page } from '@playwright/test'

// ─── Constants ───────────────────────────────────────────────────────────────

const STATUSES = ['research', 'backlog', 'todo', 'in-progress', 'review', 'docs', 'done']
const PRIORITIES = ['critical', 'needed', 'important', 'nice-to-have', 'someday']

/** Desktop viewport consistent with ≥1024px requirement from AC-1. */
const DESKTOP_VIEWPORT = { width: 1280, height: 800 }

// ─── Fixture data ────────────────────────────────────────────────────────────

const BOARD = {
  statuses: STATUSES.map((name) => ({ name })),
  priorities: PRIORITIES,
  valid_transitions: {
    research: ['backlog'],
    backlog: ['research', 'todo'],
    todo: ['backlog', 'in-progress'],
    // 'in-progress' includes 'archived' to enable ArchivalModal trigger.
    'in-progress': ['todo', 'review', 'archived'],
    review: ['in-progress', 'docs'],
    docs: ['review', 'done'],
    done: [],
  } as Record<string, string[]>,
}

/** Scan item with all non-null fields — passes isHealthBadgeItem in Shell.tsx. */
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
    tags: [],
    blocked: false,
    block_reason: null,
    claimed: true,
  },
]

const TASK_DETAIL = {
  id: 1,
  title: 'Cache implementation',
  status: 'in-progress',
  priority: 'important',
  updated: '2026-05-14T00:00:00+00:00',
  tags: [],
  blocked: false,
  block_reason: null,
  claimed: true,
  claimed_at: '2026-05-14T00:00:00+00:00',
  dep_status: null,
  parent: null,
  depends_on: [],
  body: '## Context\n\nNeeds cache layer.',
  created: '2026-05-10T00:00:00+00:00',
}

const PENDING_DRS = [
  {
    id: 'dr-overlay-001',
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

/**
 * Register all API stubs.
 * LIFO order: catch-all first (lowest priority), specific routes last (highest).
 */
async function stubApis(page: Page): Promise<void> {
  // Catch-all: registered first = lowest LIFO priority, overridden by all below.
  await page.route('/api/**', (route) => route.fulfill({ status: 200, json: {} }))

  // SSE endpoint — empty stream to avoid connection hang.
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

  // /api/tasks/scan — returns scan items so HealthBadge and RepairPanel appear.
  // Must be registered before the wildcard /api/tasks/\d+ route (LIFO).
  await page.route('/api/tasks/scan', (route) => route.fulfill({ json: SCAN_ITEMS }))

  // Task detail — catches /api/tasks/1 etc. Registered last = highest LIFO priority.
  await page.route(/\/api\/tasks\/\d+$/, (route) => route.fulfill({ json: TASK_DETAIL }))
}

/** Wait for at least one board column to be visible. */
async function waitForBoard(page: Page): Promise<void> {
  await page.locator('[data-column]').first().waitFor({ state: 'visible', timeout: 8_000 })
}

/** Wait for HealthBadge to appear (requires scan poll to complete). */
async function waitForHealthBadge(page: Page): Promise<void> {
  await page.locator('[data-testid="health-badge"]').waitFor({ state: 'visible', timeout: 8_000 })
}

/** Return the current bounding-box height of the shell grid root. */
async function shellHeight(page: Page): Promise<number> {
  const box = await page.locator('.shell').boundingBox()
  expect(box, 'shell must be measurable').not.toBeNull()
  return box!.height
}

/** Return the current bounding-box height of the status-bar element. */
async function statusBarHeight(page: Page): Promise<number> {
  const box = await page.locator('[data-region="status-bar"]').boundingBox()
  expect(box, 'status-bar must be measurable').not.toBeNull()
  return box!.height
}

// ─── AC-1 + AC-3: Shell and status-bar reflow prevention (all 6 AC-1 surfaces) ─
//
// RED (HealthBadge, DRStatusIndicator, CleanupPanel, RepairPanel): all four render
// their disclosure panels as inline div children inside the status-bar flex row
// (no position:fixed/absolute). Opening any of them expands the flex row height.
//
// Expectation (ResolveModal, ArchivalModal): modal is opened and both shell and
// status-bar heights are asserted unchanged. ResolveModal renders as an inline
// div sibling in the .shell CSS grid (no portal); ArchivalModal renders inline
// inside .shell__workspace. AC-1 requires all six surfaces to be tested.

test.describe('TestFromAC_OverlayReflow', () => {
  test.use({ viewport: DESKTOP_VIEWPORT })

  test.beforeEach(async ({ page }) => {
    await stubApis(page)
    await page.goto('/')
    await waitForBoard(page)
  })

  // AC-1 surface 1: HealthBadge popover
  // RED: popover is an inline div appended to the status-bar flex row.
  // Opening it expands the row height above its natural 56px minimum.
  test('health_badge_popover_does_not_expand_status_bar', async ({ page }) => {
    await waitForHealthBadge(page)
    const shellH = await shellHeight(page)
    const heightBefore = await statusBarHeight(page)

    await page.click('[data-testid="health-badge"]')
    await page.locator('[data-testid="health-badge-popover"]').waitFor({ state: 'visible' })

    // FAILS: inline popover div expands the status-bar flex height.
    expect(await shellHeight(page), 'shell height must not grow when HealthBadge popover opens').toBe(shellH)
    expect(await statusBarHeight(page), 'status-bar height must not grow when HealthBadge popover opens').toBe(
      heightBefore,
    )
  })

  // AC-1 surface 2: DRStatusIndicator popover
  // RED: popover is an inline div appended to the status-bar flex row.
  test('dr_indicator_popover_does_not_expand_status_bar', async ({ page }) => {
    const shellH = await shellHeight(page)
    const heightBefore = await statusBarHeight(page)

    await page.click('[data-testid="dr-indicator"]')
    await page.locator('[data-testid="dr-popover"]').waitFor({ state: 'visible' })

    // FAILS: inline popover div expands the status-bar flex height.
    expect(await shellHeight(page), 'shell height must not grow when DRStatusIndicator popover opens').toBe(shellH)
    expect(await statusBarHeight(page), 'status-bar height must not grow when DRStatusIndicator popover opens').toBe(
      heightBefore,
    )
  })

  // AC-1 surface 3: CleanupPanel confirm dialog
  // RED: CleanupPanel replaces its idle PButton with a larger dialog div in place
  // (no portal). The dialog text + two PButtons expand the flex row height.
  test('cleanup_confirm_dialog_does_not_expand_status_bar', async ({ page }) => {
    const shellH = await shellHeight(page)
    const heightBefore = await statusBarHeight(page)

    await page.click('[data-testid="cleanup-button"]')
    await page.locator('[data-testid="cleanup-confirm-dialog"]').waitFor({ state: 'visible' })

    // FAILS: cleanup confirm dialog content expands the flex row height.
    expect(await shellHeight(page), 'shell height must not grow when CleanupPanel confirm dialog opens').toBe(shellH)
    expect(
      await statusBarHeight(page),
      'status-bar height must not grow when CleanupPanel confirm dialog opens',
    ).toBe(heightBefore)
  })

  // AC-1 surface 4: RepairPanel confirm dialog
  // RED: RepairPanel is nested inside HealthBadge's popover (itself an inline div).
  // Opening HealthBadge and then triggering repair confirm both expand status-bar.
  test('repair_panel_confirm_does_not_expand_status_bar', async ({ page }) => {
    await waitForHealthBadge(page)
    const shellH = await shellHeight(page)
    const heightBefore = await statusBarHeight(page)

    // Open HealthBadge popover to expose RepairPanel (corruptionCount > 0 from scan stub).
    await page.click('[data-testid="health-badge"]')
    await page.locator('[data-testid="health-badge-popover"]').waitFor({ state: 'visible' })
    await page.locator('[data-testid="repair-button"]').waitFor({ state: 'visible' })

    // Click repair button — transitions RepairPanel to 'confirming' phase (no API call).
    await page.click('[data-testid="repair-button"]')
    await page.locator('[data-testid="repair-confirm-dialog"]').waitFor({ state: 'visible' })

    // FAILS: both the health-badge popover and the nested repair confirm expand
    // the status-bar flex row height above the baseline.
    expect(await shellHeight(page), 'shell height must not grow when RepairPanel confirm dialog opens').toBe(shellH)
    expect(
      await statusBarHeight(page),
      'status-bar height must not grow when RepairPanel confirm dialog opens',
    ).toBe(heightBefore)
  })

  // AC-1 surface 5: ResolveModal
  // ResolveModal renders as an inline <div role="dialog"> that is a direct child
  // of the .shell CSS-grid root (no portal, no position:fixed). Shell height is
  // pinned to 100vh, so the shell bounding-box should not change; the status-bar
  // is unaffected by a sibling that is auto-placed outside the named grid areas.
  test('resolve_modal_does_not_expand_shell_or_status_bar', async ({ page }) => {
    const shellH = await shellHeight(page)
    const statusH = await statusBarHeight(page)

    // Open DRStatusIndicator popover and click the DR item to open ResolveModal.
    await page.click('[data-testid="dr-indicator"]')
    await page.locator('[data-testid="dr-popover"]').waitFor({ state: 'visible' })
    await page.click('[data-testid="dr-item-dr-overlay-001"]')
    await page.locator('[data-testid="resolve-modal"]').waitFor({ state: 'visible', timeout: 5_000 })

    expect(
      await shellHeight(page),
      'shell height must not grow when ResolveModal opens',
    ).toBe(shellH)
    expect(
      await statusBarHeight(page),
      'status-bar height must not grow when ResolveModal opens',
    ).toBe(statusH)
  })

  // AC-1 surface 6: ArchivalModal
  // ArchivalModal renders as an inline <div role="dialog"> inside KanbanBoard,
  // which lives in .shell__workspace (overflow:auto). The workspace bounding-box
  // is constrained by the CSS grid 1fr row, so the shell and status-bar heights
  // should remain unchanged when the modal appears in the document flow.
  test('archival_modal_does_not_expand_shell_or_status_bar', async ({ page }) => {
    const shellH = await shellHeight(page)
    const statusH = await statusBarHeight(page)

    const card = page.locator('[data-testid="task-card"][data-id="1"]')
    await card.waitFor({ state: 'visible', timeout: 8_000 })

    // Open context menu → click archived transition → ArchivalModal appears.
    await card.click({ button: 'right' })
    const contextMenu = page.locator('[data-testid="context-menu"]')
    await contextMenu.waitFor({ state: 'visible', timeout: 5_000 })
    await page.click('[data-testid="transition-item"][data-status="archived"]')
    await page.locator('[data-testid="archival-submit"]').waitFor({ state: 'visible', timeout: 5_000 })

    expect(
      await shellHeight(page),
      'shell height must not grow when ArchivalModal opens',
    ).toBe(shellH)
    expect(
      await statusBarHeight(page),
      'status-bar height must not grow when ArchivalModal opens',
    ).toBe(statusH)
  })
})

// ─── AC-2: Blocking dialog semantics ─────────────────────────────────────────
//
// Existing green (documented, not re-tested):
//   - ConfirmDialog: aria-modal="true", Escape cancels.
//   - ResolveModal: aria-modal="true", Escape closes.
//   - ArchivalModal: aria-modal="true", Escape closes, Tab trap implemented.
//
// RED:
//   - ConfirmDialog: no Tab focus trap → Tab escapes after 2 PButtons.
//   - ResolveModal: no Tab focus trap → Tab escapes; no previous-focus tracking.
//   - ArchivalModal: no previous-focus tracking → focus not returned after close.

test.describe('TestFromAC_BlockingDialogSemantics', () => {
  test.use({ viewport: DESKTOP_VIEWPORT })

  test.beforeEach(async ({ page }) => {
    await stubApis(page)
    await page.goto('/')
    await waitForBoard(page)
  })

  /** Select task 1 in the sidecar and open the ConfirmDialog via Move Backward. */
  async function openConfirmDialog(page: Page): Promise<void> {
    const card = page.locator('[data-testid="task-card"][data-id="1"]')
    await card.waitFor({ state: 'visible', timeout: 8_000 })
    await card.click()
    // Wait for the sidecar to load task detail and show the move-backward button.
    await page.locator('[data-testid="move-backward"]').waitFor({ state: 'visible', timeout: 8_000 })
    await page.click('[data-testid="move-backward"]')
    await page.locator('[data-testid="confirm-dialog"]').waitFor({ state: 'visible', timeout: 5_000 })
  }

  // AC-2, ConfirmDialog: Tab must cycle within the dialog.
  // RED: ConfirmDialog has no Tab handler — Tab escapes after cycling through the
  // Cancel and Confirm PButtons (dialog div is tabIndex={-1}, not in tab order).
  test('confirm_dialog_tab_focus_cycles_within_dialog', async ({ page }) => {
    await openConfirmDialog(page)
    await expect(page.locator('[data-testid="confirm-dialog"]')).toBeVisible()

    // Tab through all focusable children: Cancel, Confirm, and one more for the wrap.
    await page.keyboard.press('Tab')
    await page.keyboard.press('Tab')
    await page.keyboard.press('Tab')

    // Focus must still be inside the dialog after cycling.
    // FAILS: no focus trap → 3rd Tab moves focus outside the dialog.
    const focusIsInside = await page.evaluate(() => {
      const dialogEl = document.querySelector('[data-testid="confirm-dialog"]')
      return dialogEl !== null && dialogEl.contains(document.activeElement)
    })
    expect(focusIsInside, 'Tab focus must stay inside ConfirmDialog (no trap currently)').toBe(true)
  })

  // AC-2, ResolveModal: Tab must cycle within the modal.
  // RED: ResolveModal has no Tab handler — Tab escapes after all focusable elements
  // (fieldset options, textarea, submit button, cancel button, and any PDS internals).
  test('resolve_modal_tab_focus_cycles_within_modal', async ({ page }) => {
    // Open DRStatusIndicator popover and click the DR item to open ResolveModal.
    await page.click('[data-testid="dr-indicator"]')
    await page.locator('[data-testid="dr-popover"]').waitFor({ state: 'visible' })
    await page.click('[data-testid="dr-item-dr-overlay-001"]')
    await page.locator('[data-testid="resolve-modal"]').waitFor({ state: 'visible', timeout: 5_000 })

    // Tab through all focusable children; 7 presses should wrap if a trap exists.
    for (let i = 0; i < 7; i++) {
      await page.keyboard.press('Tab')
    }

    // Focus must still be inside the modal after cycling.
    // FAILS: no focus trap → Tab eventually moves focus outside the modal.
    const focusIsInside = await page.evaluate(() => {
      const modalEl = document.querySelector('[data-testid="resolve-modal"]')
      return modalEl !== null && modalEl.contains(document.activeElement)
    })
    expect(focusIsInside, 'Tab focus must stay inside ResolveModal (no trap currently)').toBe(true)
  })

  // AC-2, ResolveModal: focus must return to the triggering element after close.
  // RED: ResolveModal mounts without capturing previousFocus — no restoration on close.
  test('resolve_modal_focus_returned_to_trigger_after_close', async ({ page }) => {
    // Open DR popover and focus the DR item button — this is the trigger.
    await page.click('[data-testid="dr-indicator"]')
    await page.locator('[data-testid="dr-popover"]').waitFor({ state: 'visible' })
    const drItem = page.locator('[data-testid="dr-item-dr-overlay-001"]')
    await drItem.waitFor({ state: 'visible' })
    await drItem.focus()

    // Click DR item → ResolveModal opens.
    await drItem.click()
    await page.locator('[data-testid="resolve-modal"]').waitFor({ state: 'visible', timeout: 5_000 })

    // Close via Escape.
    await page.keyboard.press('Escape')
    await page.locator('[data-testid="resolve-modal"]').waitFor({ state: 'hidden', timeout: 5_000 })

    // Assert focus is back on the exact DR item button that triggered the modal.
    // FAILS: ResolveModal does not track previous focus — focus goes to body after close.
    // NOTE: DRStatusIndicator.onItemClick does not close the popover, so the dr-item-*
    // button remains in DOM after modal close — exact-element assertion is valid.
    const focusOnTrigger = await page.evaluate(() => {
      const drItemButton = document.querySelector('[data-testid="dr-item-dr-overlay-001"]')
      return document.activeElement === drItemButton
    })
    expect(
      focusOnTrigger,
      'Focus must return to exact [data-testid="dr-item-dr-overlay-001"] trigger after ResolveModal closes',
    ).toBe(true)
  })

  // AC-2, ArchivalModal: focus must return to the originating task card after close.
  // RED: ArchivalModal mounts without capturing previousFocus (reasonSelectRef.current?.focus()
  // is called on mount, but no previousFocus is stored or restored on unmount).
  // Close is triggered via the Cancel button (Escape is unreliable — PDS p-select
  // may intercept Escape internally before it reaches the dialog onKeyDown handler).
  test('archival_modal_focus_returned_to_trigger_after_close', async ({ page }) => {
    const card = page.locator('[data-testid="task-card"][data-id="1"]')
    await card.waitFor({ state: 'visible', timeout: 8_000 })

    // Focus the card — establishes it as the clear triggering element.
    await card.focus()

    // Right-click to open context menu.
    await card.click({ button: 'right' })
    const contextMenu = page.locator('[data-testid="context-menu"]')
    await contextMenu.waitFor({ state: 'visible', timeout: 5_000 })

    // Click the 'archived' transition item → ArchivalModal opens.
    await page.click('[data-testid="transition-item"][data-status="archived"]')

    // Wait for ArchivalModal: identified by the submit button (no data-testid on root).
    const archivalSubmit = page.locator('[data-testid="archival-submit"]')
    await archivalSubmit.waitFor({ state: 'visible', timeout: 5_000 })

    // Close via Cancel button (avoids PDS p-select Escape interception).
    // ArchivalModal's Cancel PButton has onClick={onClose}. Select by contained text.
    const cancelBtn = page.locator('p-button:has-text("Cancel")').last()
    await cancelBtn.waitFor({ state: 'visible', timeout: 5_000 })
    await cancelBtn.click()
    await archivalSubmit.waitFor({ state: 'hidden', timeout: 5_000 })

    // Assert focus returned to the originating task card.
    // FAILS: ArchivalModal does not track or restore previous focus on close.
    const focusOnCard = await page.evaluate(() => {
      const cardEl = document.querySelector('[data-testid="task-card"][data-id="1"]')
      return cardEl !== null && cardEl.contains(document.activeElement)
    })
    expect(
      focusOnCard,
      'Focus must return to the originating task card after ArchivalModal closes',
    ).toBe(true)
  })
})

// ─── AC-4: Context menu focus return ─────────────────────────────────────────
//
// Existing green (documented, not re-tested):
//   - Context menu renders as position:fixed → board column heights unchanged.
//   - role="menu" with role="menuitem" children.
//   - ArrowDown/ArrowUp/Home/End keyboard navigation within the menu.
//   - Escape key closes the menu (document keydown handler in KanbanBoard).
//
// RED: Escape handler calls setContextMenu(null) but does not restore focus to
// the task card that was right-clicked. focus remains on body (or the previously
// focused menuitem element is removed from DOM leaving focus on body).

test.describe('TestFromAC_ContextMenuOverlay', () => {
  test.use({ viewport: DESKTOP_VIEWPORT })

  test.beforeEach(async ({ page }) => {
    await stubApis(page)
    await page.goto('/')
    await waitForBoard(page)
  })

  // AC-4: focus must return to the originating card after context menu closes via Escape.
  // RED: KanbanBoard's Escape handler (document keydown) calls setContextMenu(null)
  // but never calls `triggerElement.focus()` — focus is lost after close.
  test('context_menu_focus_returned_to_card_after_escape', async ({ page }) => {
    const card = page.locator('[data-testid="task-card"][data-id="1"]')
    await card.waitFor({ state: 'visible', timeout: 8_000 })

    // Focus the card — establishes it as the originating element.
    await card.focus()

    // Right-click to open context menu.
    await card.click({ button: 'right' })
    const contextMenu = page.locator('[data-testid="context-menu"]')
    await contextMenu.waitFor({ state: 'visible', timeout: 5_000 })

    // KanbanBoard useEffect focuses the first menuitem when context menu opens.
    await expect(page.locator('[role="menuitem"]').first()).toBeFocused()

    // Close via Escape.
    await page.keyboard.press('Escape')
    await contextMenu.waitFor({ state: 'hidden', timeout: 5_000 })

    // Assert focus returned to the originating task card.
    // FAILS: setContextMenu(null) does not restore focus — the previously-focused
    // menuitem element is removed from DOM and focus falls to body.
    await expect(
      card,
      'Focus must return to the originating task card after context menu closes',
    ).toBeFocused()
  })
})
