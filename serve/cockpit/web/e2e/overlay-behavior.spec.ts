/**
 * Playwright coverage for Cockpit overlay behavior.
 *
 * Covers shell/status-bar bounding-box stability, dialog focus traps, focus
 * return after close, and task context-menu keyboard behavior. API mocking uses
 * Playwright route LIFO order: catch-all first, specific routes last.
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

async function openWorkspaceStatus(page: Page): Promise<void> {
  await waitForHealthBadge(page)
  await page.locator('[data-testid="health-badge"]').click()
  await page.locator('[data-testid="health-badge-popover"]').waitFor({ state: 'visible', timeout: 3_000 })
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

async function expectWorkspaceStatusConfirmDialogPortaled(page: Page, testId: string): Promise<void> {
  const dialog = page.locator(`[data-testid="${testId}"]`)

  await expect(dialog).toBeVisible()
  await expect(dialog).toHaveAttribute('role', 'dialog')
  await expect(dialog).toHaveAttribute('aria-modal', 'true')
  await expect(page.locator(`[data-testid="health-badge-popover"] [data-testid="${testId}"]`)).toHaveCount(0)

  const parentTag = await dialog.evaluate((element) => element.parentElement?.tagName.toLowerCase())
  expect(parentTag, 'workspace status confirmation PModal should be portaled to document.body').toBe('body')

  const dialogContentBox = await dialog.locator('div').first().boundingBox()
  const viewport = page.viewportSize()
  expect(dialogContentBox, 'visible PModal content must be measurable').not.toBeNull()
  expect(viewport, 'viewport must be available').not.toBeNull()

  const dialogCenterX = dialogContentBox!.x + dialogContentBox!.width / 2
  expect(
    Math.abs(dialogCenterX - viewport!.width / 2),
    'PModal content should be centered in the viewport, not aligned to the PFlyout',
  ).toBeLessThan(120)
}

// ─── AC-1 + AC-3: Shell and status-bar reflow prevention (all 6 AC-1 surfaces) ─
//
// RED (HealthBadge, CleanupPanel, RepairPanel): status/care overlays used to render
// inline inside the status-bar flex row
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

  // AC-1 surface 2: CleanupPanel confirm dialog
  // RED: CleanupPanel replaces its idle PButton with a larger dialog div in place
  // (no portal). The dialog text + two PButtons expand the flex row height.
  test('cleanup_confirm_dialog_does_not_expand_status_bar', async ({ page }) => {
    const shellH = await shellHeight(page)
    const heightBefore = await statusBarHeight(page)

    await openWorkspaceStatus(page)
    await page.click('[data-testid="cleanup-button"]')
    await page.locator('[data-testid="cleanup-confirm-dialog"]').waitFor({ state: 'visible' })

    // FAILS: cleanup confirm dialog content expands the flex row height.
    expect(await shellHeight(page), 'shell height must not grow when CleanupPanel confirm dialog opens').toBe(shellH)
    expect(
      await statusBarHeight(page),
      'status-bar height must not grow when CleanupPanel confirm dialog opens',
    ).toBe(heightBefore)
  })

  // AC-1 surface 3: RepairPanel confirm dialog
  // RED: RepairPanel is nested inside HealthBadge's popover (itself an inline div).
  // Opening HealthBadge and then triggering repair confirm both expand status-bar.
  test('repair_panel_confirm_does_not_expand_status_bar', async ({ page }) => {
    await waitForHealthBadge(page)
    const shellH = await shellHeight(page)
    const heightBefore = await statusBarHeight(page)

    await openWorkspaceStatus(page)
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

  // AC-1 surface 4: ResolveModal
  // ResolveModal renders as an inline <div role="dialog"> that is a direct child
  // of the .shell CSS-grid root (no portal, no position:fixed). Shell height is
  // pinned to 100vh, so the shell bounding-box should not change; the status-bar
  // is unaffected by a sibling that is auto-placed outside the named grid areas.
  test('resolve_modal_does_not_expand_shell_or_status_bar', async ({ page }) => {
    const shellH = await shellHeight(page)
    const statusH = await statusBarHeight(page)

    await page.goto('/decisions')
    await page.locator('[data-testid="decisions-page"]').waitFor({ state: 'visible', timeout: 5_000 })
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

  // AC-1 surface 5: ArchivalModal
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

test.describe('TestFromAudit_WorkspaceStatusPdsModalComposition', () => {
  test.use({ viewport: DESKTOP_VIEWPORT })

  test.beforeEach(async ({ page }) => {
    await stubApis(page)
    await page.goto('/')
    await waitForBoard(page)
    await waitForHealthBadge(page)
  })

  test('repair_confirmation_is_a_top_level_pds_modal_from_workspace_status', async ({ page }) => {
    await openWorkspaceStatus(page)
    await page.locator('[data-testid="repair-button"]').click()
    await expectWorkspaceStatusConfirmDialogPortaled(page, 'repair-confirm-dialog')
  })

  test('cleanup_confirmation_is_a_top_level_pds_modal_from_workspace_status', async ({ page }) => {
    await openWorkspaceStatus(page)
    await page.locator('[data-testid="cleanup-button"]').click()
    await expectWorkspaceStatusConfirmDialogPortaled(page, 'cleanup-confirm-dialog')
  })
})

// ─── AC-2: Blocking dialog semantics ─────────────────────────────────────────
//
// Task-local E2E checks required by AC-2 (dual: new assertions + carry-forward):
//
// GREEN (regression guards — already implemented in source):
//   - ConfirmDialog: role="dialog" and aria-modal="true" (ConfirmDialog.tsx:65).
//   - ResolveModal: role="dialog" and aria-modal="true" (ResolveModal.tsx:157-158).
//   - ArchivalModal: role="dialog" and aria-modal="true" (ArchivalModal.tsx:246).
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

  /** Select task 1 in the task detail modal and open the ConfirmDialog via Move Backward. */
  async function openConfirmDialog(page: Page): Promise<void> {
    const card = page.locator('[data-testid="task-card"][data-id="1"]')
    await card.waitFor({ state: 'visible', timeout: 8_000 })
    await card.click()
    // Wait for the task detail modal to load task detail and show the move-backward button.
    await page.locator('[data-testid="move-backward"]').waitFor({ state: 'visible', timeout: 8_000 })
    await page.click('[data-testid="move-backward"]')
    await page.locator('[data-testid="confirm-dialog"]').waitFor({ state: 'visible', timeout: 5_000 })
  }

  // AC-2, ConfirmDialog: role="dialog" and aria-modal="true" must be present.
  // GREEN (regression guard): source already renders these attributes (ConfirmDialog.tsx:65).
  // Task-local E2E proof required by AC-2 — carry-forward documentation is not sufficient.
  test('confirm_dialog_has_role_dialog_and_aria_modal', async ({ page }) => {
    await openConfirmDialog(page)
    const dialog = page.locator('[data-testid="confirm-dialog"]')
    await expect(dialog).toBeVisible()
    await expect(dialog).toHaveAttribute('role', 'dialog')
    await expect(dialog).toHaveAttribute('aria-modal', 'true')
  })

  // AC-2, ResolveModal: role="dialog" and aria-modal="true" must be present.
  // GREEN (regression guard): source already renders these attributes (ResolveModal.tsx:157-158).
  // Task-local E2E proof required by AC-2.
  test('resolve_modal_has_role_dialog_and_aria_modal', async ({ page }) => {
    await page.goto('/decisions')
    await page.locator('[data-testid="decisions-page"]').waitFor({ state: 'visible', timeout: 5_000 })
    await page.click('[data-testid="dr-item-dr-overlay-001"]')
    const modal = page.locator('[data-testid="resolve-modal"]')
    await modal.waitFor({ state: 'visible', timeout: 5_000 })
    await expect(modal).toHaveAttribute('role', 'dialog')
    await expect(modal).toHaveAttribute('aria-modal', 'true')
  })

  // AC-2, ArchivalModal: role="dialog" and aria-modal="true" must be present.
  // GREEN (regression guard): source already renders these attributes (ArchivalModal.tsx:246).
  // Task-local E2E proof required by AC-2.
  test('archival_modal_has_role_dialog_and_aria_modal', async ({ page }) => {
    const card = page.locator('[data-testid="task-card"][data-id="1"]')
    await card.waitFor({ state: 'visible', timeout: 8_000 })
    await card.click({ button: 'right' })
    const contextMenu = page.locator('[data-testid="context-menu"]')
    await contextMenu.waitFor({ state: 'visible', timeout: 5_000 })
    await page.click('[data-testid="transition-item"][data-status="archived"]')
    await page.locator('[data-testid="archival-submit"]').waitFor({ state: 'visible', timeout: 5_000 })
    // ArchivalModal root has role="dialog" and aria-modal="true" (ArchivalModal.tsx:246).
    const modal = page.locator('[role="dialog"][aria-modal="true"]').last()
    await expect(modal).toBeVisible()
    await expect(modal).toHaveAttribute('role', 'dialog')
    await expect(modal).toHaveAttribute('aria-modal', 'true')
  })

  // AC-2, ConfirmDialog: Tab must cycle within the dialog (focus trap).
  // RED: ConfirmDialog has no Tab handler — Tab escapes the dialog.
  // Wrap assertion: focus last focusable (Confirm PButton) → Tab → first (Cancel) must be focused;
  // focus first (Cancel) → Shift+Tab → last (Confirm) must be focused.
  // FAILS: no Tab trap → Tab/Shift+Tab escape the dialog instead of wrapping.
  test('confirm_dialog_tab_focus_cycles_within_dialog', async ({ page }) => {
    await openConfirmDialog(page)
    const dialog = page.locator('[data-testid="confirm-dialog"]')
    await expect(dialog).toBeVisible()

    // ConfirmDialog renders: Cancel PButton (first), Confirm PButton (last, dynamic label).
    const cancelBtn = dialog.locator('p-button').nth(0)
    const confirmBtn = dialog.locator('p-button').nth(1)
    await cancelBtn.waitFor({ state: 'visible', timeout: 5_000 })
    await confirmBtn.waitFor({ state: 'visible', timeout: 5_000 })

    // Forward wrap: focus last focusable (Confirm), press Tab, assert first (Cancel) is focused.
    // FAILS: ConfirmDialog has no Tab handler → Tab escapes the dialog entirely.
    await confirmBtn.focus()
    await page.keyboard.press('Tab')
    await expect(
      cancelBtn,
      'Tab from last focusable (Confirm) must wrap to first focusable (Cancel) — no trap currently',
    ).toBeFocused()

    // Backward wrap: focus first focusable (Cancel), press Shift+Tab, assert last (Confirm) is focused.
    // FAILS: no Tab trap → Shift+Tab escapes the dialog entirely.
    await cancelBtn.focus()
    await page.keyboard.press('Shift+Tab')
    await expect(
      confirmBtn,
      'Shift+Tab from first focusable (Cancel) must wrap to last focusable (Confirm) — no trap currently',
    ).toBeFocused()
  })

  // AC-2, ResolveModal: Tab must cycle within the modal (focus trap).
  // RED: ResolveModal has no Tab handler — Tab escapes the modal.
  // Wrap assertion: focus last focusable (Close PButton) → Tab → first (approved radio) must be focused;
  // focus first (approved radio) → Shift+Tab → last (Close) must be focused.
  // FAILS: no Tab trap → Tab/Shift+Tab escape the modal instead of wrapping.
  test('resolve_modal_tab_focus_cycles_within_modal', async ({ page }) => {
    await page.goto('/decisions')
    await page.locator('[data-testid="decisions-page"]').waitFor({ state: 'visible', timeout: 5_000 })
    await page.click('[data-testid="dr-item-dr-overlay-001"]')
    const modal = page.locator('[data-testid="resolve-modal"]')
    await modal.waitFor({ state: 'visible', timeout: 5_000 })

    // First focusable: approved radio inside response-selector.
    // Last focusable: Close/Cancel PButton [data-testid="resolve-cancel"].
    const firstFocusable = modal.locator('[data-testid="response-selector"] input[value="approved"]')
    const lastFocusable = page.locator('[data-testid="resolve-cancel"]')
    await firstFocusable.waitFor({ state: 'visible', timeout: 5_000 })
    await lastFocusable.waitFor({ state: 'visible', timeout: 5_000 })

    // Forward wrap: focus last (Close), press Tab, assert first (approved radio) is focused.
    // FAILS: ResolveModal has no Tab trap → Tab escapes the modal.
    await lastFocusable.focus()
    await page.keyboard.press('Tab')
    const approvedFocused = await page.evaluate(() => {
      const el = document.querySelector('[data-testid="response-selector"] input[value="approved"]')
      return document.activeElement === el
    })
    expect(
      approvedFocused,
      'Tab from last focusable (Close) must wrap to first focusable (approved radio) — no trap currently',
    ).toBe(true)

    // Backward wrap: focus first (approved radio), press Shift+Tab, assert Close is focused.
    // FAILS: no Tab trap → Shift+Tab escapes the modal.
    await firstFocusable.focus()
    await page.keyboard.press('Shift+Tab')
    await expect(
      lastFocusable,
      'Shift+Tab from first focusable (approved radio) must wrap to last (Close) — no trap currently',
    ).toBeFocused()
  })

  // AC-2, ResolveModal: focus must return to the triggering element after close.
  // RED: ResolveModal mounts without capturing previousFocus — no restoration on close.
  //
  // Close mechanism: "Close Modal" button (data-testid="resolve-cancel") rather than Escape.
  // Rationale: pressing Escape while PModal host has focus does not reach the native <dialog>
  // cancel event (PDS PModal in this version focuses the host element, not the shadow dialog,
  // so the native dismiss mechanism is not triggered by Escape keypress). The "Close Modal"
  // button directly calls requestClose() via React onClick — same code path as PModal onDismiss.
  test('resolve_modal_focus_returned_to_trigger_after_close', async ({ page }) => {
    await page.goto('/decisions')
    await page.locator('[data-testid="decisions-page"]').waitFor({ state: 'visible', timeout: 5_000 })
    const drItem = page.locator('[data-testid="dr-item-dr-overlay-001"]')
    await drItem.waitFor({ state: 'visible' })
    await drItem.focus()

    // Click DR item → ResolveModal opens.
    await drItem.click()
    await page.locator('[data-testid="resolve-modal"]').waitFor({ state: 'visible', timeout: 5_000 })

    // Close via the "Close Modal" button — calls requestClose() → onClose() → modal unmounts.
    // The Decisions route remains mounted, so the dr-item-* trigger remains in DOM.
    const closeBtn = page.locator('[data-testid="resolve-cancel"]')
    await closeBtn.waitFor({ state: 'visible', timeout: 5_000 })
    await closeBtn.click()

    // Assert focus is back on the exact DR item button that triggered the modal.
    // ResolveModal.useEffect cleanup calls previousFocusRef.current?.focus() on unmount.
    // previousFocusRef captured document.activeElement (dr-item button) at mount time.
    // FAILS: ResolveModal does not track previous focus — focus goes to body after close.
    await expect(
      drItem,
      'Focus must return to exact [data-testid="dr-item-dr-overlay-001"] trigger after ResolveModal closes',
    ).toBeFocused({ timeout: 5_000 })
  })

  // AC-2, ArchivalModal: Tab must cycle within the modal — PModal native <dialog> trap.
  // PModal migration removed the hand-rolled handleKeyDown Tab cycling; native <dialog> traps Tab.
  // PModal's shadow DOM also renders a dismiss button (X) that participates in the focus cycle.
  // Updated: scope uses data-testid="archival-modal" (host element) — not shadow [role=dialog] which
  // causes scoping failures when the Cancel button is in PModal's light-DOM slot.
  // Assertion changed to boundary containment: does not assume a specific wrap target because the
  // PModal shadow X button may come first/last in the native dialog focus order.
  test('archival_modal_tab_focus_cycles_within_modal', async ({ page }) => {
    const card = page.locator('[data-testid="task-card"][data-id="1"]')
    await card.waitFor({ state: 'visible', timeout: 8_000 })
    await card.click({ button: 'right' })
    const contextMenu = page.locator('[data-testid="context-menu"]')
    await contextMenu.waitFor({ state: 'visible', timeout: 5_000 })
    await page.click('[data-testid="transition-item"][data-status="archived"]')
    await page.locator('[data-testid="archival-submit"]').waitFor({ state: 'visible', timeout: 5_000 })

    // PModal migration: scope to host element via data-testid (not shadow-DOM [role=dialog]).
    // The Cancel p-button is in PModal's light-DOM slot and is found from the host locator.
    const archivalModal = page.locator('[data-testid="archival-modal"]')
    const archivalSelect = page.locator('[name="archival-reason"]')
    const cancelBtn = archivalModal.locator('p-button').filter({ hasText: 'Cancel' })
    await archivalSelect.waitFor({ state: 'visible', timeout: 5_000 })
    await cancelBtn.waitFor({ state: 'visible', timeout: 5_000 })

    // Forward Tab from Cancel: native <dialog> trap keeps focus inside the PModal boundary.
    // The wrap target may be PModal's shadow dismiss button (X) rather than PSelect; assert
    // boundary containment only — light-DOM containment covers slotted elements, shadow-root
    // containment covers PModal's own X button.
    await cancelBtn.focus()
    await page.keyboard.press('Tab')
    const focusedInsideAfterTab = await page.evaluate(() => {
      const host = document.querySelector('[data-testid="archival-modal"]')
      if (!host) return false
      const active = document.activeElement
      return (
        active !== null &&
        (host === active ||
          host.contains(active) ||
          (host.shadowRoot !== null && host.shadowRoot.contains(active)))
      )
    })
    expect(
      focusedInsideAfterTab,
      'Tab from Cancel must keep focus inside archival-modal PModal boundary (native <dialog> trap)',
    ).toBe(true)

    // Backward Shift+Tab from PSelect: native trap keeps focus inside the PModal boundary.
    await archivalSelect.focus()
    await page.keyboard.press('Shift+Tab')
    const focusedInsideAfterShiftTab = await page.evaluate(() => {
      const host = document.querySelector('[data-testid="archival-modal"]')
      if (!host) return false
      const active = document.activeElement
      return (
        active !== null &&
        (host === active ||
          host.contains(active) ||
          (host.shadowRoot !== null && host.shadowRoot.contains(active)))
      )
    })
    expect(
      focusedInsideAfterShiftTab,
      'Shift+Tab from PSelect must keep focus inside archival-modal PModal boundary (native <dialog> trap)',
    ).toBe(true)
  })

  // AC-2, ConfirmDialog: focus must return to the triggering element after close.
  // GREEN (regression guard): ConfirmDialog.tsx:21/48-51 stores previousFocusRef on mount
  // and calls previousFocusRef.current?.focus() on unmount (cleanup).
  // This is a task-local E2E check required by AC-2 (carry-forward documentation alone is not sufficient).
  test('confirm_dialog_focus_returned_to_trigger_after_close', async ({ page }) => {
    const card = page.locator('[data-testid="task-card"][data-id="1"]')
    await card.waitFor({ state: 'visible', timeout: 8_000 })
    await card.click()
    const moveBackward = page.locator('[data-testid="move-backward"]')
    await moveBackward.waitFor({ state: 'visible', timeout: 8_000 })
    // Focus the move-backward button — previousFocusRef captures this on dialog mount.
    await moveBackward.focus()
    await moveBackward.click()
    await page.locator('[data-testid="confirm-dialog"]').waitFor({ state: 'visible', timeout: 5_000 })

    // Close via Cancel — unmounts dialog → previousFocusRef.current?.focus() restores trigger.
    const cancelBtn = page.locator('[data-testid="confirm-dialog"] p-button').filter({ hasText: 'Cancel' })
    await cancelBtn.waitFor({ state: 'visible', timeout: 5_000 })
    await cancelBtn.click()
    await page.locator('[data-testid="confirm-dialog"]').waitFor({ state: 'hidden', timeout: 5_000 })

    // GREEN: ConfirmDialog.tsx previousFocusRef stores document.activeElement on mount
    // and calls .focus() on cleanup — focus must return to the move-backward trigger.
    await expect(
      moveBackward,
      'Focus must return to the move-backward trigger after ConfirmDialog closes',
    ).toBeFocused()
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

    // Assert focus returned to the exact originating task card element.
    // Target: card host element ([data-testid="task-card"][data-id="1"]) — the menuitem
    // that opened the modal is torn down (setContextMenu(null) at KanbanBoard.tsx:202)
    // before the modal opens, so ARIA APG focus-return falls back to this card element.
    // FAILS: ArchivalModal does not track or restore previous focus on close.
    const cardEl = page.locator('[data-testid="task-card"][data-id="1"]')
    await expect(
      cardEl,
      'Focus must return to the exact originating task card after ArchivalModal closes',
    ).toBeFocused()
  })
})

