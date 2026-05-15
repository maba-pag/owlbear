/**
 * E2E tests for filter panel and task-editor PDS compliance — #1564
 * P2-08 RED: Specify filter and form control behavior
 *
 * Proof bundle: behavioral
 *
 * ═══════════════════════════════════════════════════════════════════════
 * AC-3: TEST EVIDENCE — Current PDS §5 Violations (pre-remediation)
 * ═══════════════════════════════════════════════════════════════════════
 *
 * Audit P1 finding: Filter controls use bolted-on native HTML, not PDS
 * components. Source: .owlbear/research/cockpit-visual-audit-consolidated-2026-05-14.md
 *
 * Policy reference: .owlbear/research/1560-cockpit-design-policy.md §5
 *
 * Violations:
 *   FilterPanel.tsx L152     -- <input type="text" aria-label="Search tasks">
 *                              §5 "Search" requires: p-input-search
 *
 *   FilterPanel.tsx L195     -- <input type="checkbox" role="switch">
 *                              §5 "Binary filter/setting" requires: p-switch or p-checkbox
 *
 *   FilterPanel.tsx L166-170 -- <PSelect name="priority-filter"> children are native <option>
 *                              §5 "Select/dropdown": native options inside PDS selects
 *                              are not accepted -- requires: p-select-option children
 *
 *   KanbanBoard.tsx L268-276 -- native <button data-testid="filter-toggle" tabIndex={-1}>
 *                              §5 "Primary/secondary command" requires: PButton (p-button)
 *
 *   TaskFieldsEditor.tsx L182-195 -- <PSelect name="priority"> children are native <option>
 *                                   §5 "Select/dropdown" requires: p-select-option children
 *
 *   TaskFieldsEditor.tsx L197 -- <span data-testid="tag-chip">{tag}</span>
 *                               §5 "Metadata/status chip" requires: p-tag
 *
 * Documented exception -- no remediation required:
 *   FilterPanel.tsx L177-187 -- PMultiSelect with PMultiSelectOption children are
 *                              PDS-compliant (tags filter). Presence assertion included.
 *
 * Already-compliant controls in TaskFieldsEditor.tsx (presence assertions only):
 *   title       via PInputText -> p-input-text
 *   body        via PTextarea  -> p-textarea
 *   depends_on  via PInputText -> p-input-text
 *   parent      via PInputText -> p-input-text
 *   save/edit   via PButton    -> p-button
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

const TASK_ALPHA = {
  id: 1,
  title: 'Alpha task',
  status: 'todo',
  priority: 'critical',
  tags: ['frontend'],
  blocked: false,
  block_reason: null,
  claimed: false,
  updated: '2026-05-14T00:00:00+00:00',
}

const TASK_BETA = {
  id: 2,
  title: 'Beta blocked task',
  status: 'backlog',
  priority: 'needed',
  tags: ['frontend', 'backend'],
  blocked: true,
  block_reason: 'Waiting on upstream',
  claimed: false,
  updated: '2026-05-14T00:00:00+00:00',
}

const TASK_GAMMA = {
  id: 3,
  title: 'Gamma task',
  status: 'todo',
  priority: 'someday',
  tags: [],
  blocked: false,
  block_reason: null,
  claimed: false,
  updated: '2026-05-14T00:00:00+00:00',
}

const TASK_BETA_DETAIL = {
  ...TASK_BETA,
  body: 'Beta task body',
  depends_on: [1],
  parent: null,
  created: '2026-05-14T00:00:00+00:00',
  claimed_at: null,
  dep_status: null,
}

const ALL_TASKS = [TASK_ALPHA, TASK_BETA, TASK_GAMMA]

// --- API stub ----------------------------------------------------------------

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
    route.fulfill({ json: { tasks: ALL_TASKS, mtime: 1_715_644_800 } }),
  )
  await page.route('/api/sessions', (route) => route.fulfill({ json: { sessions: [] } }))
  await page.route('/api/decisions/pending', (route) =>
    route.fulfill({ json: { count: 0, items: [] } }),
  )
  await page.route('/api/tasks/scan', (route) => route.fulfill({ json: [] }))

  // Generic registered before specific -- specific wins via LIFO.
  await page.route(/\/api\/tasks\/\d+$/, (route) => route.fulfill({ json: TASK_ALPHA }))
  await page.route(/\/api\/tasks\/2$/, (route) => route.fulfill({ json: TASK_BETA_DETAIL }))
}

// --- Helpers -----------------------------------------------------------------

async function loadBoard(page: Page): Promise<void> {
  await stubApis(page)
  await page.goto('/')
  await page.locator('[data-region="workspace"]').waitFor({ state: 'visible', timeout: 8_000 })
}

async function openFilterPanel(page: Page): Promise<void> {
  await page.click('[data-testid="filter-toggle"]')
  await page.locator('#filter-panel').waitFor({ state: 'visible', timeout: 4_000 })
}

async function openTaskEditor(page: Page): Promise<void> {
  await page.click('[data-testid="task-card"][data-id="2"]')
  await page.locator('[data-field="priority"]').waitFor({ state: 'attached', timeout: 6_000 })
}

// --- AC-1 | Filter workflow via PDS control selectors -----------------------

test.describe('AC-1 | Filter workflow via PDS control selectors', () => {
  test('filter toggle is a PDS button component, not a native button', async ({ page }) => {
    await loadBoard(page)
    // Post-remediation: p-button[data-testid="filter-toggle"].
    // Currently: native <button data-testid="filter-toggle"> -- assertion FAILS.
    await expect(page.locator('p-button[data-testid="filter-toggle"]'))
      .toBeVisible({ timeout: 2_000 })
  })

  test('search field in filter panel is p-input-search', async ({ page }) => {
    await loadBoard(page)
    await openFilterPanel(page)
    // Post-remediation: p-input-search[name="search-filter"] inside the panel.
    // Scoped by name to avoid strict-mode violation when PDS renders an inner host.
    // Currently: native <input type="text"> -- p-input-search absent -- FAILS.
    await expect(page.locator('#filter-panel p-input-search[name="search-filter"]')).toBeVisible({ timeout: 2_000 })
  })

  test('searching via p-input-search narrows visible task cards', async ({ page }) => {
    await loadBoard(page)
    await openFilterPanel(page)
    // Post-remediation: click p-input-search host to focus shadow-DOM input, then type.
    // .fill() is not reliable on PDS web component hosts -- use click + keyboard.type instead.
    // Currently: p-input-search absent OR onInput handler broken -- filter unchanged -- FAILS.
    await page.locator('#filter-panel p-input-search[name="search-filter"]').click()
    await page.keyboard.type('Alpha')
    await expect(page.locator('[data-testid="task-card"][data-id="3"]')).not.toBeVisible()
  })

  test('priority filter selects via p-select-option and narrows results', async ({ page }) => {
    await loadBoard(page)
    await openFilterPanel(page)
    // AC-2(c) already verifies p-select-option presence; no duplicate here.
    // Trigger PDS select via evaluate: dispatch CustomEvent('change', { detail: { value } }).
    // Matches PDS p-select emission contract (readStringValue reads detail.value first).
    // Currently: no onInput handler on p-select -- filter unchanged -- task-card-2 remains visible -- FAILS.
    await page.locator('#filter-panel p-select[name="priority-filter"]').evaluate((el) => {
      el.dispatchEvent(new CustomEvent('change', { detail: { value: 'critical' }, bubbles: true }))
    })
    // After correct implementation: only TASK_ALPHA (priority=critical) visible; TASK_BETA hidden.
    await expect(page.locator('[data-testid="task-card"][data-id="2"]')).not.toBeVisible({ timeout: 2_000 })
  })

  test('blocked toggle activates via p-switch or p-checkbox', async ({ page }) => {
    await loadBoard(page)
    await openFilterPanel(page)
    // Post-remediation: p-switch or p-checkbox for the blocked filter.
    // Currently: native <input type="checkbox" role="switch"> -- FAILS.
    const blockedControl = page.locator('#filter-panel').locator('p-switch, p-checkbox')
    await expect(blockedControl).toBeVisible({ timeout: 2_000 })
    await blockedControl.click()
  })

  test('active filter badge count increments after applying blocked filter via PDS control', async ({ page }) => {
    await loadBoard(page)
    await openFilterPanel(page)
    // Currently: p-switch absent -- click() rejects -- FAILS before badge check.
    await page.locator('#filter-panel').locator('p-switch, p-checkbox').click()
    await expect(page.locator('[data-testid="filter-toggle"]')).toContainText('(1)')
  })

  test('result count displays filtered/total ratio when priority filter applied via PDS control', async ({ page }) => {
    await loadBoard(page)
    await openFilterPanel(page)
    // Trigger priority filter via PDS evaluate contract.
    // Currently: no onInput handler -- filter unchanged -- result count absent -- FAILS.
    await page.locator('#filter-panel p-select[name="priority-filter"]').evaluate((el) => {
      el.dispatchEvent(new CustomEvent('change', { detail: { value: 'critical' }, bubbles: true }))
    })
    await expect(page.locator('[data-testid="filter-result-count"]')).toBeVisible({ timeout: 2_000 })
  })

  test('clearing all filters removes badge count and hides result count', async ({ page }) => {
    await loadBoard(page)
    await openFilterPanel(page)
    // Trigger priority filter via PDS evaluate contract.
    await page.locator('#filter-panel p-select[name="priority-filter"]').evaluate((el) => {
      el.dispatchEvent(new CustomEvent('change', { detail: { value: 'critical' }, bubbles: true }))
    })
    // Guard against vacuous pass: verify filter WAS applied before testing clear.
    // Currently: no onInput handler -- filter unchanged -- count absent -- FAILS here.
    await expect(page.locator('[data-testid="filter-result-count"]')).toBeVisible({ timeout: 2_000 })
    // After correct implementation: clear removes badge and hides result count.
    await page.click('[data-testid="filter-reset"]')
    await expect(page.locator('[data-testid="filter-toggle"]')).not.toContainText('(')
    await expect(page.locator('[data-testid="filter-result-count"]')).not.toBeVisible()
  })

  test('tags filter uses p-multi-select [documented exception: already PDS-compliant]', async ({ page }) => {
    // FilterPanel uses p-multi-select (PDS-compliant). Regression guard at host level.
    // p-multi-select-option children may be slotted into shadow DOM by PDS at runtime;
    // assert the host element p-multi-select[name="tags-filter"] instead of option children.
    await loadBoard(page)
    await openFilterPanel(page)
    await expect(
      page.locator('#filter-panel p-multi-select[name="tags-filter"]'),
    ).toBeAttached({ timeout: 4_000 })
  })

  test('tags behavioral: PDS update event selection narrows visible task cards', async ({ page }) => {
    // AC-1 behavioral requirement: host-presence-only (toBeAttached) is insufficient.
    // Must dispatch PDS 'update' CustomEvent with fixture tag value and assert task visibility narrows.
    // readStringArrayValue in FilterPanel.tsx reads detail.value: string[] from the CustomEvent.
    // Fixture: TASK_ALPHA tags=['frontend'] (id=1), TASK_BETA tags=['frontend','backend'] (id=2), TASK_GAMMA tags=[] (id=3).
    // Selecting 'backend' must hide TASK_ALPHA (id=1) and TASK_GAMMA (id=3); TASK_BETA (id=2) remains visible.
    // Fails until builder correctly wires the update event filter state through to task-card visibility.
    await loadBoard(page)
    await openFilterPanel(page)
    await page.locator('#filter-panel p-multi-select[name="tags-filter"]').evaluate((el) => {
      el.dispatchEvent(new CustomEvent('update', { detail: { value: ['backend'] }, bubbles: true }))
    })
    await expect(page.locator('[data-testid="task-card"][data-id="1"]')).not.toBeVisible({ timeout: 2_000 })
    await expect(page.locator('[data-testid="task-card"][data-id="3"]')).not.toBeVisible({ timeout: 2_000 })
  })

  test('search: task 1 (Alpha) remains visible and task 2 (Beta) also hidden after searching "Alpha"', async ({ page }) => {
    // Surviving-set assertion: existing test only hides task 3. Prove task 1 survives and task 2 is
    // also hidden ("Beta blocked task" does not match "Alpha"). A bug that over-filters all tasks
    // would pass the one-sided check but fail here.
    await loadBoard(page)
    await openFilterPanel(page)
    await page.locator('#filter-panel p-input-search[name="search-filter"]').click()
    await page.keyboard.type('Alpha')
    await expect(page.locator('[data-testid="task-card"][data-id="1"]')).toBeVisible({ timeout: 2_000 })
    await expect(page.locator('[data-testid="task-card"][data-id="2"]')).not.toBeVisible({ timeout: 2_000 })
  })

  test('priority filter: task 1 (critical) remains visible and task 3 (someday) is hidden', async ({ page }) => {
    // Surviving-set assertion: existing test hides only task 2. Prove task 1 survives and task 3
    // (someday) is also hidden. Prevents false-green from partial or over-filtered results.
    await loadBoard(page)
    await openFilterPanel(page)
    await page.locator('#filter-panel p-select[name="priority-filter"]').evaluate((el) => {
      el.dispatchEvent(new CustomEvent('change', { detail: { value: 'critical' }, bubbles: true }))
    })
    await expect(page.locator('[data-testid="task-card"][data-id="1"]')).toBeVisible({ timeout: 2_000 })
    await expect(page.locator('[data-testid="task-card"][data-id="3"]')).not.toBeVisible({ timeout: 2_000 })
  })

  test('blocked filter: task 2 (blocked) remains visible while tasks 1 and 3 are hidden', async ({ page }) => {
    // Full surviving-set: badge test only checks control + count. Prove the correct card set:
    // only task 2 (blocked=true) survives; tasks 1 and 3 (blocked=false) are hidden.
    await loadBoard(page)
    await openFilterPanel(page)
    await page.locator('#filter-panel').locator('p-switch, p-checkbox').click()
    await expect(page.locator('[data-testid="task-card"][data-id="2"]')).toBeVisible({ timeout: 2_000 })
    await expect(page.locator('[data-testid="task-card"][data-id="1"]')).not.toBeVisible({ timeout: 2_000 })
    await expect(page.locator('[data-testid="task-card"][data-id="3"]')).not.toBeVisible({ timeout: 2_000 })
  })

  test('tags filter: task 2 (backend tag) remains visible after tags=backend filter', async ({ page }) => {
    // Surviving-set assertion: existing behavioral test hides tasks 1 and 3 but never asserts
    // task 2 (frontend+backend) remains visible after selecting the backend tag.
    await loadBoard(page)
    await openFilterPanel(page)
    await page.locator('#filter-panel p-multi-select[name="tags-filter"]').evaluate((el) => {
      el.dispatchEvent(new CustomEvent('update', { detail: { value: ['backend'] }, bubbles: true }))
    })
    await expect(page.locator('[data-testid="task-card"][data-id="2"]')).toBeVisible({ timeout: 2_000 })
  })

  test('clearing filters restores previously hidden task cards to visible', async ({ page }) => {
    // Clear test must prove filtered-out cards reappear, not just that badge/count disappear.
    // Apply priority=critical (hides tasks 2 and 3), clear, then assert tasks 2 and 3 reappear.
    await loadBoard(page)
    await openFilterPanel(page)
    await page.locator('#filter-panel p-select[name="priority-filter"]').evaluate((el) => {
      el.dispatchEvent(new CustomEvent('change', { detail: { value: 'critical' }, bubbles: true }))
    })
    // Guard: verify filter was active before testing clear.
    await expect(page.locator('[data-testid="task-card"][data-id="3"]')).not.toBeVisible({ timeout: 2_000 })
    await page.click('[data-testid="filter-reset"]')
    await expect(page.locator('[data-testid="task-card"][data-id="2"]')).toBeVisible({ timeout: 2_000 })
    await expect(page.locator('[data-testid="task-card"][data-id="3"]')).toBeVisible({ timeout: 2_000 })
  })

  test('result count text shows correct ratio value, not just presence', async ({ page }) => {
    // Existing test only asserts toBeVisible. Assert the displayed text is the correct ratio.
    // priority=critical: 1 matching task (task 1) out of 3 total → "1 / 3 tasks".
    await loadBoard(page)
    await openFilterPanel(page)
    await page.locator('#filter-panel p-select[name="priority-filter"]').evaluate((el) => {
      el.dispatchEvent(new CustomEvent('change', { detail: { value: 'critical' }, bubbles: true }))
    })
    await expect(page.locator('[data-testid="filter-result-count"]')).toContainText('1 / 3 tasks', { timeout: 2_000 })
  })
})

// --- AC-2 | FilterPanel PDS compliance assertions ---------------------------

test.describe('AC-2 | FilterPanel PDS compliance assertions', () => {
  test.beforeEach(async ({ page }) => {
    await loadBoard(page)
    await openFilterPanel(page)
  })

  test('(a) search field renders p-input-search, not native text input', async ({ page }) => {
    // §5 "Search" row: required p-input-search.
    // Scoped by name to avoid strict-mode violation from PDS internal host rendering.
    // Currently: native <input type="text"> -- p-input-search absent -- FAILS.
    await expect(page.locator('#filter-panel p-input-search[name="search-filter"]')).toBeVisible({ timeout: 2_000 })
  })

  test('(b) blocked toggle renders p-switch or p-checkbox, not native checkbox', async ({ page }) => {
    // §5 "Binary filter/setting" row: required p-switch or p-checkbox.
    // Currently: <input type="checkbox" role="switch"> -- FAILS.
    await expect(
      page.locator('#filter-panel').locator('p-switch, p-checkbox'),
    ).toBeVisible({ timeout: 2_000 })
  })

  test('(a.2) search field: no native input[type="text"] present in filter panel (dual-render falsifiability)', async ({ page }) => {
    // Absence assertion for AC-2(a): PDS host presence alone is not falsifiable against a
    // dual-render state. FilterPanel.tsx keeps an aria-hidden native input[type="text"] fallback
    // alongside p-input-search. Both must be absent for the contract to hold.
    // FAILS until builder removes the hidden native text input.
    await expect(page.locator('#filter-panel input[type="text"]')).toHaveCount(0, { timeout: 2_000 })
  })

  test('(b.2) blocked toggle: no native input[type="checkbox"] present in filter panel (dual-render falsifiability)', async ({ page }) => {
    // Absence assertion for AC-2(b): PDS host presence alone is not falsifiable against a
    // dual-render state. FilterPanel.tsx keeps an aria-hidden native input[type="checkbox"] fallback
    // alongside p-checkbox. Both must be absent for the contract to hold.
    // FAILS until builder removes the hidden native checkbox fallback.
    await expect(page.locator('#filter-panel input[type="checkbox"]')).toHaveCount(0, { timeout: 2_000 })
  })

  test('(c) priority select uses p-select-option children, not native option', async ({ page }) => {
    // §5 "Select/dropdown" row: native options inside PDS selects are not accepted.
    // Currently: PSelect with <option> children -- p-select-option absent -- FAILS.
    // Uses toBeAttached: options are in DOM but hidden when select is closed.
    await expect(
      page.locator('#filter-panel p-select[name="priority-filter"] p-select-option').first(),
    ).toBeAttached({ timeout: 2_000 })
  })

  test('(c.2) priority-filter p-select contains no native option children (dual-render falsifiability)', async ({ page }) => {
    // AC-2(c) falsifiability guard: CSS `> option` is a confirmed false-green — PDS absorbs
    // light-DOM native <option> children so the CSS child combinator cannot reach them at runtime
    // (FilterPanel.tsx L206-214 has native <option> children but the CSS test passed green).
    // Fix: use page.evaluate() on el.children (raw DOM children collection) to count OPTION nodes
    // directly without going through the CSS selector engine.
    // FilterPanel.tsx L206-214: native <option value=""> + native <option> per priority value.
    // This test FAILS until builder removes all native <option> children from the p-select.
    const nativeOptionCount = await page
      .locator('#filter-panel p-select[name="priority-filter"]')
      .evaluate((el) => Array.from(el.children).filter((c) => c.tagName === 'OPTION').length)
    expect(nativeOptionCount).toBe(0)
  })

  test('(d) filter trigger renders as PDS button, not native button', async ({ page }) => {
    // §5 "Primary/secondary command" row: required PButton (p-button).
    // Currently: native <button data-testid="filter-toggle"> -- FAILS.
    await expect(page.locator('p-button[data-testid="filter-toggle"]')).toBeVisible({ timeout: 2_000 })
  })
})

// --- AC-4 | Task-editor PDS compliance assertions ---------------------------

test.describe('AC-4 | Task-editor PDS compliance assertions', () => {
  test.beforeEach(async ({ page }) => {
    await loadBoard(page)
    await openTaskEditor(page)
  })

  test('(a) priority select uses p-select-option children, not native option', async ({ page }) => {
    // §5 "Select/dropdown" row: native options inside PDS selects are not accepted.
    // Currently: PSelect[name="priority"] with <option> children -- p-select-option absent -- FAILS.
    // Uses toBeAttached: options are in DOM but hidden when select is closed.
    await expect(
      page.locator('p-select[name="priority"] p-select-option'),
    ).toBeAttached({ timeout: 4_000 })
  })

  test('(a.2) task-editor priority p-select contains no native option children (dual-render falsifiability)', async ({ page }) => {
    // AC-4(a) falsifiability guard: CSS `> option` is a confirmed false-green — PDS absorbs
    // light-DOM native <option> children so the CSS child combinator cannot reach them at runtime.
    // Fix: use page.evaluate() on el.children (raw DOM children collection) to count OPTION nodes
    // directly without going through the CSS selector engine — same mechanism as AC-2(c.2).
    // TaskFieldsEditor.tsx L182-192: only p-select-option present, no native <option> — regression guard.
    // Fails if builder accidentally introduces native <option> children during GREEN phase.
    const nativeOptionCount = await page
      .locator('p-select[name="priority"]')
      .evaluate((el) => Array.from(el.children).filter((c) => c.tagName === 'OPTION').length)
    expect(nativeOptionCount).toBe(0)
  })

  test('(b.1) tag chips render as p-tag[data-testid="tag-chip"] elements', async ({ page }) => {
    // §5 "Metadata/status chip" row: required p-tag.
    // RED-phase evidence (spec line 32): legacy chip was <span data-testid="tag-chip">{tag}</span>.
    // Currently: <span data-testid="tag-chip"> for each tag -- p-tag absent -- FAILS.
    // TASK_BETA has tags ["frontend", "backend"] so chip elements will render.
    await expect(page.locator('p-tag[data-testid="tag-chip"]')).toBeVisible({ timeout: 2_000 })
  })

  test('(b.2) no legacy span[data-testid="tag-chip"] chips survive (dual-render falsifiability)', async ({ page }) => {
    // AC-4(b) falsifiability guard: a visibility-only assertion on p-tag is insufficient because
    // a dual-render state (both p-tag and a surviving legacy <span data-testid="tag-chip">) would
    // pass green. This test proves no plain span chip exists alongside any p-tag.
    // Legacy chip identity documented at spec line 32: <span data-testid="tag-chip">{tag}</span>.
    // TaskFieldsEditor.tsx L192: impl renders <p-tag data-testid="tag-chip"> with no legacy spans.
    // Fails if builder accidentally introduces or re-introduces plain span chips.
    await expect(page.locator('span[data-testid="tag-chip"]')).toHaveCount(0)
  })

  test('[presence] title field: p-input-text[name="title"] is in the DOM', async ({ page }) => {
    // Already PDS-compliant -- regression guard. Passes against current implementation.
    await expect(page.locator('p-input-text[name="title"]')).toBeAttached({ timeout: 4_000 })
  })

  test('[presence] body field: p-textarea[name="body"] is in the DOM after Edit', async ({ page }) => {
    // Already PDS-compliant -- regression guard. Passes against current implementation.
    await page.click('[data-testid="body-edit-toggle"]')
    await expect(page.locator('p-textarea[name="body"]')).toBeAttached({ timeout: 4_000 })
  })

  test('[presence] depends_on field: p-input-text[name="depends_on"] is in the DOM', async ({ page }) => {
    // Already PDS-compliant -- regression guard. Passes against current implementation.
    await expect(page.locator('p-input-text[name="depends_on"]')).toBeAttached({ timeout: 4_000 })
  })

  test('[presence] parent field: p-input-text[name="parent"] is in the DOM', async ({ page }) => {
    // Already PDS-compliant -- regression guard. Passes against current implementation.
    await expect(page.locator('p-input-text[name="parent"]')).toBeAttached({ timeout: 4_000 })
  })

  test('[presence] save button: p-button[data-testid="save-button"] is in the DOM', async ({ page }) => {
    // Already PDS-compliant -- regression guard. Passes against current implementation.
    await expect(page.locator('p-button[data-testid="save-button"]')).toBeAttached({ timeout: 4_000 })
  })
})
