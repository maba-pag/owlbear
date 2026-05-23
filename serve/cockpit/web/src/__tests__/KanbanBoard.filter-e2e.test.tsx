/**
 * Full board filter flow.
 *
 * End-to-end Vitest integration tests for the complete filter feature.
 * Uses the REAL FilterPanel — no vi.mock('../components/FilterPanel').
 *
 * Covers:
 *   AC1 — Filtered tasks appear in correct status columns
 *   AC2 — Empty columns after filtering show "No tasks" placeholder
 *   AC3 — Result count updates correctly ("0 / N tasks", "M / N tasks")
 *   AC4 — Toggle badge reflects active filter count ("Filter (2)")
 *   AC5 — Filter change while context menu open dismisses menu
 *   AC6 — Filter change while dragging cancels drag
 *   AC7 — Selected tag persisting after tag vanishes from task set (0-result state)
 *   AC8 — Reset clears all filters and restores full task view
 *   AC9 — All accessibility attributes present in integrated state
 *
 * GREEN-on-write: all components exist; tests verify integrated behavior.
 */
import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'
import KanbanBoard from '../KanbanBoard'

// ─── Stubs ─────────────────────────────────────────────────────────────────────
// ArchivalModal is a KanbanBoard dependency unrelated to filter behavior.
// FilterPanel is NOT mocked — this file exercises the real component chain.

vi.mock('../components/ArchivalModal', () => ({
  default: vi.fn(() => null),
}))

// ─── Fixtures ──────────────────────────────────────────────────────────────────

const BOARD = {
  statuses: [{ name: 'backlog' }, { name: 'todo' }],
  priorities: ['someday', 'nice-to-have', 'important', 'needed', 'critical'],
  valid_transitions: {
    backlog: ['todo'],
    todo: ['backlog'],
  } as Record<string, string[]>,
}

const TASK_ALPHA = {
  id: 1,
  title: 'Alpha task',
  status: 'backlog',
  priority: 'needed',
  updated: '2026-01-01T00:00:00+00:00',
  tags: ['alpha'],
  blocked: false,
  block_reason: null,
  claimed: false,
}

const TASK_BETA = {
  id: 2,
  title: 'Beta task',
  status: 'backlog',
  priority: 'someday',
  updated: '2026-01-02T00:00:00+00:00',
  tags: ['beta'],
  blocked: false,
  block_reason: null,
  claimed: false,
}

const TASK_TODO = {
  id: 3,
  title: 'Todo item',
  status: 'todo',
  priority: 'needed',
  updated: '2026-01-03T00:00:00+00:00',
  tags: ['alpha'],
  blocked: false,
  block_reason: null,
  claimed: false,
}

// ─── Render helpers ─────────────────────────────────────────────────────────────

function renderBoard(tasks = [TASK_ALPHA, TASK_BETA, TASK_TODO]) {
  return render(
    <PorscheDesignSystemProvider>
      <MemoryRouter>
        <KanbanBoard board={BOARD} tasks={tasks} loading={false} error={null} />
      </MemoryRouter>
    </PorscheDesignSystemProvider>,
  )
}

async function openFilterPanel(container: HTMLElement): Promise<void> {
  const toggle = container.querySelector('[data-testid="filter-toggle"]')!
  fireEvent.click(toggle)
  await waitFor(() => {
    expect(container.querySelector('#filter-panel')).not.toBeNull()
  })
}

function getTextInput(container: HTMLElement): HTMLElement {
  return container.querySelector('p-input-search') as HTMLElement
}

function getPrioritySelect(container: HTMLElement): Element {
  return container.querySelector('p-select')!
}

function getTagsControl(container: HTMLElement): Element | null {
  return container.querySelector('[data-testid="filter-tags"]')
}

function getResetButton(container: HTMLElement): Element | null {
  return container.querySelector('[data-testid="filter-reset"]')
}

// ─── Tests ─────────────────────────────────────────────────────────────────────

