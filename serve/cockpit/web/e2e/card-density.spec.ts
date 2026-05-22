/**
 * Playwright coverage for task card information density.
 *
 * Exercises rendered card metadata, priority, tag previews, overflow indicators,
 * state cues, and update recency across the board UI.
 */

import { test, expect, type Page } from '@playwright/test'

// --- Board fixture -----------------------------------------------------------

const BOARD = {
  statuses: [
    { name: 'research' },
    { name: 'backlog' },
    { name: 'todo' },
    { name: 'in-progress' },
    { name: 'review' },
    { name: 'docs' },
    { name: 'done' },
  ],
  priorities: ['critical', 'needed', 'important', 'nice-to-have', 'someday'],
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

// --- Task fixtures -----------------------------------------------------------

/** id=1 — ready task, critical priority, one tag — in todo column */
const TASK_READY = {
  id: 1,
  title: 'Ready task',
  status: 'todo',
  priority: 'critical',
  tags: ['frontend'],
  blocked: false,
  block_reason: null,
  claimed: false,
  dep_status: null,
  updated: '2026-05-14T10:00:00+00:00',
}

/** id=2 — blocked task — blocked=true — in todo column */
const TASK_BLOCKED = {
  id: 2,
  title: 'Blocked task',
  status: 'todo',
  priority: 'needed',
  tags: [],
  blocked: true,
  block_reason: 'Waiting on upstream',
  claimed: false,
  dep_status: null,
  updated: '2026-05-14T10:00:00+00:00',
}

/** id=3 — claimed task — claimed=true — in in-progress column */
const TASK_CLAIMED = {
  id: 3,
  title: 'Claimed task',
  status: 'in-progress',
  priority: 'needed',
  tags: [],
  blocked: false,
  block_reason: null,
  claimed: true,
  dep_status: null,
  updated: '2026-05-14T10:00:00+00:00',
}

/** id=4 — deps-unmet task — dep_status='blocked' — in todo column */
const TASK_DEPS_UNMET = {
  id: 4,
  title: 'Deps-unmet task',
  status: 'todo',
  priority: 'important',
  tags: ['backend'],
  blocked: false,
  block_reason: null,
  claimed: false,
  dep_status: 'blocked',
  updated: '2026-05-14T10:00:00+00:00',
}

/** id=5 — DR-pending task — pendingDRIds will include 5 via decisions API stub */
const TASK_DR_PENDING = {
  id: 5,
  title: 'DR-pending task',
  status: 'todo',
  priority: 'needed',
  tags: ['active-decision', 'frontend'],
  blocked: false,
  block_reason: null,
  claimed: false,
  dep_status: null,
  updated: '2026-05-14T10:00:00+00:00',
}

/** id=6 — 5 tags to trigger tag overflow indicator — in backlog column */
const TASK_MANY_TAGS = {
  id: 6,
  title: 'Many-tags task',
  status: 'backlog',
  priority: 'someday',
  tags: ['frontend', 'backend', 'phase-2', 'scope:cockpit', 'type:test'],
  blocked: false,
  block_reason: null,
  claimed: false,
  dep_status: null,
  updated: '2026-05-14T10:00:00+00:00',
}

/** id=7 — stale task updated months ago — in todo column */
const TASK_STALE = {
  id: 7,
  title: 'Stale task',
  status: 'todo',
  priority: 'nice-to-have',
  tags: [],
  blocked: false,
  block_reason: null,
  claimed: false,
  dep_status: null,
  updated: '2026-01-01T00:00:00+00:00',
}

const ALL_TASKS = [
  TASK_READY,
  TASK_BLOCKED,
  TASK_CLAIMED,
  TASK_DEPS_UNMET,
  TASK_DR_PENDING,
  TASK_MANY_TAGS,
  TASK_STALE,
]

// --- Pending DR fixture ------------------------------------------------------

/** Marks task id=5 as dr-pending via the decisions/pending API stub.
 *  Shell.tsx: pendingDRIds = new Set(pendingDRItems.map(dr => dr.task_id))
 *  So task_id=5 causes computeSignal to return 'dr-pending' for card id=5. */
const PENDING_DR_FOR_TASK_5 = {
  count: 1,
  items: [
    {
      id: 'dr-1565-1',
      task_id: 5,
      agent: 'test-writer',
      request_type: 'decision',
      created: '2026-05-14T10:00:00+00:00',
      title: 'Test decision request for task 5',
      body: 'Test DR body.',
      body_preview: 'Test DR body.',
    },
  ],
}

const NO_PENDING_DRS = { count: 0, items: [] as object[] }

// --- API stub ----------------------------------------------------------------

async function stubApis(
  page: Page,
  pendingDRs: { count: number; items: object[] } = NO_PENDING_DRS,
): Promise<void> {
  // Generic catch-all registered FIRST — specific routes registered after take
  // precedence (Playwright route() matching is LIFO: last registered wins).
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
    route.fulfill({ json: { tasks: ALL_TASKS, mtime: 1_715_644_800 } }),
  )
  await page.route('/api/sessions', (route) => route.fulfill({ json: { sessions: [] } }))
  await page.route('/api/decisions/pending', (route) => route.fulfill({ json: pendingDRs }))
  await page.route('/api/tasks/scan', (route) => route.fulfill({ json: [] }))
}

