/**
 * Playwright coverage for shell and task detail modal behavior.
 *
 * Covers task detail composition, decision route structure, keyboard
 * modal behavior, and status-bar chrome hierarchy.
 * API mocking: all routes stubbed via page.route(); no real backend required.
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
 * Navigate to the app root and select the first task to populate the task detail modal.
 * Waits for the kanban board columns to render and for the task detail modal to appear.
 */
async function navigateAndSelectTask(page: Page): Promise<void> {
  await page.goto('/')
  await page.waitForSelector('[data-column]', { timeout: 10_000 })
  await page.locator('[data-testid="task-card"]').first().click()
  await expect(page.locator('[data-testid="task-detail-modal-summary"]')).toBeVisible({ timeout: 8_000 })
  await expect(page.locator('[data-region="task-detail-body"]')).toBeVisible({ timeout: 8_000 })
}

async function expectTaskEditorLabelContract(page: Page): Promise<void> {
  const controls = [
    { selector: 'p-input-text[data-field="title"]', label: 'Title' },
    { selector: 'p-select[data-field="priority"]', label: 'Priority' },
    { selector: 'p-input-text[data-field="new-tag"]', label: 'Add tag' },
    { selector: 'p-input-text[data-field="depends_on"]', label: 'Depends on' },
    { selector: 'p-input-text[data-field="parent"]', label: 'Parent' },
  ]

  for (const control of controls) {
    const host = page.locator(control.selector)
    await expect(host).toBeVisible()
    const label = await host.evaluate((element) => {
      return (element as HTMLElement & { label?: string }).label ?? element.getAttribute('label')
    })
    expect(label).toBe(control.label)
    expect(await host.evaluate((element) => element.hasAttribute('hide-label'))).toBe(false)
  }
}

async function openTaskDetailEditor(page: Page): Promise<void> {
  await page.locator('[data-testid="edit-details-button"]').click()
  await expect(page.locator('[data-region="task-detail-edit-form"]')).toBeVisible()
}

// ─── AC-1: Task detail modal composition ────────────────────────────────────
//
// RED targets:
//   (a) PModal summary shows the selected task identity
//   (b) Metadata fields have no visible label text ("Status:" or "Priority:")
//   (c) No distinct body/description section identifiable by data-region or heading
//   (d) No identifiable activity / actions sub-region inside modal

