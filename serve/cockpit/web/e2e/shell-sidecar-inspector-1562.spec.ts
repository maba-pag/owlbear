/**
 * RED phase Playwright E2E tests for #1562: P2-04 Shell and sidecar inspector behavior.
 *
 * BUILDER INSTRUCTION (#1568): Copy this file to the tracked E2E directory before implementing:
 *   cp .owlbear/scratch/1562-shell-sidecar-inspector.spec.ts serve/cockpit/web/e2e/shell-sidecar-inspector-1562.spec.ts
 *   git add serve/cockpit/web/e2e/shell-sidecar-inspector-1562.spec.ts
 *   cd serve/cockpit/web && npm run test:e2e -- shell-sidecar-inspector-1562  # must show failures
 *
 * Covers sidecar inspector composition, decision queue structure, keyboard
 * collapse contract, status-bar chrome hierarchy, and activity row/filter grouping.
 *
 * RED targets (failing against current implementation):
 *   AC-1(a): No [data-region="sidecar-header"] or heading outside tabs showing task title/ID
 *   AC-1(b): Metadata fields use unlabeled <span data-testid="field-*"> — no visible "Status:"/"Priority:" labels
 *   AC-1(c): No distinct body section ([data-region="sidecar-body"] or "Description" heading)
 *   AC-1(d): No identifiable activity/actions sub-regions inside sidecar
 *   AC-2:    DecisionViewport renders each item as <button data-testid="decision-item-*">
 *   AC-3(b): [data-region="sidecar-header"] does not exist after keyboard collapse/expand
 *   AC-4(a): <h1> uses SR-only clipping — rendered width ≤ 1px, invisible to users
 *   AC-5(a): ActivityTab renders session rows as div[role="button"] (ActivityTab.tsx current code)
 *   AC-5(b): ActivityTab filter controls are ungrouped sibling PButtons — no ARIA grouping role
 *
 * Regression guards (expected to pass — existing behavior):
 *   AC-3(a): Sidecar collapse toggle is keyboard-activatable via Enter
 *   AC-4(b): Nav rail active surface has aria-current="page"
 *   AC-4(c): Status-bar area contains at least one element with an accessible name (aria-label)
 *   AC-4(d): Nav rail button bounding box fits within nav-rail container bounds
 *
 * API mocking: all routes stubbed via page.route() — no real backend required.
 * Desktop viewport: 1280×800 (default Playwright Desktop Chrome).
 */
import { test, expect, type Page } from '@playwright/test'

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

const TASKS = [
  {
    id: 1,
    title: 'Implement cache layer',
    status: 'backlog',
    priority: 'important',
    updated: '2026-05-14T00:00:00+00:00',
    tags: [],
    blocked: false,
    block_reason: null,
    claimed: false,
  },
]

const TASK_DETAIL = {
  id: 1,
  title: 'Implement cache layer',
  status: 'backlog',
  priority: 'important',
  updated: '2026-05-14T00:00:00+00:00',
  created: '2026-05-13T00:00:00+00:00',
  tags: [],
  blocked: false,
  block_reason: null,
  claimed: false,
  claimed_at: null,
  dep_status: null,
  parent: null,
  depends_on: [],
  body: '## Context\n\nCache implementation details.',
}

const DECISION_ITEMS = [
  {
    id: 'dr-1562-001',
    task_id: 1,
    agent: 'builder',
    request_type: 'scope-decision',
    created: '2026-05-14T00:00:00+00:00',
    title: 'Confirm caching strategy',
    body_preview: 'Builder needs guidance on caching.',
    body: '## Context\n\nShould we use Redis or in-memory?',
  },
]

// Two sessions: 'running' is shown under default 'active' filter; 'released' is filtered out.
const SESSIONS = [
  {
    task_id: 1,
    state: 'running',
    agent: 'builder',
    started_at: '2026-05-14T10:00:00+00:00',
    duration: null,
    outcome: null,
  },
  {
    task_id: 2,
    state: 'released',
    agent: 'reviewer',
    started_at: '2026-05-14T09:00:00+00:00',
    duration: 3_600,
    outcome: 'success',
  },
]