async function loadBoard(
  page: Page,
  pendingDRs: { count: number; items: object[] } = NO_PENDING_DRS,
): Promise<void> {
  await stubApis(page, pendingDRs)
  await page.goto('/')
  await page.locator('[data-region="workspace"]').waitFor({ state: 'visible', timeout: 8_000 })
}

// --- AC-1 | Card rendering fixtures — id, priority, tags, state cues ---------

test.describe('AC-1 | Card rendering fixtures — id, priority, tags, state signals', () => {
  test('card displays task id as a visible element', async ({ page }) => {
    await loadBoard(page)
    const card = page.locator('[data-testid="task-card"][data-id="1"]')
    await card.waitFor({ state: 'visible', timeout: 6_000 })
    await expect(card.locator('[data-testid="card-id"]')).toBeVisible({ timeout: 2_000 })
  })

  test('card keeps priority in data and accessible text without a visible priority chip', async ({ page }) => {
    await loadBoard(page)
    const card = page.locator('[data-testid="task-card"][data-id="1"]')
    await card.waitFor({ state: 'visible', timeout: 6_000 })
    await expect(card.locator('[data-testid="card-priority"]')).toHaveCount(0)
    await expect(card).toHaveAttribute('data-priority', 'critical')
    await expect(card).toHaveAttribute('aria-label', /critical priority/)
  })

  test('card with tags displays tag preview', async ({ page }) => {
    await loadBoard(page)
    const card = page.locator('[data-testid="task-card"][data-id="1"]')
    await card.waitFor({ state: 'visible', timeout: 6_000 })
    await expect(card.locator('[data-testid="card-tags"]')).toBeVisible({ timeout: 2_000 })
  })

  test('card with five tags shows overflow indicator', async ({ page }) => {
    await loadBoard(page)
    // Task 6 has 5 tags — exceeds any reasonable preview slot limit.
    const card = page.locator('[data-testid="task-card"][data-id="6"]')
    await card.waitFor({ state: 'visible', timeout: 6_000 })
    await expect(card.locator('[data-testid="card-tag-overflow"]')).toBeVisible({ timeout: 2_000 })
  })

  test('blocked card shows blocked primary signal without duplicate cue text', async ({ page }) => {
    await loadBoard(page)
    const card = page.locator('[data-testid="task-card"][data-id="2"]')
    await card.waitFor({ state: 'visible', timeout: 6_000 })
    await expect(card.locator('[data-testid="card-signal"]')).toContainText('Blocked', { timeout: 2_000 })
    await expect(card.locator('[data-testid="card-blocked-cue"]')).toHaveCount(0)
  })

  test('claimed card shows claimed primary signal without duplicate cue text', async ({ page }) => {
    await loadBoard(page)
    const card = page.locator('[data-testid="task-card"][data-id="3"]')
    await card.waitFor({ state: 'visible', timeout: 6_000 })
    await expect(card.locator('[data-testid="card-signal"]')).toContainText('Claimed', { timeout: 2_000 })
    await expect(card.locator('[data-testid="card-claimed-cue"]')).toHaveCount(0)
  })

  test('deps-unmet card shows dependency primary signal without duplicate cue text', async ({ page }) => {
    await loadBoard(page)
    const card = page.locator('[data-testid="task-card"][data-id="4"]')
    await card.waitFor({ state: 'visible', timeout: 6_000 })
    await expect(card.locator('[data-testid="card-signal"]')).toContainText('Dependencies', { timeout: 2_000 })
    await expect(card.locator('[data-testid="card-deps-unmet-cue"]')).toHaveCount(0)
  })

  test('dr-pending card shows decision primary signal without duplicate cue text', async ({ page }) => {
    await loadBoard(page, PENDING_DR_FOR_TASK_5)
    // Shell.tsx builds pendingDRIds = new Set([5]) from decisions/pending items[].task_id.
    const card = page.locator('[data-testid="task-card"][data-id="5"]')
    await card.waitFor({ state: 'visible', timeout: 6_000 })
    await expect(card.locator('[data-testid="card-signal"]')).toContainText('Decision', { timeout: 2_000 })
    await expect(card.locator('[data-testid="card-dr-pending-cue"]')).toHaveCount(0)
  })

  test('dr-pending card hides duplicate active-decision tag while preserving normal tags', async ({ page }) => {
    await loadBoard(page, PENDING_DR_FOR_TASK_5)
    const card = page.locator('[data-testid="task-card"][data-id="5"]')
    await card.waitFor({ state: 'visible', timeout: 6_000 })
    const tags = card.locator('[data-testid="card-tags"]')
    await expect(tags).toBeVisible({ timeout: 2_000 })
    await expect(tags).not.toContainText('active-decision')
    await expect(tags).toContainText('frontend')
  })

  // AC-1 retry gap-fill (#1570): title element visible + correct text in browser
  test('card title element is browser-visible with correct text content', async ({ page }) => {
    await loadBoard(page)
    // Reviewer Finding #1: unit proof existed but no E2E assertion confirmed title
    // visible under the denser metadata layout. This test closes that gap.
    const card = page.locator('[data-testid="task-card"][data-id="1"]')
    await card.waitFor({ state: 'visible', timeout: 6_000 })
    const title = card.locator('[data-testid="card-title"]')
    await expect(title).toBeVisible({ timeout: 2_000 })
    const text = await title.textContent()
    expect(text?.trim()).toBe('Ready task')
  })

  // AC-2 retry gap-fill (#1570): tag preview text contains actual tag names
  test('card tag preview element shows actual tag names in text content', async ({ page }) => {
    await loadBoard(page)
    // TASK_MANY_TAGS (id=6): tags=['frontend','backend','phase-2','scope:cockpit','type:test']
    // TAG_PREVIEW_LIMIT=3 → previewTags = first 3 → card-tags text = "frontend, backend, phase-2"
    // Reviewer Finding #2: tests proved card-tags visible but never asserted preview text.
    const card = page.locator('[data-testid="task-card"][data-id="6"]')
    await card.waitFor({ state: 'visible', timeout: 6_000 })
    const tagsEl = card.locator('[data-testid="card-tags"]')
    await expect(tagsEl).toBeVisible({ timeout: 2_000 })
    const text = await tagsEl.textContent() ?? ''
    expect(text).toContain('frontend')
    expect(text).toContain('backend')
    expect(text).toContain('phase-2')
  })
})