test.describe('TestFromAC_TaskDetailModalComposition', () => {
  test.use({ viewport: { width: 1280, height: 800 } })

  test.beforeEach(async ({ page }) => {
    await stubApis(page)
    await navigateAndSelectTask(page)
  })

  test('task modal summary region shows selected task identity', async ({
    page,
  }) => {
    const modalSummary = page.locator('[data-testid="task-detail-modal-summary"]')
    await expect(modalSummary).toBeVisible()
    await expect(modalSummary).toContainText('Implement cache layer')
    await expect(page.locator('[data-region="sidecar-header"]')).toHaveCount(0)
    await expect(page.locator('p-tabs')).toHaveCount(0)
  })

  test('task modal metadata fields have visible Status and Priority labels', async ({
    page,
  }) => {
    const metadata = page.locator('[data-testid="task-detail-modal"] [data-region="task-detail-metadata"]')
    await expect(metadata).toBeVisible()
    await expect(metadata).not.toHaveJSProperty('tagName', 'P-ACCORDION')
    await expect(page.locator('[data-testid="field-id"]')).toBeVisible()

    await expect(metadata.locator('dt', { hasText: /^Status$/ })).toBeVisible()
    await expect(metadata.locator('[data-testid="field-status"]')).toBeVisible()

    await expect(metadata.locator('dt', { hasText: /^Priority$/ })).toBeVisible()
    await expect(metadata.locator('[data-testid="field-priority"]')).toBeVisible()
  })

  test('history control is compact secondary chrome', async ({ page }) => {
    const history = page.locator('[data-region="history"]')
    await expect(history).toBeVisible()
    const historyButton = history.locator('p-button[data-testid="history-tab"]')
    await expect(historyButton).toBeVisible()
    expect(await historyButton.evaluate((element) => {
      return (element as HTMLElement & { compact?: boolean }).compact ?? element.hasAttribute('compact')
    })).toBe(true)
  })

  test('task modal has distinct body section for task description', async ({
    page,
  }) => {
    // AC-1(c): A distinct body/description section must be identifiable by data-region
    //          or a heading element inside the task detail modal.
    const bodySection = page.locator(
      '[data-testid="task-detail-modal"] [data-region="task-detail-body"], ' +
        '[data-testid="task-detail-modal"] h2:has-text("Description"), ' +
        '[data-testid="task-detail-modal"] h3:has-text("Description"), ' +
        '[data-testid="task-detail-modal"] h2:has-text("Body"), ' +
        '[data-testid="task-detail-modal"] h3:has-text("Body")',
    )
    await expect(bodySection).toBeVisible()

    // AC-1(c) refined: the body section must contain the task's description content —
    // not just a visible wrapper or heading.
    // TaskFieldsEditor renders body as ReactMarkdown by default (editBody=false).
    // PTextarea (edit mode) uses PDS shadow DOM so native textarea is not accessible
    // via standard CSS selectors. The correct proof is content visibility.
    await expect(page.locator('[data-region="task-detail-body"]')).toContainText(
      'Cache implementation details',
    )
  })

  test('task detail opens in display mode with explicit edit affordance', async ({
    page,
  }) => {
    const details = page.locator('[data-region="task-detail-body"]')
    await expect(details).toContainText('Task details')
    await expect(details.locator('[data-testid="task-detail-display"]')).toBeVisible()
    await expect(details.locator('[data-testid="edit-details-button"]')).toBeVisible()
    await expect(details.locator('p-input-text[data-field="title"]')).toBeHidden()
    await expect(details.locator('p-select[data-field="priority"]')).toBeHidden()

    await openTaskDetailEditor(page)
    await expect(details.locator('p-input-text[data-field="title"]')).toBeVisible()
    await expect(details.locator('p-select[data-field="priority"]')).toBeVisible()
  })

  test('task modal has identifiable history region', async ({
    page,
  }) => {
    // AC-1(d): History must be identifiable inside the modal.
    const activityRegion = page.locator(
      '[data-testid="task-detail-modal"] [data-region="history"], ' +
        '[data-testid="task-detail-modal"] h2:has-text("History"), ' +
        '[data-testid="task-detail-modal"] h3:has-text("History")',
    )
    await expect(activityRegion).toBeVisible()
  })

  test('task modal has identifiable actions region separate from history', async ({
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
        '[data-testid="task-detail-modal"] [data-region="actions"], ' +
          '[data-testid="task-detail-modal"] h2:has-text("Actions"), ' +
          '[data-testid="task-detail-modal"] h3:has-text("Actions")',
      )
      .first()
    await expect(actionsRegion).toBeVisible()
  })

  test('task editor labels remain visible after priority and body mode interactions', async ({
    page,
  }) => {
    await openTaskDetailEditor(page)
    await expectTaskEditorLabelContract(page)

    await page.locator('p-select[data-field="priority"]').evaluate((element) => {
      element.dispatchEvent(new CustomEvent('change', { detail: { value: 'needed' }, bubbles: true }))
    })
    await expectTaskEditorLabelContract(page)

    await page.locator('[data-testid="body-edit-toggle"]').click()
    await expect(page.locator('p-textarea[data-field="body"]')).toBeVisible()
    const bodyTextarea = page.locator('p-textarea[data-field="body"]')
    const bodyLabel = await bodyTextarea.evaluate((element) => {
      return (element as HTMLElement & { label?: string }).label ?? element.getAttribute('label')
    })
    expect(bodyLabel).toBe('Task body')
    expect(await bodyTextarea.evaluate((element) => element.hasAttribute('hide-label'))).toBe(false)
    await expectTaskEditorLabelContract(page)

    await page.locator('[data-testid="body-edit-toggle"]').click()
    await expect(page.locator('p-textarea[data-field="body"]')).toHaveCount(0)
    await expectTaskEditorLabelContract(page)
  })

  test('task body uses consistent copy between preview and edit mode', async ({
    page,
  }) => {
    const details = page.locator('[data-region="task-detail-body"]')
    await expect(details).toContainText('Task body')
    await expect(details).not.toContainText('Brief')

    await openTaskDetailEditor(page)
    await page.locator('[data-testid="body-edit-toggle"]').click()
    await expect(details).not.toContainText('Brief')
    const bodyTextarea = page.locator('p-textarea[data-field="body"]')
    const bodyLabel = await bodyTextarea.evaluate((element) => {
      return (element as HTMLElement & { label?: string }).label ?? element.getAttribute('label')
    })
    expect(bodyLabel).toBe('Task body')
  })
})