// ─── API stub helpers ─────────────────────────────────────────────────────────

/**
 * Stub all API routes used by the Cockpit shell.
 * Catch-all registered first → lowest LIFO priority.
 * Specific routes registered after → higher LIFO priority.
 */
async function stubApis(page: Page): Promise<void> {
  // Catch-all: lowest priority — handles unknown endpoints gracefully
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

  // Handles /api/tasks/1, /api/tasks/2, etc. (specific task detail)
  await page.route('/api/tasks/*', (route) => route.fulfill({ json: TASK_DETAIL }))

  // Regex matches /api/sessions and /api/sessions?filter=all (query-string variant)
  await page.route(/\/api\/sessions(\?.*)?$/, (route) =>
    route.fulfill({ json: { sessions: SESSIONS } }),
  )

  await page.route('/api/decisions/pending', (route) =>
    route.fulfill({ json: { count: DECISION_ITEMS.length, items: DECISION_ITEMS } }),
  )

  // Registered last → highest LIFO priority (overrides /api/tasks/* for the scan path)
  await page.route('/api/tasks/scan', (route) => route.fulfill({ json: [] }))
}

/**
 * Navigate to the app root and select the first task to populate the sidecar detail panel.
 * Waits for the kanban board columns to render and for the task detail data to appear.
 */
async function navigateAndSelectTask(page: Page): Promise<void> {
  await page.goto('/')
  await page.waitForSelector('[data-column]', { timeout: 10_000 })
  await page.locator('[data-testid="task-card"]').first().click()
  // field-id renders when DetailTab has loaded task data
  await expect(page.locator('[data-testid="field-id"]')).toBeVisible({ timeout: 8_000 })
}

// ─── AC-1: Sidecar inspector composition ─────────────────────────────────────
//
// RED targets:
//   (a) No [data-region="sidecar-header"] or heading outside p-tabs exists in sidecar
//   (b) Metadata fields have no visible label text ("Status:" or "Priority:")
//   (c) No distinct body/description section identifiable by data-region or heading
//   (d) No identifiable activity / actions sub-region inside sidecar

