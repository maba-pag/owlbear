/**
 * RED phase Playwright E2E tests for #1626: P3-06 — Focus-visible rings (PDS focus styling)
 *
 * AC-1: Every element matching `button, [role="button"], [role="menuitem"], input, a`
 *       shows a visible :focus-visible outline when it receives keyboard focus —
 *       Playwright assertion on outline-style and outline-color.
 *
 * AC-2 (behavioral proxy): Card div[role="button"] outline-offset must be 2px after
 *       token migration (--pds-state-focus → --color-focus). Currently 1px → FAILS.
 *
 * RED reasons for AC-1 tests:
 *   - No global :focus-visible CSS rule exists for `button, [role="button"],
 *     [role="menuitem"], input, a` in the application CSS.
 *   - button (.icon-button): UA default is `outline: auto` (not 'solid') — FAILS.
 *   - article[role="button"] (DecisionViewport): non-natively-focusable element gets
 *     no UA focus ring → `outline: none` (not 'solid') — FAILS.
 *   - div[role="menuitem"] (context menu): UA gives `outline: none` for div — FAILS.
 *   - a link (DecisionViewport): UA default is `outline: auto` (not 'solid') — FAILS.
 *   - outlineColor for all: UA supplies a system accent color ≠ rgb(26, 68, 234) — FAILS.
 *
 * RED reason for AC-2 behavioral proxy:
 *   - Card.css has `outline-offset: 1px`; AC requires 2px after migration — FAILS.
 *
 * CSS source-contract coverage for AC-2 (--pds-state-focus → --color-focus migration)
 * is in: serve/cockpit/web/src/__tests__/FocusVisibleCssSource_1626.test.ts
 *
 * Builder fix: add global :focus-visible rule using var(--color-focus) in a shared
 * CSS file (tokens.css or equivalent), and migrate Card.css offset to 2px.
 *
 * API isolation: all /api/* routes stubbed — no backend required.
 * LIFO route registration: catch-all registered first, specific routes last (highest priority).
 */
import { test, expect, type Page } from '@playwright/test'

// ─── PDS canonical focus color ────────────────────────────────────────────────
// var(--color-focus) from PDS Tailwind theme resolves to #1A44EA = rgb(26, 68, 234).
const PDS_FOCUS_COLOR = 'rgb(26, 68, 234)'

// ─── Fixture data ─────────────────────────────────────────────────────────────

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

const TASKS = {
  tasks: [
    {
      id: 1,
      title: 'Focus ring test task',
      status: 'todo',
      priority: 'important',
      updated: '2026-05-16T00:00:00+00:00',
      tags: [],
      blocked: false,
      block_reason: null,
      claimed: false,
    },
  ],
  mtime: 1_713_456_000,
}

// One pending decision — causes DecisionViewport to render an <a> link and
// an article[role="button"] in the sidecar panel, enabling AC-1 anchor/role-button tests.
const DECISION_ITEMS = [
  {
    id: 'dr-1626-001',
    task_id: 1,
    agent: 'builder',
    request_type: 'scope-decision',
    created: '2026-05-16T00:00:00+00:00',
    title: 'Focus ring test decision',
    body_preview: 'Test decision for focus ring E2E.',
    body: '## Context\n\nNeeded to surface DecisionViewport anchor.',
  },
]

// ─── API stub helper ───────────────────────────────────────────────────────────
// LIFO: catch-all registered first (lowest priority); specific routes last (highest priority).

async function stubApis(page: Page): Promise<void> {
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

  await page.route(/\/api\/sessions(\?.*)?$/, (route) =>
    route.fulfill({ json: { sessions: [] } }),
  )

  await page.route('/api/tasks/scan', (route) => route.fulfill({ json: [] }))

  await page.route('/api/decisions/pending', (route) =>
    route.fulfill({ json: { count: DECISION_ITEMS.length, items: DECISION_ITEMS } }),
  )

  await page.route('/api/tasks', (route) => route.fulfill({ json: TASKS }))
  await page.route('/api/board', (route) => route.fulfill({ json: BOARD }))
}

// ─── AC-1: Focus-visible outline on interactive elements ──────────────────────
//
// Verifies that `button, [role="button"], [role="menuitem"], input, a` elements
// show a visible :focus-visible outline using the PDS canonical pattern:
//   outline: 2px solid var(--color-focus);   /* resolves to rgb(26, 68, 234) */
//   outline-offset: 2px;
//
// In RED: No global :focus-visible CSS rule exists. Native elements (button, a)
// get the UA default `outline: auto` (not 'solid'); non-native elements (div, article
// with ARIA roles) get `outline: none` from the UA. Both fail the 'solid' check.
// The UA outline color is a system accent color, never rgb(26, 68, 234). Both fail.
//
// In GREEN: Global CSS rule `outline: 2px solid var(--color-focus)` is applied to
// all matching elements. Both outlineStyle and outlineColor assertions pass.