// ─── AC-2: Decision route composition ───────────────────────────────────────

test.describe('TestFromAC_DecisionRouteComposition', () => {
  test.use({ viewport: { width: 1280, height: 800 } })

  test.beforeEach(async ({ page }) => {
    await stubApis(page)
    await page.goto('/decisions')
    await expect(page.locator('[data-testid="decisions-page"]')).toBeVisible({ timeout: 8_000 })
  })

  test('legacy DecisionViewport decision-item elements are absent from the shell', async ({
    page,
  }) => {
    await expect(page.locator('[data-testid^="decision-item-"]')).toHaveCount(0)
  })

  test('Decisions route exposes pending request identity', async ({
    page,
  }) => {
    const item = page.locator('[data-testid="dr-item-dr-1562-001"]')
    await expect(item).toBeVisible()
    await expect(item).toContainText('Confirm caching strategy')
    await expect(item).toContainText('builder')
    await expect(item).toContainText('1')
  })

  test('clicking a Decisions route item opens the PModal resolve workflow', async ({
    page,
  }) => {
    await page.locator('[data-testid="dr-item-dr-1562-001"]').click()
    const modal = page.locator('[data-testid="resolve-modal"]')
    await expect(modal).toBeVisible()
    await expect(modal).toContainText('Confirm caching strategy')
  })
})

// ─── AC-3: Keyboard modal close / no sidecar collapse ───────────────────────

test.describe('TestFromAC_TaskModalKeyboardContract', () => {
  test.use({ viewport: { width: 1280, height: 800 } })

  test.beforeEach(async ({ page }) => {
    await stubApis(page)
    await navigateAndSelectTask(page)
  })

  test('retired sidecar collapse toggle is absent from the keyboard contract', async ({
    page,
  }) => {
    await expect(page.locator('[data-testid="sidecar-collapse"]')).toHaveCount(0)
    await expect(page.locator('#shell-sidecar-content')).toHaveCount(0)
  })

  test('Escape closes the task detail modal and returns board width to the shell', async ({
    page,
  }) => {
    await expect(page.locator('[data-testid="task-detail-modal"]')).toBeVisible()
    await page.keyboard.press('Escape')
    await expect(page.locator('[data-testid="task-detail-modal"]')).toHaveCount(0)
    await expect(page.locator('[data-region="sidecar"]')).toHaveCount(0)
  })
})

// ─── AC-4: Status bar and nav hierarchy ──────────────────────────────────────
//
// AC-4(a): OwlBear identity is visible while the PCanvas title slot remains hidden.
// AC-4(b): Nav rail active surface has aria-current="page" (regression guard).
// AC-4(c): Status-bar has at least one aria-labeled element (regression guard).
// AC-4(d): Nav rail is compact and icon-only, with labels in accessible names.