// --- AC-2 | Accessibility — state cues perceivable without rail color --------

test.describe('AC-2 | Accessibility — blocked, claimed, deps-unmet, dr-pending without color', () => {
  test('blocked card has accessible state text not relying on rail color alone', async ({ page }) => {
    await loadBoard(page)
    const card = page.locator('[data-testid="task-card"][data-id="2"]')
    await card.waitFor({ state: 'visible', timeout: 6_000 })
    const signal = card.locator('[data-testid="card-signal"]')
    await expect(signal).toBeVisible({ timeout: 2_000 })
    const text = await signal.textContent()
    expect(text?.toLowerCase()).toContain('blocked')
  })

  test('claimed card has accessible state text not relying on rail color alone', async ({ page }) => {
    await loadBoard(page)
    const card = page.locator('[data-testid="task-card"][data-id="3"]')
    await card.waitFor({ state: 'visible', timeout: 6_000 })
    const signal = card.locator('[data-testid="card-signal"]')
    await expect(signal).toBeVisible({ timeout: 2_000 })
    const text = await signal.textContent()
    expect(text?.toLowerCase()).toContain('claimed')
  })

  test('deps-unmet card has accessible state text not relying on rail color alone', async ({ page }) => {
    await loadBoard(page)
    const card = page.locator('[data-testid="task-card"][data-id="4"]')
    await card.waitFor({ state: 'visible', timeout: 6_000 })
    const signal = card.locator('[data-testid="card-signal"]')
    await expect(signal).toBeVisible({ timeout: 2_000 })
    const text = await signal.textContent()
    expect(text?.toLowerCase()).toMatch(/deps|depend/)
  })

  test('dr-pending card has accessible state text not relying on rail color alone', async ({ page }) => {
    await loadBoard(page, PENDING_DR_FOR_TASK_5)
    const card = page.locator('[data-testid="task-card"][data-id="5"]')
    await card.waitFor({ state: 'visible', timeout: 6_000 })
    const signal = card.locator('[data-testid="card-signal"]')
    await expect(signal).toBeVisible({ timeout: 2_000 })
    const text = await signal.textContent()
    expect(text?.toLowerCase()).toMatch(/decision/)
  })
})