test.describe('TestFromAC_FocusVisibleOutline', () => {
  test.use({ viewport: { width: 1280, height: 800 } })

  test.beforeEach(async ({ page }) => {
    await stubApis(page)
    await page.goto('/')
    await page.waitForSelector('[data-region="workspace"]', { timeout: 10_000 })
  })

  // ── button: ThemeToggle (.icon-button) ──────────────────────────────────────

  // Happy path: button (.icon-button) shows outline-style 'solid' on keyboard focus (AC-1)
  // RED: Shell.css has no :focus-visible rule for .icon-button — UA applies `outline: auto`
  // which resolves outlineStyle to 'auto', not 'solid'.
  test('button (.icon-button): outlineStyle is solid on keyboard focus (AC-1)', async ({
    page,
  }) => {
    const themeToggle = page.locator('[data-testid="theme-toggle"]')
    await themeToggle.focus()

    const outlineStyle = await page.evaluate(
      () => getComputedStyle(document.activeElement as Element).outlineStyle,
    )

    expect(
      outlineStyle,
      'button.icon-button must show outline-style:solid with PDS :focus-visible rule. ' +
        "RED: no CSS rule → UA applies outline:auto (resolves to 'auto', not 'solid').",
    ).toBe('solid')
  })

  // Happy path: button (.icon-button) shows PDS focus color on keyboard focus (AC-1)
  // RED: UA focus ring uses a system accent color — never rgb(26, 68, 234).
  test('button (.icon-button): outlineColor is PDS focus blue rgb(26,68,234) on keyboard focus (AC-1)', async ({
    page,
  }) => {
    const themeToggle = page.locator('[data-testid="theme-toggle"]')
    await themeToggle.focus()

    const outlineColor = await page.evaluate(
      () => getComputedStyle(document.activeElement as Element).outlineColor,
    )

    expect(
      outlineColor,
      `button.icon-button must show outline-color:${PDS_FOCUS_COLOR} (var(--color-focus)). ` +
        'RED: no CSS rule → UA supplies a system accent color, not the PDS focus blue.',
    ).toBe(PDS_FOCUS_COLOR)
  })

  // ── [role="button"]: DecisionViewport article ────────────────────────────────
  //
  // DecisionViewport renders article[role="button"][tabIndex=0] for each pending DR.
  // Unlike Card (.card[role="button"]), this element has NO existing :focus-visible rule.
  // RED: article/div elements with ARIA roles get no UA focus ring → outlineStyle is 'none'.

  // Happy path: article[role="button"] (DR item) shows outline-style 'solid' on focus (AC-1)
  test('article[role="button"] (DecisionViewport DR item): outlineStyle is solid on focus (AC-1)', async ({
    page,
  }) => {
    const drItem = page.locator('[data-testid="decision-item-dr-1626-001"]')
    await expect(drItem).toBeVisible({ timeout: 5_000 })
    await drItem.focus()

    const outlineStyle = await page.evaluate(
      () => getComputedStyle(document.activeElement as Element).outlineStyle,
    )

    expect(
      outlineStyle,
      'article[role="button"] (DecisionViewport) must show outline-style:solid with PDS ' +
        ':focus-visible rule. RED: no CSS rule → UA gives no ring to non-native elements ' +
        "(outlineStyle is 'none').",
    ).toBe('solid')
  })

  // Happy path: article[role="button"] (DR item) shows PDS focus color on focus (AC-1)
  test('article[role="button"] (DecisionViewport DR item): outlineColor is PDS focus blue on focus (AC-1)', async ({
    page,
  }) => {
    const drItem = page.locator('[data-testid="decision-item-dr-1626-001"]')
    await expect(drItem).toBeVisible({ timeout: 5_000 })
    await drItem.focus()

    const outlineColor = await page.evaluate(
      () => getComputedStyle(document.activeElement as Element).outlineColor,
    )

    expect(
      outlineColor,
      `article[role="button"] must show outline-color:${PDS_FOCUS_COLOR} (var(--color-focus)). ` +
        'RED: no CSS rule → element has no outline (outlineColor is transparent or system color).',
    ).toBe(PDS_FOCUS_COLOR)
  })

  // ── [role="menuitem"]: context menu transition items ─────────────────────────
  //
  // KanbanBoard renders div[role="menuitem"][tabIndex=-1] inside the right-click context
  // menu. These are div elements with no UA focus ring.
  // RED: No :focus-visible CSS rule exists → outlineStyle is 'none' → FAILS.

  // Happy path: [role="menuitem"] shows outline-style 'solid' when focused (AC-1)
  test('[role="menuitem"] (context menu): outlineStyle is solid when focused (AC-1)', async ({
    page,
  }) => {
    // Open context menu via right-click on the task card
    const card = page.locator('[data-testid="task-card"]').first()
    await expect(card).toBeVisible({ timeout: 5_000 })
    await card.click({ button: 'right' })
    await page.waitForSelector('[data-testid="context-menu"]', { timeout: 5_000 })

    // Focus first transition menuitem programmatically (they have tabIndex=-1)
    const menuitem = page.locator('[data-testid="context-menu"] [role="menuitem"]').first()
    await menuitem.focus()

    const outlineStyle = await page.evaluate(
      () => getComputedStyle(document.activeElement as Element).outlineStyle,
    )

    expect(
      outlineStyle,
      '[role="menuitem"] must show outline-style:solid with PDS :focus-visible rule. ' +
        "RED: no CSS rule → UA gives no ring to div elements (outlineStyle is 'none').",
    ).toBe('solid')
  })

  // Happy path: [role="menuitem"] shows PDS focus color when focused (AC-1)
  test('[role="menuitem"] (context menu): outlineColor is PDS focus blue when focused (AC-1)', async ({
    page,
  }) => {
    const card = page.locator('[data-testid="task-card"]').first()
    await expect(card).toBeVisible({ timeout: 5_000 })
    await card.click({ button: 'right' })
    await page.waitForSelector('[data-testid="context-menu"]', { timeout: 5_000 })

    const menuitem = page.locator('[data-testid="context-menu"] [role="menuitem"]').first()
    await menuitem.focus()

    const outlineColor = await page.evaluate(
      () => getComputedStyle(document.activeElement as Element).outlineColor,
    )

    expect(
      outlineColor,
      `[role="menuitem"] must show outline-color:${PDS_FOCUS_COLOR} (var(--color-focus)). ` +
        'RED: no CSS rule → element has no outline (outlineColor is transparent).',
    ).toBe(PDS_FOCUS_COLOR)
  })

  // ── a: DecisionViewport anchor link ─────────────────────────────────────────
  //
  // DecisionViewport renders <a href="#task-{id}"> for each pending DR.
  // In RED: no app CSS :focus-visible rule for `a` → UA applies `outline: auto`
  // (system accent color), not the 2px solid PDS blue.

  // Happy path: a element shows outline-style 'solid' on keyboard focus (AC-1)
  test('a element (DecisionViewport anchor): outlineStyle is solid on keyboard focus (AC-1)', async ({
    page,
  }) => {
    const anchor = page.locator('[data-testid="decision-task-ref-dr-1626-001"]')
    await expect(anchor).toBeVisible({ timeout: 5_000 })
    await anchor.focus()

    const outlineStyle = await page.evaluate(
      () => getComputedStyle(document.activeElement as Element).outlineStyle,
    )

    expect(
      outlineStyle,
      'a element must show outline-style:solid with PDS :focus-visible rule. ' +
        "RED: no CSS rule → UA applies outline:auto for links (resolves to 'auto', not 'solid').",
    ).toBe('solid')
  })

  // Happy path: a element shows PDS focus color on keyboard focus (AC-1)
  test('a element (DecisionViewport anchor): outlineColor is PDS focus blue on keyboard focus (AC-1)', async ({
    page,
  }) => {
    const anchor = page.locator('[data-testid="decision-task-ref-dr-1626-001"]')
    await expect(anchor).toBeVisible({ timeout: 5_000 })
    await anchor.focus()

    const outlineColor = await page.evaluate(
      () => getComputedStyle(document.activeElement as Element).outlineColor,
    )

    expect(
      outlineColor,
      `a element must show outline-color:${PDS_FOCUS_COLOR} (var(--color-focus)). ` +
        'RED: no CSS rule → UA supplies a system accent color, not rgb(26, 68, 234).',
    ).toBe(PDS_FOCUS_COLOR)
  })
})