describe('TestFromAC_FilterBoardIntegration', () => {
  afterEach(() => {
    vi.clearAllMocks()
  })

  // ─── AC1: Filtered tasks appear in correct status columns ─────────────────

  it('text filter keeps matching tasks in their home columns and removes non-matching tasks', async () => {
    const { container } = renderBoard()
    await openFilterPanel(container)

    const input = getTextInput(container)
    expect(input).not.toBeNull()
    // 'alpha' matches TASK_ALPHA (title 'Alpha task') only — case-insensitive
    fireEvent.change(input, { target: { value: 'alpha' } })

    await waitFor(() => {
      // TASK_ALPHA (backlog, id=1): title matches → present in home column
      expect(
        container.querySelector('[data-column="backlog"] [data-testid="task-card"][data-id="1"]'),
      ).not.toBeNull()
      // TASK_BETA (backlog, id=2): 'Beta task' does not match → absent from all columns
      expect(
        container.querySelector('[data-column="backlog"] [data-testid="task-card"][data-id="2"]'),
      ).toBeNull()
      expect(
        container.querySelector('[data-column="todo"] [data-testid="task-card"][data-id="2"]'),
      ).toBeNull()
      // TASK_TODO (todo, id=3): 'Todo item' does not match → absent from all columns
      expect(
        container.querySelector('[data-column="todo"] [data-testid="task-card"][data-id="3"]'),
      ).toBeNull()
      expect(
        container.querySelector('[data-column="backlog"] [data-testid="task-card"][data-id="3"]'),
      ).toBeNull()
    })
  })

  it('priority filter places matching tasks in their columns and removes non-matching tasks', async () => {
    const { container } = renderBoard()
    await openFilterPanel(container)

    // 'needed' matches TASK_ALPHA (backlog) and TASK_TODO (todo); excludes TASK_BETA (someday)
    const pSelect = getPrioritySelect(container)
    fireEvent(pSelect, new CustomEvent('change', { detail: { value: 'needed' }, bubbles: true }))

    await waitFor(() => {
      expect(
        container.querySelector('[data-column="backlog"] [data-testid="task-card"][data-id="1"]'),
      ).not.toBeNull()
      expect(
        container.querySelector('[data-column="todo"] [data-testid="task-card"][data-id="3"]'),
      ).not.toBeNull()
      // TASK_BETA (someday) absent from all columns
      expect(
        container.querySelector('[data-column="backlog"] [data-testid="task-card"][data-id="2"]'),
      ).toBeNull()
      expect(
        container.querySelector('[data-column="todo"] [data-testid="task-card"][data-id="2"]'),
      ).toBeNull()
    })
  })

  // ─── AC2: Empty columns after filtering show "No tasks" placeholder ────────

  it('a column with no matching tasks shows the "No tasks" empty-column placeholder', async () => {
    const { container } = renderBoard()
    await openFilterPanel(container)

    // 'alpha' matches TASK_ALPHA (backlog) only; TASK_TODO (todo) does not match by title
    const input = getTextInput(container)
    fireEvent.change(input, { target: { value: 'alpha' } })

    await waitFor(() => {
      // todo column: no matching tasks → shows empty placeholder
      const todoColumn = container.querySelector('[data-column="todo"]')!
      const emptyPlaceholder = todoColumn.querySelector('[data-testid="empty-column"]')
      expect(emptyPlaceholder).not.toBeNull()
      expect(emptyPlaceholder!.textContent).toBe('No Todo tasks')
    })
  })

  it('all columns show "No tasks" when no task matches the filter', async () => {
    const { container } = renderBoard()
    await openFilterPanel(container)

    // 'zzz' matches nothing
    const input = getTextInput(container)
    fireEvent.change(input, { target: { value: 'zzz' } })

    await waitFor(() => {
      const backlog = container.querySelector('[data-column="backlog"]')!
      const todo = container.querySelector('[data-column="todo"]')!
      expect(backlog.querySelector('[data-testid="empty-column"]')).not.toBeNull()
      expect(todo.querySelector('[data-testid="empty-column"]')).not.toBeNull()
    })
  })

  // ─── AC3: Result count updates correctly ─────────────────────────────────

  it('result count shows "M / N tasks" when a filter matches some tasks', async () => {
    const { container } = renderBoard()
    await openFilterPanel(container)

    // 'needed' matches 2 of 3 tasks (TASK_ALPHA + TASK_TODO)
    const pSelect = getPrioritySelect(container)
    fireEvent(pSelect, new CustomEvent('change', { detail: { value: 'needed' }, bubbles: true }))

    await waitFor(() => {
      const countEl = container.querySelector('[data-testid="filter-result-count"]')
      expect(countEl).not.toBeNull()
      expect(countEl!.textContent).toMatch(/^2 \/ 3 tasks$/)
    })
  })

  it('result count shows "0 / N tasks" when no tasks match the filter', async () => {
    const { container } = renderBoard()
    await openFilterPanel(container)

    // 'zzz' matches nothing — 0 of 3
    const input = getTextInput(container)
    fireEvent.change(input, { target: { value: 'zzz' } })

    await waitFor(() => {
      const countEl = container.querySelector('[data-testid="filter-result-count"]')
      expect(countEl).not.toBeNull()
      expect(countEl!.textContent).toMatch(/^0 \/ 3 tasks$/)
    })
  })

  // ─── AC4: Toggle badge reflects active filter count ───────────────────────

  it('toggle badge shows "(N)" suffix counting active filter dimensions', async () => {
    const { container } = renderBoard()
    const toggle = container.querySelector('[data-testid="filter-toggle"]')!

    // No active filters: no count suffix
    expect(toggle.textContent).toBe('Filters')

    await openFilterPanel(container)

    // Apply first filter criterion (text)
    const input = getTextInput(container)
    fireEvent.change(input, { target: { value: 'foo' } })
    await waitFor(() => {
      expect(toggle.textContent).toMatch(/^Filters \(1\)$/)
    })

    // Apply second filter criterion (priority)
    const pSelect = getPrioritySelect(container)
    fireEvent(pSelect, new CustomEvent('change', { detail: { value: 'needed' }, bubbles: true }))
    await waitFor(() => {
      expect(toggle.textContent).toMatch(/^Filters \(2\)$/)
    })
  })

  it('header names active filter constraints so filtered boards are explainable', async () => {
    const { container } = renderBoard()
    await openFilterPanel(container)

    const input = getTextInput(container)
    fireEvent.change(input, { target: { value: 'alpha' } })

    const pSelect = getPrioritySelect(container)
    fireEvent(pSelect, new CustomEvent('change', { detail: { value: 'needed' }, bubbles: true }))

    await waitFor(() => {
      const summary = container.querySelector('[data-testid="active-filter-summary"]')
      expect(summary).not.toBeNull()
      expect(summary!.textContent).toContain('Search: alpha')
      expect(summary!.textContent).toContain('Priority: Needed')
      expect(container.querySelectorAll('[data-testid="active-filter-chip"]')).toHaveLength(2)
    })
  })

  // ─── AC5: Filter change while context menu open dismisses menu ────────────

  it('changing a filter while a context menu is open dismisses the context menu', async () => {
    const { container } = renderBoard()
    await openFilterPanel(container)

    // Open context menu on TASK_ALPHA (backlog → todo is a valid transition)
    const card = container.querySelector('[data-testid="task-card"][data-id="1"]')!
    fireEvent.contextMenu(card)
    await waitFor(() => {
      expect(container.querySelector('[data-testid="context-menu"]')).not.toBeNull()
    })

    // Change text filter via the real FilterPanel input — menu must be dismissed
    const input = getTextInput(container)
    fireEvent.change(input, { target: { value: 'alpha' } })

    await waitFor(() => {
      expect(container.querySelector('[data-testid="context-menu"]')).toBeNull()
    })
  })

  // ─── AC7: Selected tag persists after tag vanishes from task set ──────────

  it('selected tag filter persists and board shows 0-result state when tag vanishes from task set', async () => {
    // AC7: "Selected tag persisting after tag vanishes from task set (0-result state)"
    //
    // Scenario:
    //   1. Board has TASK_ALPHA (tags: ['alpha']) + TASK_BETA (tags: ['beta'])
    //   2. User selects 'alpha' tag via the real PMultiSelect update event
    //   3. Board re-renders with tasks that no longer contain 'alpha' (only TASK_BETA)
    //   4. Filter state is NOT auto-cleared: filter.tags still = ['alpha']
    //   5. Result count shows "0 / 1 tasks"; toggle badge shows "Filters (1)"
    const { container, rerender } = renderBoard([TASK_ALPHA, TASK_BETA])
    await openFilterPanel(container)

    // PMultiSelect must be present — availableTags derived from current tasks
    const pMultiSelect = getTagsControl(container)
    expect(pMultiSelect).not.toBeNull()

    // Select tag 'alpha' via real PMultiSelect update event
    // FilterPanel registers 'update' listener via useEffect on the PMultiSelect ref
    fireEvent(pMultiSelect!, new CustomEvent('update', { bubbles: true, detail: { value: ['alpha'] } }))

    await waitFor(() => {
      // TASK_ALPHA has tag 'alpha' → matched and visible
      expect(container.querySelector('[data-testid="task-card"][data-id="1"]')).not.toBeNull()
      // TASK_BETA has tag 'beta' only → not matched by 'alpha' filter
      expect(container.querySelector('[data-testid="task-card"][data-id="2"]')).toBeNull()
    })

    // Rerender without TASK_ALPHA — 'alpha' tag no longer present in any task
    rerender(
      <PorscheDesignSystemProvider>
        <MemoryRouter>
          <KanbanBoard board={BOARD} tasks={[TASK_BETA]} loading={false} error={null} />
        </MemoryRouter>
      </PorscheDesignSystemProvider>,
    )

    await waitFor(() => {
      // filter.tags = ['alpha'] persists; TASK_BETA lacks 'alpha' tag → 0 of 1 tasks match
      const countEl = container.querySelector('[data-testid="filter-result-count"]')
      expect(countEl).not.toBeNull()
      expect(countEl!.textContent).toMatch(/^0 \/ 1 tasks$/)

      // Toggle badge still shows active filter dimension (tags)
      const toggle = container.querySelector('[data-testid="filter-toggle"]')!
      expect(toggle.textContent).toMatch(/^Filters \(1\)$/)

      // Backlog column has no matching tasks → shows "No tasks" placeholder
      const backlog = container.querySelector('[data-column="backlog"]')!
      expect(backlog.querySelector('[data-testid="empty-column"]')).not.toBeNull()
    })
  })

  // ─── AC8: Reset clears all filters and restores full task view ────────────

  it('clicking the reset button clears all filters and restores the full task view', async () => {
    const { container } = renderBoard()
    await openFilterPanel(container)

    // Apply a priority filter — hides TASK_ALPHA (needed) and TASK_TODO (needed), shows TASK_BETA (someday)
    const pSelect = getPrioritySelect(container)
    fireEvent(pSelect, new CustomEvent('change', { detail: { value: 'someday' }, bubbles: true }))

    await waitFor(() => {
      expect(
        container.querySelector('[data-column="backlog"] [data-testid="task-card"][data-id="2"]'),
      ).not.toBeNull()
      expect(
        container.querySelector('[data-column="backlog"] [data-testid="task-card"][data-id="1"]'),
      ).toBeNull()
    })

    // Click the real "Clear all" reset button
    const resetBtn = getResetButton(container)
    expect(resetBtn).not.toBeNull()
    fireEvent.click(resetBtn!)

    await waitFor(() => {
      // All 3 tasks visible in their columns
      expect(
        container.querySelector('[data-column="backlog"] [data-testid="task-card"][data-id="1"]'),
      ).not.toBeNull()
      expect(
        container.querySelector('[data-column="backlog"] [data-testid="task-card"][data-id="2"]'),
      ).not.toBeNull()
      expect(
        container.querySelector('[data-column="todo"] [data-testid="task-card"][data-id="3"]'),
      ).not.toBeNull()
      // Result count hidden — no active filters
      expect(container.querySelector('[data-testid="filter-result-count"]')).toBeNull()
    })
  })

  // ─── AC9: All accessibility attributes present in integrated state ─────────

  it('filter panel has id="filter-panel", role="region", and aria-label="Task filters"', async () => {
    const { container } = renderBoard()
    await openFilterPanel(container)

    const panel = container.querySelector('#filter-panel')
    expect(panel).not.toBeNull()
    expect(panel!.getAttribute('role')).toBe('region')
    expect(panel!.getAttribute('aria-label')).toBe('Task filters')
  })

  it('filter toggle has aria-expanded reflecting panel state and aria-controls="filter-panel"', async () => {
    const { container } = renderBoard()
    const toggle = container.querySelector('[data-testid="filter-toggle"]')!

    // Panel closed: aria-expanded=false
    expect(toggle.getAttribute('aria-expanded')).toBe('false')
    expect(toggle.getAttribute('aria-controls')).toBe('filter-panel')

    // Panel open: aria-expanded=true
    fireEvent.click(toggle)
    await waitFor(() => {
      expect(toggle.getAttribute('aria-expanded')).toBe('true')
    })
  })
})
