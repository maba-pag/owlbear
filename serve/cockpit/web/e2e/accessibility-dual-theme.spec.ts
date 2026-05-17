/**
 * AC-3: Dual-theme WCAG 2.1 AA accessibility sweep — cockpit visual redesign (#1629).
 *
 * Verifies board, sidecar, and modal surfaces produce zero AxeBuilder violations
 * under both .scheme-light and .scheme-dark document color schemes.
 *
 * Theme injection: localStorage is seeded before page load via addInitScript so the
 * useTheme() hook resolves the target scheme before first render — no post-load
 * DOM patching needed.
 *
 * Surfaces tested per theme:
 *   1. Board view
 *   2. Sidecar detail view
 *   3. ResolveModal (DR resolution modal)
 *   4. RepairPanel confirm dialog — KNOWN RED: <span onClick> violates
 *      interactive-supports-focus (wcag2a, SC 2.1.1). Builder must replace
 *      with a proper interactive element under both themes.
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

const PENDING_DRS = [
  {
    id: 'dr-dualtheme-001',
    task_id: 1,
    agent: 'builder',
    request_type: 'scope-decision',
    created: '2026-05-16T00:00:00+00:00',
    title: 'Confirm caching strategy',
    body_preview: 'Builder needs guidance on caching.',
    body: '## Context\n\nShould we use Redis or in-memory cache?',
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
  await page.route('/api/decisions/pending', (route) =>
    route.fulfill({ json: { count: PENDING_DRS.length, items: PENDING_DRS } }),
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
    test.use({ viewport: { width: 1024, height: 768 } })

    test.beforeEach(async ({ page }) => {
      // Seed theme before app loads so useTheme() reads the correct value from storage.
      await page.addInitScript((t: string) => {
        localStorage.setItem('owlbear-theme', t)
      }, theme)
      await stubApis(page)
      await page.goto('/')
      await waitForCards(page)
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

    // ── Surface 2: sidecar detail view ────────────────────────────────────
    // Task detail panel — TaskFieldsEditor, TaskActions, metadata accordion.
    test(`sidecar detail view passes wcag2.1 aa under ${theme} theme (AC3)`, async ({ page }) => {
      await expect(
        page.locator('html'),
        `html element must carry class scheme-${theme}`,
      ).toHaveClass(new RegExp(`scheme-${theme}`))

      const card = page.locator('[data-testid="task-card"]').first()
      await card.waitFor({ state: 'visible', timeout: 5_000 })
      await card.click()

      await expect(
        page.locator('[data-field="title"]'),
        'sidecar [data-field="title"] must be visible before axe scan',
      ).toBeVisible({ timeout: 5_000 })

      const results = await new AxeBuilder({ page }).withTags([...WCAG_TAGS]).analyze()
      expect(results.violations, formatViolations(results.violations)).toEqual([])
    })

    // ── Surface 3: ResolveModal (modal surface) ────────────────────────────
    // DR resolution modal — opened from DRStatusIndicator popover.
    test(`resolve modal passes wcag2.1 aa under ${theme} theme (AC3)`, async ({ page }) => {
      await expect(
        page.locator('html'),
        `html element must carry class scheme-${theme}`,
      ).toHaveClass(new RegExp(`scheme-${theme}`))

      const drIndicator = page.locator('[data-testid="dr-indicator"]')
      await drIndicator.waitFor({ state: 'visible', timeout: 5_000 })
      await expect(
        drIndicator,
        'dr-indicator must have data-status="attention" — /api/decisions/pending must have returned items',
      ).toHaveAttribute('data-status', 'attention')

      await drIndicator.click()
      await page.locator('[data-testid="dr-popover"]').waitFor({ state: 'visible', timeout: 3_000 })

      const drItem = page.locator(`[data-testid="dr-item-${PENDING_DRS[0].id}"]`)
      await drItem.waitFor({ state: 'visible', timeout: 3_000 })
      await drItem.click()

      await page.locator('[data-testid="resolve-modal"]').waitFor({ state: 'visible', timeout: 3_000 })

      const results = await new AxeBuilder({ page }).withTags([...WCAG_TAGS]).analyze()
      expect(results.violations, formatViolations(results.violations)).toEqual([])
    })

    // ── Surface 4: RepairPanel confirm dialog (modal surface) ──────────────
    // KNOWN RED: <span data-testid="repair-confirm-btn" onClick> in RepairPanel.tsx
    // carries a click handler on a non-interactive <span> element. Axe flags this as
    // an `interactive-supports-focus` violation under wcag2a:
    //   SC 2.1.1 (keyboard): click target not keyboard reachable.
    // Test fails under BOTH themes until builder replaces the span with a <button>.
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

      await page.locator('[data-testid="health-badge"]').click()
      await page
        .locator('[data-testid="health-badge-popover"]')
        .waitFor({ state: 'visible', timeout: 3_000 })

      const repairButton = page.locator('[data-testid="repair-button"]')
      await repairButton.waitFor({ state: 'visible', timeout: 3_000 })
      await repairButton.click()

      await expect(
        page.locator('[data-testid="repair-confirm-dialog"]'),
        'repair-confirm-dialog must be visible after clicking repair-button',
      ).toBeVisible({ timeout: 3_000 })

      // AC3: KNOWN FAILING — <span onClick> on repair-confirm-btn violates
      // interactive-supports-focus (wcag2a / SC 2.1.1). Must fail under both themes.
      const results = await new AxeBuilder({ page }).withTags([...WCAG_TAGS]).analyze()
      expect(results.violations, formatViolations(results.violations)).toEqual([])
    })
  })
}