// ─── AC-2 (behavioral proxy): Card outline-offset migration ───────────────────
//
// Card.css currently: `outline: 2px solid var(--pds-state-focus); outline-offset: 1px;`
// AC-2 requires: `outline: 2px solid var(--color-focus); outline-offset: 2px;`
//
// Since --pds-state-focus and --color-focus resolve to the same hex (#1A44EA),
// only outline-offset distinguishes pre-migration (1px) from post-migration (2px).
// This Playwright test checks the computed outline-offset on a focused Card.
//
// RED: Card.css has outline-offset: 1px → computed outlineOffset is '1px' → FAILS.
// GREEN: After migration, computed outlineOffset is '2px' → PASSES.

test.describe('TestFromAC_CardFocusTokenMigration', () => {
  test.use({ viewport: { width: 1280, height: 800 } })

  test.beforeEach(async ({ page }) => {
    await stubApis(page)
    await page.goto('/')
    await page.waitForSelector('[data-testid="task-card"]', { timeout: 10_000 })
  })

  // Boundary: Card div[role="button"] has outline-offset 2px after migration (AC-2)
  // RED: Card.css still has `outline-offset: 1px` → assertion for '2px' FAILS.
  test('div[role="button"] (.card): outlineOffset is 2px on keyboard focus after --color-focus migration (AC-2)', async ({
    page,
  }) => {
    const card = page.locator('[data-testid="task-card"]').first()
    await card.focus()

    const outlineOffset = await page.evaluate(
      () => getComputedStyle(document.activeElement as Element).outlineOffset,
    )

    expect(
      outlineOffset,
      'Card div[role="button"] must have outline-offset:2px after --pds-state-focus → ' +
        '--color-focus migration. RED: Card.css still has outline-offset:1px.',
    ).toBe('2px')
  })

})