test.describe('TestFromAC_SidecarInspectorComposition', () => {
  test.use({ viewport: { width: 1280, height: 800 } })

  test.beforeEach(async ({ page }) => {
    await stubApis(page)
    await navigateAndSelectTask(page)
  })

  test('sidecar header region exists outside tabs when task is selected — RED: no sidecar-header region', async ({
    page,
  }) => {
    // AC-1(a): [data-region="sidecar-header"] must appear outside <p-tabs> in the sidecar,
    //          showing the selected task title/ID. The DOM-hierarchy assertion (toHaveCount(0)
    //          for 'p-tabs [data-region="sidecar-header"]') mechanically proves outside-tab
    //          position — a build that moves the header inside <p-tabs> would fail here.
    const sidecarHeader = page.locator('[data-region="sidecar-header"]')
    await expect(sidecarHeader).toBeVisible()

    // DOM-hierarchy guard: sidecar-header must NOT be a descendant of p-tabs.
    // If the header were inside <p-tabs>, this count would be 1 not 0.
    await expect(page.locator('p-tabs [data-region="sidecar-header"]')).toHaveCount(0)
  })

  test('sidecar metadata fields have visible Status and Priority labels — RED: unlabeled spans', async ({
    page,
  }) => {
    // AC-1(b): Each metadata field must have a visible label element (e.g. "Status:", "Priority:").
    //
    // RED: DetailTab renders:
    //   <span data-testid="field-status">backlog</span>
    //   <span data-testid="field-id">1</span>
    // No visible "Status:" or "Priority:" label text is present → getByText fails.
    const statusLabel = page
      .locator('[data-region="sidecar"]')
      .getByText('Status:', { exact: true })
    await expect(statusLabel).toBeVisible()

    const priorityLabel = page
      .locator('[data-region="sidecar"]')
      .getByText('Priority:', { exact: true })
    await expect(priorityLabel).toBeVisible()

    // Pairing proof: label and value must coexist in the same parent container.
    // AC-1(b) refined: a detached label elsewhere in the sidecar must not pass.
    // DetailTab renders <p><strong>Status:</strong> <span data-testid="field-status">…</span></p>
    const statusContainer = page
      .locator('[data-region="sidecar"]')
      .locator('p', { hasText: 'Status:' })
      .first()
    await expect(statusContainer.locator('[data-testid="field-status"]')).toBeVisible()

    const priorityContainer = page
      .locator('[data-region="sidecar"]')
      .locator('p', { hasText: 'Priority:' })
      .first()
    await expect(priorityContainer.locator('[data-testid="field-priority"]')).toBeVisible()
  })

  test('sidecar has distinct body section for task description — RED: no sidecar-body region or Description heading', async ({
    page,
  }) => {
    // AC-1(c): A distinct body/description section must be identifiable by data-region
    //          or a heading element (h2/h3) inside the sidecar.
    //
    // RED: DetailTab has no [data-region="sidecar-body"] and no heading labeling the
    //      description/body area. TaskFieldsEditor renders a body textarea without a
    //      labeled section heading → none of the selectors below match.
    const bodySection = page.locator(
      '[data-region="sidecar"] [data-region="sidecar-body"], ' +
        '[data-region="sidecar"] h2:has-text("Description"), ' +
        '[data-region="sidecar"] h3:has-text("Description"), ' +
        '[data-region="sidecar"] h2:has-text("Body"), ' +
        '[data-region="sidecar"] h3:has-text("Body")',
    )
    await expect(bodySection).toBeVisible()
  })

  test('sidecar has identifiable activity and actions regions — RED: no sub-region markers', async ({
    page,
  }) => {
    // AC-1(d): Activity/history and actions regions must each be identifiable by
    //          data-region attribute or heading element inside the sidecar (light DOM).
    //
    // RED: No [data-region="activity"], [data-region="history"], [data-region="actions"],
    //      or labeled h2/h3 headings exist in the sidecar light DOM. PDS <p-tabs> tab
    //      labels live in shadow DOM, not accessible via standard locators.
    const activityRegion = page.locator(
      '[data-region="sidecar"] [data-region="activity"], ' +
        '[data-region="sidecar"] [data-region="history"], ' +
        '[data-region="sidecar"] h2:has-text("Activity"), ' +
        '[data-region="sidecar"] h2:has-text("History"), ' +
        '[data-region="sidecar"] h3:has-text("Activity")',
    )
    await expect(activityRegion).toBeVisible()
  })

  test('sidecar has identifiable actions region separate from activity/history — AC-1(d) actions proof', async ({
    page,
  }) => {
    // AC-1(d): BOTH the activity/history region AND the actions region must be individually
    //          identifiable. The prior test proves activity/history; this test proves actions.
    //
    // A build omitting the actions section would still pass the prior test.
    // This test closes that gap by asserting [data-region="actions"] or equivalent heading.
    // Use .first() because the combined locator may match both the section and
    // an h3 heading inside it — Playwright strict mode requires a single match.
    const actionsRegion = page
      .locator(
        '[data-region="sidecar"] [data-region="actions"], ' +
          '[data-region="sidecar"] h2:has-text("Actions"), ' +
          '[data-region="sidecar"] h3:has-text("Actions")',
      )
      .first()
    await expect(actionsRegion).toBeVisible()
  })
})

// ─── AC-2: Decision queue composition ────────────────────────────────────────
//
// RED targets:
//   Decision items must be non-button structured containers — currently they
//   are rendered as <button data-testid="decision-item-*"> in DecisionViewport.tsx.

