/**
 * AC-3: Dual-theme WCAG 2.1 AA accessibility sweep — cockpit visual redesign (#1629).
 *
 * Verifies board, task detail, and modal surfaces produce zero AxeBuilder violations
 * under both .scheme-light and .scheme-dark document color schemes.
 *
 * Theme injection: localStorage is seeded before page load via addInitScript so the
 * useTheme() hook resolves the target scheme before first render — no post-load
 * DOM patching needed.
 *
 * Surfaces tested per theme (full parity with accessibility-sweep.spec.ts):
 *   1. Board view
 *   2. Ideas workspace
 *   3. Memory workspace
 *   4. Task detail modal
 *   5. Workspace Status popover
 *   6. Workspace Status issue list
 *   7. FilterPanel (open state)
 *   8. ArchivalModal
 *   9. ConfirmDialog
 *  10. CleanupPanel confirm dialog
 *  11. RepairPanel confirm dialog
 *
 * Route mocks use Playwright LIFO ordering: catch-all first, specific routes last.
 */

import { test, expect, type Page } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'

// ─── Constants ────────────────────────────────────────────────────────────────

/** WCAG 2.1 AA tag set matching AC-3 specification. */
const WCAG_TAGS = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'] as const

const STATUSES = ['research', 'backlog', 'todo', 'in-progress', 'review', 'docs', 'done']
const PRIORITIES = ['critical', 'needed', 'important', 'nice-to-have', 'someday']

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

const MEMORY_ENTRIES = [
  {
    id: 'memory-dualtheme-001',
    title: 'Morning operator cadence',
    content: 'Use the top-level cockpit routes to review decisions, memory, and ideas before moving work.',
    categories: ['process', 'workflow'],
    confidence: 0.92,
    state: 'pending',
    scope_agents: ['builder', 'reviewer'],
    source_agent: 'auditor',
    created_at: '2026-05-15T08:00:00+00:00',
    updated_at: '2026-05-16T08:00:00+00:00',
    approved_at: null,
  },
  {
    id: 'memory-dualtheme-002',
    title: 'Keep Cockpit routes dense and direct',
    content: 'Operational surfaces should prioritize scanning, editing, and decisions over explanatory copy.',
    categories: ['behaviour'],
    confidence: 0.88,
    state: 'curated',
    scope_agents: ['builder'],
    source_agent: 'reviewer',
    created_at: '2026-05-14T08:00:00+00:00',
    updated_at: '2026-05-15T08:00:00+00:00',
    approved_at: null,
  },
]

/** Provides a corrupted-file scan item so HealthBadge renders red and RepairPanel appears. */
const SCAN_ITEMS = [
  {
    code: 'E001',
    detail: 'Task file is corrupted',
    file_path: 'store/tasks/TASK-001.md',
  },
]

// ─── Helpers ──────────────────────────────────────────────────────────────────

/**
 * Register all API stubs.
 * LIFO: catch-all first (lowest priority), specific routes last (highest priority).
 */
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

  await page.route('/api/board', (route) => route.fulfill({ json: BOARD }))
  await page.route('/api/tasks', (route) =>
    route.fulfill({ json: { tasks: TASKS, mtime: 1_716_000_000 } }),
  )
  await page.route('/api/sessions', (route) => route.fulfill({ json: { sessions: [] } }))
  await page.route('/api/ideas', (route) =>
    route.fulfill({
      json: {
        content: '# Morning shape\n\n- [x] Review overnight work\n- [ ] Refine cockpit surfaces',
      },
    }),
  )
  await page.route('/api/memories', (route) =>
    route.fulfill({ json: { entries: MEMORY_ENTRIES, parse_errors: 0 } }),
  )
  await page.route('/api/tasks/scan', (route) => route.fulfill({ json: SCAN_ITEMS }))
  await page.route(/\/api\/tasks\/\d+$/, (route) => route.fulfill({ json: TASK_DETAIL }))
}

async function waitForCards(page: Page): Promise<void> {
  await page
    .locator('[data-testid="task-card"]')
    .first()
    .waitFor({ state: 'visible', timeout: 8_000 })
}

async function waitForWorkspaceSettled(page: Page): Promise<void> {
  await page.waitForFunction(() => {
    const panels = Array.from(document.querySelectorAll('[data-region="workspace"] > div'))
    return panels.length === 1 && panels.every((panel) => getComputedStyle(panel).opacity === '1')
  })
}

async function openWorkspaceStatus(page: Page): Promise<void> {
  await page.locator('[data-testid="health-badge"]').waitFor({ state: 'visible', timeout: 8_000 })
  await page.locator('[data-testid="health-badge"]').click()
  await page.locator('[data-testid="health-badge-popover"]').waitFor({ state: 'visible', timeout: 3_000 })
}

