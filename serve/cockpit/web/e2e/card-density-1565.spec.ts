/**
 * E2E tests for task card information density — #1565
 * P2-10 RED: Specify task card information density
 *
 * Proof bundle: behavioral
 *
 * ═══════════════════════════════════════════════════════════════════════
 * AC-3: TEST EVIDENCE — Current Card Information Density Violations (pre-remediation)
 * ═══════════════════════════════════════════════════════════════════════
 *
 * Audit finding: Task cards are title-only. All metadata (id, priority, tags,
 * state cues, update recency) is absent from the rendered card UI.
 * Source: .owlbear/research/cockpit-visual-audit-consolidated-2026-05-14.md §6, §8
 * Policy reference: .owlbear/research/1560-cockpit-design-policy.md
 *
 * Violations in Card.tsx (confirmed pre-remediation baseline):
 *
 *   Card.tsx L74–80 -- <span data-testid="card-title">{task.title}</span>
 *                      Only rendered field. All other task fields are absent.
 *
 *   Card.tsx L56    -- data-signal={signal}
 *                      computeSignal.ts emits dr-pending | blocked | claimed |
 *                      deps-unmet | ready, distinguished by CSS rail color only.
 *                      No text, icon, or ARIA annotation communicates state.
 *
 *   Card.tsx        -- NO data-testid="card-id"           (task id absent)
 *   Card.tsx        -- NO data-testid="card-priority"     (priority tag absent)
 *   Card.tsx        -- NO data-testid="card-tags"         (tag preview absent)
 *   Card.tsx        -- NO data-testid="card-tag-overflow" (overflow indicator absent)
 *   Card.tsx        -- NO data-testid="card-blocked-cue"  (blocked cue absent)
 *   Card.tsx        -- NO data-testid="card-claimed-cue"  (claimed cue absent)
 *   Card.tsx        -- NO data-testid="card-deps-unmet-cue" (deps-unmet cue absent)
 *   Card.tsx        -- NO data-testid="card-dr-pending-cue" (dr-pending cue absent)
 *   Card.tsx        -- NO data-testid="card-updated"      (update recency absent)
 *
 * Baseline confirmed: Card.tsx renders task.title and nothing else.
 * computeSignal.ts computes 5 states (dr-pending, blocked, claimed, deps-unmet,
 * ready) but Card.tsx does not surface any cue element for any state.
 * ═══════════════════════════════════════════════════════════════════════
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
  tags: [],
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

test.describe('AC-1 | Card rendering fixtures — id, priority, tags, state cues', () => {
  test('card displays task id as a visible element', async ({ page }) => {
    await loadBoard(page)
    // Post-remediation: visible task-id element on card.
    // Currently: task id only in data-id attribute on root div — no visible element — FAILS.
    const card = page.locator('[data-testid="task-card"][data-id="1"]')
    await card.waitFor({ state: 'visible', timeout: 6_000 })
    await expect(card.locator('[data-testid="card-id"]')).toBeVisible({ timeout: 2_000 })
  })

  test('card displays priority tag as a visible element', async ({ page }) => {
    await loadBoard(page)
    // Post-remediation: visible priority chip/tag element on each card.
    // Currently: priority only in data-priority attribute — no visible tag — FAILS.
    const card = page.locator('[data-testid="task-card"][data-id="1"]')
    await card.waitFor({ state: 'visible', timeout: 6_000 })
    await expect(card.locator('[data-testid="card-priority"]')).toBeVisible({ timeout: 2_000 })
  })

  test('card with tags displays tag preview', async ({ page }) => {
    await loadBoard(page)
    // Post-remediation: tag preview element rendered for tasks with non-empty tags.
    // Currently: no tag preview on card — FAILS.
    const card = page.locator('[data-testid="task-card"][data-id="1"]')
    await card.waitFor({ state: 'visible', timeout: 6_000 })
    await expect(card.locator('[data-testid="card-tags"]')).toBeVisible({ timeout: 2_000 })
  })

  test('card with five tags shows overflow indicator', async ({ page }) => {
    await loadBoard(page)
    // Task 6 has 5 tags — exceeds any reasonable preview slot limit.
    // Post-remediation: overflow indicator visible when tags exceed preview limit.
    // Currently: no tag preview or overflow element — FAILS.
    const card = page.locator('[data-testid="task-card"][data-id="6"]')
    await card.waitFor({ state: 'visible', timeout: 6_000 })
    await expect(card.locator('[data-testid="card-tag-overflow"]')).toBeVisible({ timeout: 2_000 })
  })

  test('blocked card shows blocked cue element', async ({ page }) => {
    await loadBoard(page)
    // Post-remediation: visible blocked cue (text label or icon) on card with blocked=true.
    // Currently: blocked state only in data-signal="blocked" — no cue element — FAILS.
    const card = page.locator('[data-testid="task-card"][data-id="2"]')
    await card.waitFor({ state: 'visible', timeout: 6_000 })
    await expect(card.locator('[data-testid="card-blocked-cue"]')).toBeVisible({ timeout: 2_000 })
  })

  test('claimed card shows claimed cue element', async ({ page }) => {
    await loadBoard(page)
    // Post-remediation: visible claimed cue on card with claimed=true.
    // Currently: claimed state only in data-signal="claimed" — no cue element — FAILS.
    const card = page.locator('[data-testid="task-card"][data-id="3"]')
    await card.waitFor({ state: 'visible', timeout: 6_000 })
    await expect(card.locator('[data-testid="card-claimed-cue"]')).toBeVisible({ timeout: 2_000 })
  })

  test('deps-unmet card shows deps-unmet cue element', async ({ page }) => {
    await loadBoard(page)
    // Post-remediation: visible deps-unmet cue on card with dep_status='blocked'.
    // Currently: deps-unmet only in data-signal="deps-unmet" — no cue element — FAILS.
    const card = page.locator('[data-testid="task-card"][data-id="4"]')
    await card.waitFor({ state: 'visible', timeout: 6_000 })
    await expect(card.locator('[data-testid="card-deps-unmet-cue"]')).toBeVisible({ timeout: 2_000 })
  })

  test('dr-pending card shows dr-pending cue element', async ({ page }) => {
    await loadBoard(page, PENDING_DR_FOR_TASK_5)
    // Shell.tsx builds pendingDRIds = new Set([5]) from decisions/pending items[].task_id.
    // Post-remediation: visible dr-pending cue on card when task has a pending DR.
    // Currently: dr-pending only in data-signal="dr-pending" — no cue element — FAILS.
    const card = page.locator('[data-testid="task-card"][data-id="5"]')
    await card.waitFor({ state: 'visible', timeout: 6_000 })
    await expect(card.locator('[data-testid="card-dr-pending-cue"]')).toBeVisible({ timeout: 2_000 })
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
    // Post-remediation: blocked cue element contains text with "blocked" for AT users.
    // Currently: no cue element exists — FAILS at visibility check.
    const card = page.locator('[data-testid="task-card"][data-id="2"]')
    await card.waitFor({ state: 'visible', timeout: 6_000 })
    const cue = card.locator('[data-testid="card-blocked-cue"]')
    await expect(cue).toBeVisible({ timeout: 2_000 })
    const text = await cue.textContent()
    expect(text?.toLowerCase()).toContain('blocked')
  })

  test('claimed card has accessible state text not relying on rail color alone', async ({ page }) => {
    await loadBoard(page)
    // Post-remediation: claimed cue element contains text with "claimed" for AT users.
    // Currently: no cue element exists — FAILS at visibility check.
    const card = page.locator('[data-testid="task-card"][data-id="3"]')
    await card.waitFor({ state: 'visible', timeout: 6_000 })
    const cue = card.locator('[data-testid="card-claimed-cue"]')
    await expect(cue).toBeVisible({ timeout: 2_000 })
    const text = await cue.textContent()
    expect(text?.toLowerCase()).toContain('claimed')
  })

  test('deps-unmet card has accessible state text not relying on rail color alone', async ({ page }) => {
    await loadBoard(page)
    // Post-remediation: deps-unmet cue element contains text conveying dependency state.
    // Currently: no cue element exists — FAILS at visibility check.
    const card = page.locator('[data-testid="task-card"][data-id="4"]')
    await card.waitFor({ state: 'visible', timeout: 6_000 })
    const cue = card.locator('[data-testid="card-deps-unmet-cue"]')
    await expect(cue).toBeVisible({ timeout: 2_000 })
    const text = await cue.textContent()
    expect(text?.toLowerCase()).toMatch(/deps|blocked|depend/)
  })

  test('dr-pending card has accessible state text not relying on rail color alone', async ({ page }) => {
    await loadBoard(page, PENDING_DR_FOR_TASK_5)
    // Post-remediation: dr-pending cue element contains text about pending decision.
    // Currently: no cue element exists — FAILS at visibility check.
    const card = page.locator('[data-testid="task-card"][data-id="5"]')
    await card.waitFor({ state: 'visible', timeout: 6_000 })
    const cue = card.locator('[data-testid="card-dr-pending-cue"]')
    await expect(cue).toBeVisible({ timeout: 2_000 })
    const text = await cue.textContent()
    expect(text?.toLowerCase()).toMatch(/decision|dr|pending/)
  })
})

// --- AC-3 | Baseline failing evidence — cards currently title-only -----------

test.describe('AC-3 | Baseline failing evidence — pre-remediation title-only baseline', () => {
  // The violation catalogue above (═══ block) is the primary AC-3 artifact.
  // These tests assert the post-remediation contract and fail against the current
  // title-only Card.tsx, establishing machine-readable failing baseline evidence.

  test('baseline: card exposes task id beyond data attribute (proves title-only gap)', async ({ page }) => {
    await loadBoard(page)
    // Card.tsx renders only <span data-testid="card-title">. data-id="1" is on the
    // root div but no visible id element exists — FAILS, confirming title-only state.
    const card = page.locator('[data-testid="task-card"][data-id="1"]')
    await card.waitFor({ state: 'visible', timeout: 6_000 })
    await expect(card.locator('[data-testid="card-id"]')).toBeVisible({ timeout: 2_000 })
  })

  test('baseline: card exposes priority beyond data attribute (proves title-only gap)', async ({ page }) => {
    await loadBoard(page)
    // Card.tsx sets data-priority="critical" on root div but renders no priority chip.
    // FAILS, confirming priority is CSS/color-only, not visible text.
    const card = page.locator('[data-testid="task-card"][data-id="1"]')
    await card.waitFor({ state: 'visible', timeout: 6_000 })
    await expect(card.locator('[data-testid="card-priority"]')).toBeVisible({ timeout: 2_000 })
  })
})

// --- AC-4 | Update recency metadata via updated field ------------------------

test.describe('AC-4 | Update recency metadata using updated field from TaskSummary', () => {
  test('card shows update recency element derived from updated timestamp', async ({ page }) => {
    await loadBoard(page)
    // TaskSummary.updated is available on /api/tasks (not created — list-endpoint-only).
    // Post-remediation: card renders [data-testid="card-updated"] with age text.
    // Currently: updated field not rendered on card — FAILS.
    const card = page.locator('[data-testid="task-card"][data-id="1"]')
    await card.waitFor({ state: 'visible', timeout: 6_000 })
    await expect(card.locator('[data-testid="card-updated"]')).toBeVisible({ timeout: 2_000 })
  })

  test('update recency element contains non-empty accessible text (not color-only)', async ({ page }) => {
    await loadBoard(page)
    // Post-remediation: recency element has visible text — not rendered via color alone.
    // Currently: element absent — FAILS at visibility check.
    const card = page.locator('[data-testid="task-card"][data-id="1"]')
    await card.waitFor({ state: 'visible', timeout: 6_000 })
    const updatedEl = card.locator('[data-testid="card-updated"]')
    await expect(updatedEl).toBeVisible({ timeout: 2_000 })
    const text = await updatedEl.textContent()
    expect(text?.trim().length).toBeGreaterThan(0)
  })

  test('stale card shows update recency for old updated timestamp', async ({ page }) => {
    await loadBoard(page)
    // Task 7: updated='2026-01-01T00:00:00+00:00' — months before test date (2026-05-14).
    // Post-remediation: stale card renders recency indication.
    // Currently: no recency element rendered — FAILS.
    const card = page.locator('[data-testid="task-card"][data-id="7"]')
    await card.waitFor({ state: 'visible', timeout: 6_000 })
    await expect(card.locator('[data-testid="card-updated"]')).toBeVisible({ timeout: 2_000 })
  })

  test('update recency shows relative age text not raw ISO timestamp string', async ({ page }) => {
    await loadBoard(page)
    // Post-remediation: human-readable age (e.g., "2h", "3d", "just now") not raw ISO.
    // Currently: element absent — FAILS at visibility check.
    const card = page.locator('[data-testid="task-card"][data-id="1"]')
    await card.waitFor({ state: 'visible', timeout: 6_000 })
    const updatedEl = card.locator('[data-testid="card-updated"]')
    await expect(updatedEl).toBeVisible({ timeout: 2_000 })
    const text = await updatedEl.textContent() ?? ''
    // Should NOT be a raw ISO string: YYYY-MM-DDTHH:MM:SS
    expect(text).not.toMatch(/\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/)
  })
})