test.describe('TestFromAC_DecisionQueueComposition', () => {
  test.use({ viewport: { width: 1280, height: 800 } })

  test.beforeEach(async ({ page }) => {
    await stubApis(page)
    await page.goto('/')
    // Wait for decision items to render from /api/decisions/pending stub
    await expect(page.locator('[data-testid^="decision-item-"]')).not.toHaveCount(0, {
      timeout: 8_000,
    })
  })

  test('decision items are not button elements — RED: DecisionViewport uses button[data-testid="decision-item-*"]', async ({
    page,
  }) => {
    // AC-2: Each pending decision item must render as a non-button structured container
    //       (e.g. article, div with data-testid matching decision-card-* or similar),
    //       NOT as a <button> element.
    //
    // RED: DecisionViewport.tsx line ~56:
    //   <button type="button" data-testid={`decision-item-${item.id}`} onClick={...}>
    // Expected count of button[data-testid^="decision-item-"]: 0.
    // Fails because current count is 1 (one DR in fixture).
    const buttonItems = page.locator('button[data-testid^="decision-item-"]')
    await expect(buttonItems).toHaveCount(0)
  })

  test('decision items contain separately labeled fields for agent, type, age, and task reference — RED: no labeled structure', async ({
    page,
  }) => {
    // AC-2: Decision items must contain separately labeled fields for agent, request type,
    //       age, and task reference — not as concatenated child text nodes.
    //
    // RED: Current <button data-testid="decision-item-*"> has unlabeled PText children:
    //   <PText>{item.agent}</PText>
    //   <PText>{item.request_type}</PText>
    // No visible label text "Agent:" or "Request type:" exists inside any decision item.
    const agentLabel = page
      .locator('[data-testid^="decision-item-"]')
      .getByText('Agent:', { exact: true })
    await expect(agentLabel).toBeVisible()
  })

  test('decision items contain labeled Request type, Age, and Task reference fields — AC-2 completion', async ({
    page,
  }) => {
    // AC-2: All four labeled fields must be separately visible in each decision item:
    //       Agent:, Request type:, Age:, and Task: — not just Agent:.
    //
    // Prior spec proved only "Agent:" was present. This test closes the remaining gap.
    const item = page.locator('[data-testid^="decision-item-"]').first()
    await expect(item.getByText('Request type:', { exact: true })).toBeVisible()
    await expect(item.getByText('Age:', { exact: true })).toBeVisible()
    await expect(item.getByText('Task:', { exact: true })).toBeVisible()

    // Child-structure proof: each labeled field must be a distinct direct child element,
    // not concatenated text in a single node.
    // AC-2 refined: a flat non-button container with all labels in one node must not pass.
    // DecisionViewport renders each field as a separate <PText> direct child of <article>.
    for (const label of ['Agent:', 'Request type:', 'Age:', 'Task:']) {
      await expect(
        item.locator(':scope > *').filter({ hasText: label }),
      ).toHaveCount(1)
    }
  })
})

// ─── AC-3: Keyboard collapse / expand ────────────────────────────────────────
//
// AC-3(a): Collapse toggle is keyboard-activatable → sidecar content hidden (regression guard).
// AC-3(b): After expand, sidecar-header region is visible with task title/ID preserved (RED).