// ─── AC-4: Context menu overlay behavior ─────────────────────────────────────
//
// Task-local E2E checks required by AC-4 (dual: new assertions + carry-forward):
//
// GREEN (regression guards — already implemented in source, KanbanBoard.tsx:359-391):
//   - Context menu renders with position:fixed → board column heights unchanged.
//   - role="menu" on context menu container.
//   - role="menuitem" on transition items.
//   - ArrowDown/ArrowUp keyboard navigation.
//
// RED: Escape handler calls setContextMenu(null) but does not restore focus to
// the task card that was right-clicked. Focus remains on body (or the previously
// focused menuitem element is removed from DOM leaving focus on body).

test.describe('TestFromAC_ContextMenuOverlay', () => {
  test.use({ viewport: DESKTOP_VIEWPORT })

  test.beforeEach(async ({ page }) => {
    await stubApis(page)
    await page.goto('/')
    await waitForBoard(page)
  })

  // AC-4: context menu must render as a positioned overlay without changing board
  // column heights. GREEN (regression guard): context menu uses position:fixed
  // (KanbanBoard.tsx:361) — no in-flow reflow occurs.
  // Task-local E2E proof required by AC-4. AC-4 says "board column heights" — plural;
  // all visible [data-column] elements are measured.
  test('context_menu_renders_as_fixed_overlay_without_column_reflow', async ({ page }) => {
    const card = page.locator('[data-testid="task-card"][data-id="1"]')
    await card.waitFor({ state: 'visible', timeout: 8_000 })

    // Measure ALL board column heights before opening the context menu.
    const columns = page.locator('[data-column]')
    const count = await columns.count()
    expect(count, 'at least one board column must be visible').toBeGreaterThan(0)
    const heightsBefore: number[] = []
    for (let i = 0; i < count; i++) {
      const box = await columns.nth(i).boundingBox()
      expect(box, `board column ${i} must be measurable before context menu open`).not.toBeNull()
      heightsBefore.push(box!.height)
    }

    // Open context menu via right-click.
    await card.click({ button: 'right' })
    const contextMenu = page.locator('[data-testid="context-menu"]')
    await contextMenu.waitFor({ state: 'visible', timeout: 5_000 })

    // ALL column heights must be unchanged — position:fixed context menu does not reflow any column.
    for (let i = 0; i < count; i++) {
      const box = await columns.nth(i).boundingBox()
      expect(box, `board column ${i} must be measurable after context menu open`).not.toBeNull()
      expect(box!.height, `board column ${i} height must not change when context menu opens`).toBeCloseTo(heightsBefore[i], 3)
    }
  })

  // AC-4: context menu must expose role="menu" with role="menuitem" children.
  // GREEN (regression guard): KanbanBoard.tsx:359-368 renders these roles.
  // Task-local E2E proof required by AC-4. Must verify the complete menu structure:
  // task 1 is 'in-progress' with valid_transitions ['todo', 'review', 'archived'] = exactly 3 items.
  test('context_menu_has_role_menu_and_menuitem_children', async ({ page }) => {
    const card = page.locator('[data-testid="task-card"][data-id="1"]')
    await card.waitFor({ state: 'visible', timeout: 8_000 })
    await card.click({ button: 'right' })

    const contextMenu = page.locator('[data-testid="context-menu"]')
    await contextMenu.waitFor({ state: 'visible', timeout: 5_000 })

    // The context menu container must have role="menu".
    await expect(contextMenu).toHaveAttribute('role', 'menu')

    // All transition children must have role="menuitem".
    // Task 1 status='in-progress' → valid_transitions=['todo', 'review', 'archived'] → 3 items.
    const menuItems = contextMenu.locator('[role="menuitem"]')
    await expect(menuItems).toHaveCount(3)
  })

  test('context_menu_clamps_to_viewport_right_edge', async ({ page }) => {
    const card = page.locator('[data-testid="task-card"][data-id="1"]')
    await card.waitFor({ state: 'visible', timeout: 8_000 })
    await card.evaluate((element) => element.scrollIntoView({ block: 'nearest', inline: 'end' }))

    const cardBox = await card.boundingBox()
    const viewport = await page.evaluate(() => ({ width: window.innerWidth, height: window.innerHeight }))
    expect(cardBox, 'task card must be measurable after edge alignment').not.toBeNull()

    await page.mouse.click(
      Math.min(viewport.width - 2, cardBox!.x + cardBox!.width - 2),
      cardBox!.y + 24,
      { button: 'right' },
    )

    const contextMenu = page.locator('[data-testid="context-menu"]')
    await contextMenu.waitFor({ state: 'visible', timeout: 5_000 })

    await expect.poll(
      async () => {
        const menuBox = await contextMenu.boundingBox()
        expect(menuBox, 'context menu must be measurable after right-edge open').not.toBeNull()
        return menuBox!.x + menuBox!.width
      },
      { message: 'context menu should stay inside the right viewport edge' },
    ).toBeLessThanOrEqual(viewport.width - 8 + 0.5)
  })

  // AC-4: context menu must be keyboard-navigable with arrow keys.
  // GREEN (regression guard): KanbanBoard.tsx:382-391 handles ArrowDown/ArrowUp.
  // Task-local E2E proof required by AC-4. Must verify actual directional focus movement:
  // first item focused → ArrowDown → second item focused → ArrowUp → first item again.
  test('context_menu_keyboard_navigation_with_arrow_keys', async ({ page }) => {
    const card = page.locator('[data-testid="task-card"][data-id="1"]')
    await card.waitFor({ state: 'visible', timeout: 8_000 })
    await card.click({ button: 'right' })

    const contextMenu = page.locator('[data-testid="context-menu"]')
    await contextMenu.waitFor({ state: 'visible', timeout: 5_000 })

    const menuItems = contextMenu.locator('[role="menuitem"]')
    const firstItem = menuItems.nth(0)
    const secondItem = menuItems.nth(1)

    // KanbanBoard useEffect focuses the first menuitem when context menu opens.
    await expect(firstItem).toBeFocused()

    // ArrowDown must move focus to the SECOND (next) menuitem — not just any menuitem.
    await page.keyboard.press('ArrowDown')
    await expect(secondItem, 'ArrowDown must move focus to the second menuitem').toBeFocused()

    // ArrowUp must move focus BACK to the first menuitem.
    await page.keyboard.press('ArrowUp')
    await expect(firstItem, 'ArrowUp must move focus back to the first menuitem').toBeFocused()
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