async function showIdeasEditor(page: Page): Promise<void> {
  const textarea = page.locator('textarea[aria-label="Ideas draft"]')
  if (await textarea.isVisible()) {
    return
  }

  await page.locator('[data-testid="ideas-preview-toggle"]').click()
  await textarea.waitFor({ state: 'visible', timeout: 5_000 })
}

async function openTaskDetail(page: Page): Promise<void> {
  const card = page.locator('[data-testid="task-card"]').first()
  await card.waitFor({ state: 'visible', timeout: 5_000 })
  await card.click()
  await page.locator('[data-testid="task-detail-modal"]').waitFor({ state: 'visible', timeout: 5_000 })
}

async function openTaskDetailEditor(page: Page): Promise<void> {
  await openTaskDetail(page)
  await page.locator('[data-testid="edit-details-button"]').click()
  await page.locator('[data-field="title"]').waitFor({ state: 'visible', timeout: 5_000 })
}

/** Format axe violations into a human-readable string for assertion messages. */
function formatViolations(
  violations: Array<{
    id: string
    impact?: string | null
    help: string
    nodes: Array<{ html: string }>
  }>,
): string {
  if (violations.length === 0) return 'no violations'
  return violations
    .map(
      (v) =>
        `[${v.impact ?? 'unknown'} — ${v.id}] ${v.help}\n  ${v.nodes.map((n) => n.html).join('\n  ')}`,
    )
    .join('\n\n')
}

// ─── Dual-theme surface scans ─────────────────────────────────────────────────
//
// Each theme iteration registers the theme in localStorage via addInitScript
// so useTheme() resolves the correct scheme before first render (no FOUC).
//
// An assertion on html.classList verifies the theme was applied — prevents
// silent wrong-theme false-greens if useTheme() fails to read localStorage.

const THEMES = ['light', 'dark'] as const