// --- AC-3 | Regression guards — cards expose scan-critical metadata ----------

test.describe('AC-3 | Regression guards — card metadata remains visible', () => {
  test('card exposes task id beyond the root data attribute', async ({ page }) => {
    await loadBoard(page)
    const card = page.locator('[data-testid="task-card"][data-id="1"]')
    await card.waitFor({ state: 'visible', timeout: 6_000 })
    await expect(card.locator('[data-testid="card-id"]')).toBeVisible({ timeout: 2_000 })
  })

  test('card exposes priority via data and accessible text without chip noise', async ({ page }) => {
    await loadBoard(page)
    const card = page.locator('[data-testid="task-card"][data-id="1"]')
    await card.waitFor({ state: 'visible', timeout: 6_000 })
    await expect(card.locator('[data-testid="card-priority"]')).toHaveCount(0)
    await expect(card).toHaveAttribute('data-priority', 'critical')
    await expect(card).toHaveAttribute('aria-label', /critical priority/)
  })
})

// --- AC-4 | Update recency metadata via updated field ------------------------

test.describe('AC-4 | Update recency metadata using updated field from TaskSummary', () => {
  test('card shows update recency element derived from updated timestamp', async ({ page }) => {
    await loadBoard(page)
    const card = page.locator('[data-testid="task-card"][data-id="1"]')
    await card.waitFor({ state: 'visible', timeout: 6_000 })
    await expect(card.locator('[data-testid="card-updated"]')).toBeVisible({ timeout: 2_000 })
  })

  test('update recency element contains non-empty accessible text (not color-only)', async ({ page }) => {
    await loadBoard(page)
    const card = page.locator('[data-testid="task-card"][data-id="1"]')
    await card.waitFor({ state: 'visible', timeout: 6_000 })
    const updatedEl = card.locator('[data-testid="card-updated"]')
    await expect(updatedEl).toBeVisible({ timeout: 2_000 })
    const text = await updatedEl.textContent()
    expect(text?.trim().length).toBeGreaterThan(0)
  })

  test('stale card shows update recency for old updated timestamp', async ({ page }) => {
    await loadBoard(page)
    const card = page.locator('[data-testid="task-card"][data-id="7"]')
    await card.waitFor({ state: 'visible', timeout: 6_000 })
    await expect(card.locator('[data-testid="card-updated"]')).toBeVisible({ timeout: 2_000 })
  })

  test('update recency shows relative age text not raw ISO timestamp string', async ({ page }) => {
    await loadBoard(page)
    const card = page.locator('[data-testid="task-card"][data-id="1"]')
    await card.waitFor({ state: 'visible', timeout: 6_000 })
    const updatedEl = card.locator('[data-testid="card-updated"]')
    await expect(updatedEl).toBeVisible({ timeout: 2_000 })
    const text = await updatedEl.textContent() ?? ''
    // Should NOT be a raw ISO string: YYYY-MM-DDTHH:MM:SS
    expect(text).not.toMatch(/\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/)
  })
})