test.describe('TestFromAC_StatusBarNavHierarchy', () => {
  test.use({ viewport: { width: 1280, height: 800 } })

  test.beforeEach(async ({ page }) => {
    await stubApis(page)
    await page.goto('/')
    await page.waitForSelector('[data-column]', { timeout: 10_000 })
  })

  test('product identity is visible without clipping the compact rail', async ({
    page,
  }) => {
    await expect(page.getByTestId('app-identity')).toBeVisible()
    await expect(page.getByTestId('app-identity')).toHaveText(/OwlBear/)
    await expect(page.getByTestId('app-identity')).toHaveText(/Cockpit/)
    await expect(page.getByRole('img', { name: 'Porsche' })).toHaveCount(0)
    const title = page.locator('[slot="title"]')
    await expect(title).toHaveText('OwlBear Cockpit')
    await expect(title).toHaveClass(/sr-only/)

    const viewport = page.viewportSize()
    const identityBox = await page.getByTestId('app-identity').boundingBox()
    const statusBox = await page.locator('[data-region="status-bar"]').boundingBox()
    const workspaceBox = await page.locator('[data-region="workspace"]').boundingBox()

    expect(viewport).not.toBeNull()
    expect(identityBox).not.toBeNull()
    expect(statusBox).not.toBeNull()
    expect(workspaceBox).not.toBeNull()
    const identityCenter = identityBox!.x + identityBox!.width / 2
    const workspaceCenter = workspaceBox!.x + workspaceBox!.width / 2
    expect(Math.abs(identityCenter - workspaceCenter)).toBeLessThan(24)
    expect(statusBox!.x + statusBox!.width).toBeGreaterThan(viewport!.width - 96)
    expect(statusBox!.x).toBeGreaterThan(identityBox!.x + identityBox!.width + 300)
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
    // AC-4(c): Each status-bar control (workspace status and theme) must have a
    //          distinguishing accessible name via aria-label or visible text.
    //
    // REGRESSION GUARD: Verifies at least one aria-labeled element exists in the status bar.
    // ThemeToggle and the workspace status trigger each have aria-labels.
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
    // Theme toggle — aria-label="Theme mode: ..."
    const themeToggle = page.locator('[data-testid="theme-toggle"]')
    await expect(themeToggle).toBeVisible()
    await expect(themeToggle).toHaveAttribute('aria-label', /Theme mode/)

    // Workspace status owns health and care actions.
    const healthBadge = page.locator('[data-testid="health-badge"]')
    await expect(healthBadge).toBeVisible({ timeout: 8_000 })
    await expect(healthBadge).toHaveAttribute('aria-label', /Workspace status/)
    await healthBadge.click()
    await expect(page.locator('[data-testid="health-badge-popover"]')).toBeVisible()
    await expect(page.locator('[data-testid="cleanup-button"]')).toBeVisible()
  })

  test('nav rail is icon-only while retaining accessible names', async ({
    page,
  }) => {
    const navRail = page.locator('[data-region="nav-rail"]')
    await expect(navRail).toBeVisible()
    const kanbanButton = navRail.locator('[data-surface="kanban"]')
    await expect(kanbanButton).toHaveAttribute('aria-label', 'Kanban')
    await expect(kanbanButton).toHaveAttribute('title', 'Kanban')
    await expect(kanbanButton.locator('p-icon')).toBeVisible()
    await expect(kanbanButton).not.toContainText('Kanban')

    const buttonBox = await kanbanButton.boundingBox()
    expect(buttonBox).not.toBeNull()
    expect(buttonBox!.width).toBeGreaterThanOrEqual(44)
    expect(buttonBox!.height).toBeGreaterThanOrEqual(44)

    const decisionsButton = navRail.locator('[data-surface="decisions"]')
    const badgeBox = await decisionsButton.locator('[data-testid="nav-badge"]').boundingBox()
    const railBox = await navRail.boundingBox()
    expect(badgeBox).not.toBeNull()
    expect(railBox).not.toBeNull()
    expect(badgeBox!.x).toBeGreaterThanOrEqual(railBox!.x)
    expect(badgeBox!.x + badgeBox!.width).toBeLessThanOrEqual(railBox!.x + railBox!.width + 0.5)
  })
})

// ─── AC-5: Activity is no longer a shell sidecar tab ────────────────────────

test.describe('TestFromAC_NoActivitySidecarTab', () => {
  test.use({ viewport: { width: 1280, height: 800 } })

  test.beforeEach(async ({ page }) => {
    await stubApis(page)
    await page.goto('/')
    await page.waitForSelector('[data-column]', { timeout: 10_000 })
  })

  test('shell does not mount ActivityTab session rows by default', async ({
    page,
  }) => {
    await expect(page.locator('[data-testid="session-row"]')).toHaveCount(0)
    await expect(page.locator('p-tabs')).toHaveCount(0)
  })

  test('shell does not mount retired activity filter controls by default', async ({
    page,
  }) => {
    await expect(page.locator('[data-testid="filter-active"]')).toHaveCount(0)
    await expect(page.locator('[data-testid="filter-all"]')).toHaveCount(0)
  })

  test('task detail modal remains focused on task fields rather than activity rows', async ({
    page,
  }) => {
    await page.locator('[data-testid="task-card"]').first().click()
    await expect(page.locator('[data-testid="task-detail-modal"]')).toBeVisible()
    await expect(page.locator('[data-field="title"]')).toBeVisible()
    await expect(page.locator('[data-testid="session-outcome"]')).toHaveCount(0)
  })
})