for (const theme of THEMES) {
  test.describe(`CockpitVisualRedesignDualTheme_${theme}`, () => {
    test.use({ viewport: { width: 1280, height: 800 } })

    test.beforeEach(async ({ page }) => {
      // Seed theme before app loads so useTheme() reads the correct value from storage.
      await page.addInitScript((t: string) => {
        localStorage.setItem('owlbear-theme', t)
      }, theme)
      await stubApis(page)
      await page.goto('/')
      await waitForCards(page)
      await waitForWorkspaceSettled(page)
    })

    // ── Surface 1: board view ──────────────────────────────────────────────
    // Primary surface — board columns, task cards, status bar, filter toggle.
    test(`board view passes wcag2.1 aa under ${theme} theme (AC3)`, async ({ page }) => {
      await expect(
        page.locator('[data-testid="task-card"]').first(),
        'at least one task card must be visible before axe scan',
      ).toBeVisible()

      // Confirm correct theme class is active — no silent wrong-theme scan.
      await expect(
        page.locator('html'),
        `html element must carry class scheme-${theme}`,
      ).toHaveClass(new RegExp(`scheme-${theme}`))

      const results = await new AxeBuilder({ page }).withTags([...WCAG_TAGS]).analyze()
      expect(results.violations, formatViolations(results.violations)).toEqual([])
    })

    // ── Surface 2: Ideas workspace ────────────────────────────────────────
    // Ideas notebook route — editor shell, state chips, and native textarea.
    test(`ideas workspace passes wcag2.1 aa under ${theme} theme (AC3)`, async ({ page }) => {
      await page.goto('/ideas')
      await expect(
        page.locator('html'),
        `html element must carry class scheme-${theme}`,
      ).toHaveClass(new RegExp(`scheme-${theme}`))

      await expect(
        page.locator('[data-region="ideas-workspace"]'),
        'ideas workspace must be visible before axe scan',
      ).toBeVisible({ timeout: 8_000 })
      await showIdeasEditor(page)
      await expect(
        page.locator('textarea[aria-label="Ideas draft"]'),
        'ideas textarea must be visible before axe scan',
      ).toBeVisible({ timeout: 8_000 })
      await waitForWorkspaceSettled(page)

      const results = await new AxeBuilder({ page }).withTags([...WCAG_TAGS]).analyze()
      expect(results.violations, formatViolations(results.violations)).toEqual([])
    })

    // ── Surface 4: Memory workspace ──────────────────────────────────────
    // Memory route — filter controls, entry summaries, and state/category chips.
    test(`memory workspace passes wcag2.1 aa under ${theme} theme (AC3)`, async ({ page }) => {
      await page.goto('/memories')
      await expect(
        page.locator('html'),
        `html element must carry class scheme-${theme}`,
      ).toHaveClass(new RegExp(`scheme-${theme}`))

      await expect(
        page.locator('[data-testid="memory-tab"]'),
        'memory workspace must be visible before axe scan',
      ).toBeVisible({ timeout: 8_000 })
      await expect(
        page.locator('[data-testid="memory-entry"]').first(),
        'at least one memory entry must be visible before axe scan',
      ).toBeVisible({ timeout: 8_000 })
      await waitForWorkspaceSettled(page)

      const results = await new AxeBuilder({ page }).withTags([...WCAG_TAGS]).analyze()
      expect(results.violations, formatViolations(results.violations)).toEqual([])
    })

    // ── Surface 5: task detail modal ──────────────────────────────────────
    // Task detail panel — TaskFieldsEditor, TaskActions, metadata accordion.
    test(`task detail modal passes wcag2.1 aa under ${theme} theme (AC3)`, async ({ page }) => {
      await expect(
        page.locator('html'),
        `html element must carry class scheme-${theme}`,
      ).toHaveClass(new RegExp(`scheme-${theme}`))

      await openTaskDetailEditor(page)

      await expect(
        page.locator('[data-field="title"]'),
        'task detail modal [data-field="title"] must be visible before axe scan',
      ).toBeVisible({ timeout: 5_000 })

      const results = await new AxeBuilder({ page }).withTags([...WCAG_TAGS]).analyze()
      expect(results.violations, formatViolations(results.violations)).toEqual([])
    })

    // ── Surface 6: Workspace Status popover ──────────────────────────────
    // Workspace Status owns scan findings and care actions in the header.
    test(`workspace status popover passes wcag2.1 aa under ${theme} theme (AC3)`, async ({ page }) => {
      await expect(
        page.locator('html'),
        `html element must carry class scheme-${theme}`,
      ).toHaveClass(new RegExp(`scheme-${theme}`))

      const badge = page.locator('[data-testid="health-badge"]')
      await badge.waitFor({ state: 'visible', timeout: 8_000 })
      await expect(
        badge,
        'health-badge must have data-health="red" — /api/tasks/scan must have returned scan items',
      ).toHaveAttribute('data-health', 'red')

      await badge.click()
      await page.locator('[data-testid="health-badge-popover"]').waitFor({ state: 'visible', timeout: 3_000 })
      await expect(page.locator('[data-testid="cleanup-button"]')).toBeVisible()

      const results = await new AxeBuilder({ page }).withTags([...WCAG_TAGS]).analyze()
      expect(results.violations, formatViolations(results.violations)).toEqual([])
    })

    // ── Surface 7: HealthBadge popover ────────────────────────────────────
    // The HealthBadge popover opens when the health-badge button is clicked.
    // Renders a fixed-position div with role="dialog" listing scan issues.
    test(`health badge popover passes wcag2.1 aa under ${theme} theme (AC3)`, async ({ page }) => {
      await expect(
        page.locator('html'),
        `html element must carry class scheme-${theme}`,
      ).toHaveClass(new RegExp(`scheme-${theme}`))

      await page
        .locator('[data-testid="health-badge"]')
        .waitFor({ state: 'visible', timeout: 8_000 })
      await expect(
        page.locator('[data-testid="health-badge"]'),
        'health-badge must have data-health="red" — /api/tasks/scan must have returned scan items',
      ).toHaveAttribute('data-health', 'red')

      await page.locator('[data-testid="health-badge"]').click()
      await page
        .locator('[data-testid="health-badge-popover"]')
        .waitFor({ state: 'visible', timeout: 3_000 })

      const results = await new AxeBuilder({ page }).withTags([...WCAG_TAGS]).analyze()
      expect(results.violations, formatViolations(results.violations)).toEqual([])
    })

    // ── Surface 8: FilterPanel (open state) ──────────────────────────────
    // The FilterPanel is visible when panelOpen=true. Contains PDS search,
    // select, and multi-select inputs. Toggled by filter-toggle.
    test(`filter panel open state passes wcag2.1 aa under ${theme} theme (AC3)`, async ({ page }) => {
      await expect(
        page.locator('html'),
        `html element must carry class scheme-${theme}`,
      ).toHaveClass(new RegExp(`scheme-${theme}`))

      const filterToggle = page.locator('[data-testid="filter-toggle"]')
      await filterToggle.waitFor({ state: 'visible', timeout: 5_000 })
      await filterToggle.click()

      await expect(
        page.locator('[data-testid="filter-panel"]'),
        'filter-panel must be visible after clicking filter-toggle',
      ).toBeVisible({ timeout: 3_000 })

      const results = await new AxeBuilder({ page }).withTags([...WCAG_TAGS]).analyze()
      expect(results.violations, formatViolations(results.violations)).toEqual([])
    })

    // ── Surface 10: ArchivalModal ─────────────────────────────────────────
    // ArchivalModal opens when the user selects "archived" from the task context menu.
    // The context menu appears on right-click of a task card.
    test(`archival modal passes wcag2.1 aa under ${theme} theme (AC3)`, async ({ page }) => {
      await expect(
        page.locator('html'),
        `html element must carry class scheme-${theme}`,
      ).toHaveClass(new RegExp(`scheme-${theme}`))

      const card = page.locator('[data-testid="task-card"][data-id="1"]')
      await card.waitFor({ state: 'visible', timeout: 8_000 })

      await card.click({ button: 'right' })
      const contextMenu = page.locator('[data-testid="context-menu"]')
      await contextMenu.waitFor({ state: 'visible', timeout: 5_000 })

      await page.locator('[data-testid="transition-item"][data-status="archived"]').click()

      await page
        .locator('[data-testid="archival-modal"]')
        .waitFor({ state: 'attached', timeout: 5_000 })
      await page
        .locator('[data-testid="archival-submit"]')
        .waitFor({ state: 'visible', timeout: 5_000 })

      const results = await new AxeBuilder({ page }).withTags([...WCAG_TAGS]).analyze()
      expect(results.violations, formatViolations(results.violations)).toEqual([])
    })

    // ── Surface 11: ConfirmDialog ─────────────────────────────────────────
    // ConfirmDialog opens from the current TaskActions confirmation surface.
    test(`confirm dialog passes wcag2.1 aa under ${theme} theme (AC3)`, async ({ page }) => {
      await expect(
        page.locator('html'),
        `html element must carry class scheme-${theme}`,
      ).toHaveClass(new RegExp(`scheme-${theme}`))

      await openTaskDetail(page)

      await expect(
        page.locator('[data-testid="task-detail-modal"]'),
        'task detail modal must be visible before clicking unclaim',
      ).toBeVisible({ timeout: 5_000 })

      const unclaimBtn = page.locator('[data-testid="unclaim-action"]')
      await unclaimBtn.waitFor({ state: 'visible', timeout: 5_000 })
      await unclaimBtn.click()

      await page
        .locator('[data-testid="confirm-dialog"]')
        .waitFor({ state: 'attached', timeout: 5_000 })

      const results = await new AxeBuilder({ page }).withTags([...WCAG_TAGS]).analyze()
      expect(results.violations, formatViolations(results.violations)).toEqual([])
    })

    // ── Surface 12: CleanupPanel confirm dialog ───────────────────────────
    // CleanupPanel confirm dialog opens from Workspace Status.
    test(`cleanup panel confirm dialog passes wcag2.1 aa under ${theme} theme (AC3)`, async ({ page }) => {
      await expect(
        page.locator('html'),
        `html element must carry class scheme-${theme}`,
      ).toHaveClass(new RegExp(`scheme-${theme}`))

      await openWorkspaceStatus(page)

      const cleanupButton = page.locator('[data-testid="cleanup-button"]')
      await cleanupButton.waitFor({ state: 'visible', timeout: 5_000 })
      await cleanupButton.click()

      await expect(
        page.locator('[data-testid="cleanup-confirm-dialog"]'),
        'cleanup-confirm-dialog must be visible after clicking cleanup-button',
      ).toBeVisible({ timeout: 3_000 })

      const results = await new AxeBuilder({ page }).withTags([...WCAG_TAGS]).analyze()
      expect(results.violations, formatViolations(results.violations)).toEqual([])
    })

    // ── Surface 13: RepairPanel confirm dialog ───────────────────────────
    // RepairPanel confirm dialog opens from Workspace Status after scan issues load.
    test(`repair panel confirm dialog passes wcag2.1 aa under ${theme} theme (AC3)`, async ({
      page,
    }) => {
      await expect(
        page.locator('html'),
        `html element must carry class scheme-${theme}`,
      ).toHaveClass(new RegExp(`scheme-${theme}`))

      await page
        .locator('[data-testid="health-badge"]')
        .waitFor({ state: 'visible', timeout: 8_000 })
      await expect(
        page.locator('[data-testid="health-badge"]'),
        'health-badge must have data-health="red" — /api/tasks/scan must have returned items',
      ).toHaveAttribute('data-health', 'red')

      await openWorkspaceStatus(page)

      const repairButton = page.locator('[data-testid="repair-button"]')
      await repairButton.waitFor({ state: 'visible', timeout: 3_000 })
      await repairButton.click()

      await expect(
        page.locator('[data-testid="repair-confirm-dialog"]'),
        'repair-confirm-dialog must be visible after clicking repair-button',
      ).toBeVisible({ timeout: 3_000 })

      const results = await new AxeBuilder({ page }).withTags([...WCAG_TAGS]).analyze()
      expect(results.violations, formatViolations(results.violations)).toEqual([])
    })
  })
}
