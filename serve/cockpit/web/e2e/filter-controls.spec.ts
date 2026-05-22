/**
 * Playwright coverage for filter panel and task-editor PDS compliance.
 *
 * Covers PDS search/filter controls, PSelect option structure, filter toggle
 * behavior, task editor field controls, and tag chip rendering.
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
  // AC-1: filter-panel opening must use PDS-host-scoped selector (Cycle 8 fix).
  // Generic [data-testid="filter-toggle"] click is not acceptable because a native button
  // reusing the same test-id would drive the workflow green without proving PDS identity.
  await page.click('p-button[data-testid="filter-toggle"]')
  await page.locator('#filter-panel').waitFor({ state: 'visible', timeout: 4_000 })
}

async function openTaskEditor(page: Page): Promise<void> {
  await page.click('[data-testid="task-card"][data-id="2"]')
  await page.locator('[data-testid="edit-details-button"]').waitFor({ state: 'visible', timeout: 6_000 })
  await page.click('[data-testid="edit-details-button"]')
  await page.locator('[data-field="priority"]').waitFor({ state: 'visible', timeout: 6_000 })
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

  test('blocked toggle activates via p-checkbox[name="blocked-filter"]', async ({ page }) => {
    await loadBoard(page)
    await openFilterPanel(page)
    // AC-1 exact contract: must be p-checkbox with name="blocked-filter", not p-switch.
    // Fails if control type drifts to p-switch or name attribute changes.
    const blockedControl = page.locator('#filter-panel p-checkbox[name="blocked-filter"]')
    await expect(blockedControl).toBeVisible({ timeout: 2_000 })
    await blockedControl.click()
  })

  test('active filter badge count increments after applying blocked filter via PDS control', async ({ page }) => {
    await loadBoard(page)
    await openFilterPanel(page)
    // AC-1 exact contract: click p-checkbox[name="blocked-filter"]; fails if name/type drifts.
    await page.locator('#filter-panel p-checkbox[name="blocked-filter"]').click()
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
    // PDS-host-scoped selector required: generic [data-testid="filter-reset"] would pass green
    // against a native button reusing the same test-id.
    await page.click('p-button[data-testid="filter-reset"]')
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
    // AC-1 exact contract: click p-checkbox[name="blocked-filter"]; fails if name/type drifts.
    await loadBoard(page)
    await openFilterPanel(page)
    await page.locator('#filter-panel p-checkbox[name="blocked-filter"]').click()
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
    // PDS-host-scoped selector required: generic [data-testid="filter-reset"] would pass green
    // against a native button reusing the same test-id.
    await page.click('p-button[data-testid="filter-reset"]')
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

  test('(b) blocked toggle renders p-checkbox[name="blocked-filter"], not p-switch or native checkbox', async ({ page }) => {
    // AC-1 exact contract: must be p-checkbox with name="blocked-filter".
    // Fails if control type changes to p-switch or name attribute drifts.
    await expect(
      page.locator('#filter-panel p-checkbox[name="blocked-filter"]'),
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

  test('(d.1) filter trigger: p-button[data-testid="filter-toggle"] is visible', async ({ page }) => {
    // AC-2(d) dual-assertion — positive half.
    // §5 "Primary/secondary command" row: required PButton (p-button).
    // Currently: native <button data-testid="filter-toggle"> -- p-button absent -- FAILS.
    await expect(page.locator('p-button[data-testid="filter-toggle"]')).toBeVisible({ timeout: 2_000 })
  })

  test('(d.2) filter trigger: no native button[data-testid="filter-toggle"] survives (dual-render falsifiability)', async ({ page }) => {
    // AC-2(d) dual-assertion — negative half.
    // A positive-only check on p-button cannot falsify a surviving native button sharing the same
    // test-id. This assertion closes that gap, matching the dual-render guards for search/blocked
    // controls (filter-controls.spec.ts:392-405).
    // KanbanBoard.tsx L269-281: toggle renders <PButton data-testid="filter-toggle"> only.
    // Fails if builder introduces a parallel native <button data-testid="filter-toggle">.
    await expect(page.locator('button[data-testid="filter-toggle"]')).toHaveCount(0)
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
    // Uses not.toHaveCount(0): the editable control has multiple p-select-option children;
    // toBeAttached fails in strict mode when more than one element matches the locator.
    await expect(
      page.locator('p-select[name="priority"] p-select-option'),
    ).not.toHaveCount(0, { timeout: 4_000 })
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

  test('(a.4) editable priority p-select is visible — not a hidden shim', async ({ page }) => {
    // Reviewer finding #1: the prior proof was satisfied by a hidden p-select[name="priority"]
    // shim; the visible editable control used name="priority-editor" instead.
    // Contract: name="priority" must be on the visible editable control, not a hidden element.
    // Fails until builder removes the hidden shim and assigns name="priority" to the editor.
    await expect(page.locator('p-select[name="priority"]')).toBeVisible({ timeout: 4_000 })
  })

  test('(b.1) editable tag chips render as p-tag-dismissible[data-testid="tag-chip"] elements', async ({ page }) => {
    // Editable task tags must use dismissible PDS chips so users can remove them.
    // TASK_BETA has tags ["frontend", "backend"] so chip elements will render.
    // Uses .first() to avoid strict-mode failure when both chips are dismissible hosts.
    await expect(page.locator('p-tag-dismissible[data-testid="tag-chip"]').first()).toBeVisible({ timeout: 2_000 })
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

  test('(b.3) all editable task tag chips are dismissible PDS hosts — no div wrappers', async ({ page }) => {
    // Reviewer finding #2: first chip was PDS but chips at index > 0 used div[data-testid="tag-chip"]
    // wrapping an inner PDS chip, so only the first chip registered as the expected host.
    // Contract: every editable chip host must be a direct p-tag-dismissible element.
    // Uses count equality to avoid strict-mode issues with multiple matching elements.
    const total = await page.locator('[data-testid="tag-chip"]').count()
    const dismissiblePdsTags = await page.locator('p-tag-dismissible[data-testid="tag-chip"]').count()
    expect(total).toBeGreaterThan(0)
    expect(dismissiblePdsTags).toBe(total)
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

  test('[presence] edit toggle: p-button[data-testid="body-edit-toggle"] is in the DOM', async ({ page }) => {
    // AC-4 action-button clause: already-compliant action buttons require individual presence
    // assertions. A native button with data-testid="body-edit-toggle" would pass green without
    // this PDS-host-scoped assertion. Matching the save-button pattern established above.
    // TaskFieldsEditor.tsx L238-239: renders <PButton data-testid="body-edit-toggle">.
    await expect(page.locator('p-button[data-testid="body-edit-toggle"]')).toBeAttached({ timeout: 4_000 })
  })
})