test.describe('TestFromAC_KeyboardCollapseExpand', () => {
  test.use({ viewport: { width: 1280, height: 800 } })

  test.beforeEach(async ({ page }) => {
    await stubApis(page)
    await navigateAndSelectTask(page)
  })

  test('sidecar collapse toggle hides content when activated via keyboard Enter — regression guard', async ({
    page,
  }) => {
    // AC-3(a): Reach sidecar-collapse button via sequential Tab presses from a reset
    //          starting point (not .focus() shortcut) — proving real Tab reachability.
    //          Then activate via Enter; assert #shell-sidecar-content gets aria-hidden="true".
    //
    // REGRESSION GUARD: Shell.tsx collapse button toggles isSidecarCollapsed →
    //   <div id="shell-sidecar-content" aria-hidden={isSidecarCollapsed ? 'true' : undefined}>
    // Expected to pass with current implementation.

    // Reset focus to document root before tabbing
    await page.locator('body').click()

    // Tab through focusable elements until sidecar-collapse is focused
    let reached = false
    for (let i = 0; i < 30; i++) {
      await page.keyboard.press('Tab')
      const isFocused = await page.evaluate(
        () => document.activeElement?.getAttribute('data-testid') === 'sidecar-collapse',
      )
      if (isFocused) {
        reached = true
        break
      }
    }
    expect(reached, 'sidecar-collapse toggle must be reachable via sequential Tab navigation').toBe(
      true,
    )

    await page.keyboard.press('Enter')

    const sidecarContent = page.locator('#shell-sidecar-content')
    await expect(sidecarContent).toHaveAttribute('aria-hidden', 'true')
  })

  test('sidecar header region is visible with task info after keyboard expand — RED: no sidecar-header region', async ({
    page,
  }) => {
    // AC-3(b): After a collapse + expand cycle via keyboard, [data-region="sidecar-header"]
    //          must be visible and display the same task title or ID as before collapse.
    //
    // RED: The sidecar has no [data-region="sidecar-header"] element (AC-1(a) RED target).
    //      Collapse works (AC-3(a) passes) but the header state-preservation check fails
    //      because the header region itself does not exist.
    const collapseToggle = page.locator('[data-testid="sidecar-collapse"]')

    // Collapse via keyboard
    await collapseToggle.focus()
    await page.keyboard.press('Enter')
    await expect(page.locator('#shell-sidecar-content')).toHaveAttribute('aria-hidden', 'true')

    // Expand again via keyboard
    await page.keyboard.press('Enter')
    await expect(page.locator('#shell-sidecar-content')).not.toHaveAttribute('aria-hidden', 'true')

    // Assert sidecar-header region is visible and shows task title/ID (state preserved)
    // RED: no [data-region="sidecar-header"] exists → toBeVisible() fails.
    const sidecarHeader = page.locator('[data-region="sidecar-header"]')
    await expect(sidecarHeader).toBeVisible()

    // Verify the header contains the task title or ID (not an empty placeholder)
    const headerText = await sidecarHeader.textContent()
    expect(headerText).toMatch(/Implement cache layer|#?1\b/)
  })
})

// ─── AC-4: Status bar and nav hierarchy ──────────────────────────────────────
//
// AC-4(a): Product-identity h1 has visible width > 50px (RED: SR-only clipping = 1px).
// AC-4(b): Nav rail active surface has aria-current="page" (regression guard).
// AC-4(c): Status-bar has at least one aria-labeled element (regression guard).
// AC-4(d): Nav rail button fits within nav-rail container (regression guard).

test.describe('TestFromAC_StatusBarNavHierarchy', () => {
  test.use({ viewport: { width: 1280, height: 800 } })

  test.beforeEach(async ({ page }) => {
    await stubApis(page)
    await page.goto('/')
    await page.waitForSelector('[data-column]', { timeout: 10_000 })
  })

  test('product-identity h1 has visible rendered width greater than 50px — RED: SR-only clipping', async ({
    page,
  }) => {
    // AC-4(a): The status-bar product-identity element must have non-zero rendered width
    //          and height — not visually hidden by SR-only clipping.
    //
    // RED: Shell.tsx renders the <h1> with SR-only style:
    //   { position:'absolute', width:'1px', height:'1px',
    //     clip:'rect(0,0,0,0)', overflow:'hidden', margin:'-1px', ... }
    // getBoundingClientRect().width === 1px — fails the 50px minimum for a visible heading.
    const h1 = page.locator('[data-region="status-bar"] h1')
    await expect(h1).toHaveCount(1, { timeout: 5_000 })

    const box = await h1.boundingBox()
    expect(box).not.toBeNull()
    // A visible product-identity element should be significantly wider than 1px.
    // SR-only h1 (width:1px via clip) fails this threshold.
    expect(box!.width).toBeGreaterThan(50)
  })

  test('nav rail active surface has aria-current="page" — regression guard', async ({ page }) => {
    // AC-4(b): The active nav rail surface must have aria-current="page".
    //
    // REGRESSION GUARD: Shell.tsx renders:
    //   <PButton data-surface="kanban" aria-current="page" ...>Kanban</PButton>
    // Expected to pass with current implementation.
    const activeNavItem = page.locator('[data-region="nav-rail"] [aria-current="page"]')
    await expect(activeNavItem).toBeVisible()
  })

  test('status-bar contains at least one element with an accessible name — regression guard', async ({
    page,
  }) => {
    // AC-4(c): Each status-bar control (health, DR count, cleanup, theme) must have a
    //          distinguishing accessible name via aria-label or visible text.
    //
    // REGRESSION GUARD: Verifies at least one aria-labeled element exists in the status bar.
    // ThemeToggle, DRStatusIndicator, CleanupPanel, HealthBadge each have aria-labels.
    const statusBar = page.locator('[data-region="status-bar"]')
    await expect(statusBar).toBeVisible()

    const labeledControls = statusBar.locator('[aria-label]')
    await expect(labeledControls).not.toHaveCount(0)
  })

  test('each named status-bar control has an individually distinguishable accessible name — per-control AC-4(c)', async ({
    page,
  }) => {
    // AC-4(c): EACH named control must independently have a distinguishing accessible name.
    //          Prior spec only checked "at least one labeled element" — a single labeled
    //          control would satisfy it even if health, cleanup, or theme were unlabeled.
    //
    // DR count indicator — aria-label="Pending decision requests: N"
    const drIndicator = page.locator('[data-testid="dr-indicator"]')
    await expect(drIndicator).toBeVisible()
    await expect(drIndicator).toHaveAttribute('aria-label', /Pending decision requests/)

    // Theme toggle — aria-label="Theme mode: ..."
    const themeToggle = page.locator('[data-testid="theme-toggle"]')
    await expect(themeToggle).toBeVisible()
    await expect(themeToggle).toHaveAttribute('aria-label', /Theme mode/)

    // Cleanup trigger button — proves accessible name by role + name lookup.
    // PDS <p-button> slotted text is in shadow DOM so toHaveAccessibleName() returns
    // empty on the host; getByRole finds the button via its computed accessible name.
    const cleanupButton = page.locator('[data-testid="cleanup-button"]')
    await expect(cleanupButton).toBeVisible()
    // Accessible name comes from slotted text "Cleanup" visible in the rendered button
    await expect(
      page.locator('[data-region="status-bar"]').getByRole('button', { name: /Cleanup/i }),
    ).toBeVisible()

    // Health badge — conditionally rendered when scan completes; aria-label reflects health
    const healthBadge = page.locator('[data-testid="health-badge"]')
    await expect(healthBadge).toBeVisible({ timeout: 8_000 })
    await expect(healthBadge).toHaveAttribute('aria-label', /Health/)
  })

  test('nav rail text fits within nav-rail container with no horizontal overflow — regression guard', async ({
    page,
  }) => {
    // AC-4(d): Nav rail text bounding box must fit within the nav-rail container bounding box
    //          (no horizontal overflow).
    //
    // REGRESSION GUARD: Uses scrollWidth > clientWidth DOM check, which detects content
    // overflow regardless of PDS p-button shadow DOM layout quirks (host element bounding
    // boxes can extend beyond the container due to negative margin offsets in PDS internals).
    // Expected to pass: the nav rail has a fixed width and a single short label ("Kanban").
    const navRail = page.locator('[data-region="nav-rail"]')
    await expect(navRail).toBeVisible()

    const hasHorizontalOverflow = await navRail.evaluate(
      (el) => el.scrollWidth > el.clientWidth,
    )
    expect(hasHorizontalOverflow).toBe(false)
  })
})

// ─── AC-5: Activity rows and filters ─────────────────────────────────────────
//
// RED targets:
//   (a) ActivityTab session rows use div[role="button"] — must use semantic elements instead
//   (b) ActivityTab filter controls are ungrouped sibling PButtons — must have ARIA grouping role

test.describe('TestFromAC_ActivityRowsAndFilters', () => {
  test.use({ viewport: { width: 1280, height: 800 } })

  test.beforeEach(async ({ page }) => {
    await stubApis(page)
    await page.goto('/')
    await page.waitForSelector('[data-column]', { timeout: 10_000 })
  })

  test('activity session rows are not rendered as div[role=button] — RED: ActivityTab uses div[role="button"]', async ({
    page,
  }) => {
    // AC-5(a): Activity session rows must NOT be div[role="button"]. They must use
    //          semantic elements (tr, li, or container without role="button") with
    //          distinct child elements for agent, duration, and outcome.
    //
    // RED: ActivityTab.tsx renders:
    //   <div data-testid="session-row" role="button" tabIndex={0} ...>
    // Sessions arrive via /api/sessions?filter=all stub. Default filter is 'active'
    // which includes the 'running' session → at least one session-row in DOM.

    // Wait for session rows to attach to DOM (ActivityTab fetches on mount;
    // state:'attached' works regardless of CSS visibility from PDS tab hiding)
    await page.locator('[data-testid="session-row"]').first().waitFor({
      state: 'attached',
      timeout: 10_000,
    })

    // Verify rows are present (precondition: at least one row exists)
    const totalRowCount = await page.evaluate(
      () => document.querySelectorAll('[data-testid="session-row"]').length,
    )
    expect(totalRowCount).toBeGreaterThan(0)

    // RED assertion: current impl has div[role="button"] rows → count is non-zero → fails
    const divButtonRowCount = await page.evaluate(
      () => document.querySelectorAll('div[role="button"][data-testid="session-row"]').length,
    )
    expect(divButtonRowCount).toBe(0)
  })

  test('activity filter controls are wrapped in an ARIA grouping container — RED: ungrouped sibling PButtons', async ({
    page,
  }) => {
    // AC-5(b): Filter controls must be wrapped in a container with role="radiogroup",
    //          role="tablist", role="toolbar", or equivalent ARIA grouping — not as
    //          independent sibling buttons without a grouping parent.
    //
    // RED: ActivityTab.tsx wraps filter buttons in a plain <div> with no ARIA role:
    //   <div>
    //     <PButton data-testid="filter-active" aria-pressed="true">Active</PButton>
    //     <PButton data-testid="filter-all" ...>All</PButton>
    //     ...
    //   </div>
    // Walking up from [data-testid="filter-active"] finds no ancestor with a grouping role.

    // Wait for filter controls to attach to DOM (inside ActivityTab)
    await page.locator('[data-testid="filter-active"]').waitFor({
      state: 'attached',
      timeout: 10_000,
    })

    // Walk up the ancestor chain from the filter button looking for a grouping role
    const groupingRoleCount = await page.evaluate(() => {
      const filterButton = document.querySelector('[data-testid="filter-active"]')
      if (!filterButton) return -1 // sentinel: filter button not found at all
      let el: Element | null = filterButton.parentElement
      while (el && el !== document.body) {
        const role = el.getAttribute('role')
        if (
          role === 'radiogroup' ||
          role === 'tablist' ||
          role === 'toolbar' ||
          role === 'group'
        ) {
          return 1
        }
        el = el.parentElement
      }
      return 0
    })

    // Precondition: filter button was found in DOM
    expect(groupingRoleCount).not.toBe(-1)

    // RED: no ARIA grouping ancestor found (count=0) → expect >0 fails
    expect(groupingRoleCount).toBeGreaterThan(0)
  })

  test('activity session rows have a distinct outcome child element — RED: no session-outcome element', async ({
    page,
  }) => {
    // AC-5(a): Each session row must have distinct child elements for agent, duration, AND outcome.
    //          Prior spec only banned div[role="button"] rows — it never asserted an outcome child.
    //          Current ActivityTab.tsx has session-agent, session-task, session-state, and
    //          session-duration, but has no session-outcome element.
    //
    // RED: [data-testid="session-outcome"] is absent from ActivityTab session rows.
    //      The running session in the fixture has outcome: null — the builder must render
    //      a child element (e.g. "—" or the value) for outcome regardless of null vs set.

    // Wait for session rows to attach
    await page.locator('[data-testid="session-row"]').first().waitFor({
      state: 'attached',
      timeout: 10_000,
    })

    // Precondition: at least one row exists
    const rowCount = await page.evaluate(
      () => document.querySelectorAll('[data-testid="session-row"]').length,
    )
    expect(rowCount).toBeGreaterThan(0)

    const firstRow = page.locator('[data-testid="session-row"]').first()

    // Agent and duration children are present (sanity check)
    await expect(firstRow.locator('[data-testid="session-agent"]')).toBeAttached()
    await expect(firstRow.locator('[data-testid="session-duration"]')).toBeAttached()

    // RED: outcome child does not exist — toBeAttached() fails
    await expect(firstRow.locator('[data-testid="session-outcome"]')).toBeAttached()
  })
})
