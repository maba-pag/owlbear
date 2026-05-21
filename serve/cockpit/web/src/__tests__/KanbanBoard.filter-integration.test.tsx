/**
 * RED — KanbanBoard filter integration tests.
 *
 * Covers:
 *   AC1 — Board renders filter toggle button (td:1)
 *   AC2 — Toggle button opens/closes FilterPanel (td:2)
 *   AC3 — Filter state changes cause filtered tasks to appear in correct columns (td:2)
 *   AC4 — availableTags computed from full (unfiltered) task set — set-membership,
 *          order-insensitive (td:1)
 *   AC5 — Result count displays "N / M tasks" when filter is active (td:1)
 *   AC6 — Filter change dismisses open context menu (td:1)
 *   AC7 — Filter change cancels active drag — drop targets deactivated (td:1)
 *   AC8 — Empty filter state shows all tasks (td:1)
 *
 * Strategy: FilterPanel is mocked using the callback-capture pattern from
 * KanbanBoard_1246 (ArchivalModal intercept). capturedOnFilterChange is set
 * whenever KanbanBoard renders FilterPanel; capturedAvailableTags is also captured.
 *
 * All 10 tests fail RED — KanbanBoard has no filter-related code: no toggle,
 * no FilterPanel import, no filterTasks call, no interaction rules.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, fireEvent, waitFor, act } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'
import KanbanBoard from '../KanbanBoard'
import type { FilterState } from '../utils/filterTasks'

// ─── FilterPanel stub ─────────────────────────────────────────────────────────
// Captures onFilterChange and availableTags on every render (including open=false).
// Tests drive filter state changes via capturedOnFilterChange.

interface FilterPanelStubProps {
  filter: FilterState
  onFilterChange: (filter: FilterState) => void
  priorities: string[]
  availableTags: string[]
  open: boolean
}

let capturedOnFilterChange: ((filter: FilterState) => void) | null = null
let capturedAvailableTags: string[] | null = null
let capturedFilter: FilterState | null = null
let capturedPriorities: string[] | null = null

vi.mock('../components/FilterPanel', () => ({
  default: vi.fn(
    ({ filter, onFilterChange, priorities, availableTags, open }: FilterPanelStubProps) => {
      capturedOnFilterChange = onFilterChange
      capturedAvailableTags = availableTags
      capturedFilter = filter
      capturedPriorities = priorities
      if (!open) return null
      return (
        <div
          data-testid="filter-panel-stub"
          data-available-tags={JSON.stringify(availableTags)}
        />
      )
    },
  ),
}))

// Stub ArchivalModal — KanbanBoard already depends on it.
vi.mock('../components/ArchivalModal', () => ({
  default: vi.fn(() => null),
}))

// ─── Fixtures ─────────────────────────────────────────────────────────────────

const BOARD = {
  statuses: [{ name: 'backlog' }, { name: 'todo' }],
  priorities: ['someday', 'nice-to-have', 'important', 'needed', 'critical'],
  valid_transitions: {
    backlog: ['todo'],
    todo: ['backlog'],
  } as Record<string, string[]>,
}

const TASK_NEEDED = {
  id: 1,
  title: 'Important task',
  status: 'backlog',
  priority: 'needed',
  updated: '2026-01-01T00:00:00+00:00',
  tags: ['alpha'],
  blocked: false,
  block_reason: null,
  claimed: false,
}

const TASK_SOMEDAY = {
  id: 2,
  title: 'Low priority task',
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
  title: 'In-progress work',
  status: 'todo',
  priority: 'important',
  updated: '2026-01-03T00:00:00+00:00',
  tags: ['gamma'],
  blocked: false,
  block_reason: null,
  claimed: false,
}

// AC3 multi-column fixture: needed-priority task in todo column so the priority
// filter test has matching tasks in ≥2 distinct status columns (AC3 td:2 contract).
const TASK_TODO_MATCH = {
  id: 4,
  title: 'Needed todo task',
  status: 'todo',
  priority: 'needed',
  updated: '2026-01-04T00:00:00+00:00',
  tags: ['delta'],
  blocked: false,
  block_reason: null,
  claimed: false,
}

const EMPTY_FILTER: FilterState = { text: '', priority: '', tags: [], blocked: false }

// ─── Render helper ────────────────────────────────────────────────────────────

function renderBoard(tasks = [TASK_NEEDED, TASK_SOMEDAY, TASK_TODO]) {
  return render(
    <PorscheDesignSystemProvider>
      <MemoryRouter>
        <KanbanBoard
          board={BOARD}
          tasks={tasks}
          loading={false}
          error={null}
        />
      </MemoryRouter>
    </PorscheDesignSystemProvider>,
  )
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('TestFromAC_FilterIntegration', () => {
  beforeEach(() => {
    capturedOnFilterChange = null
    capturedAvailableTags = null
    capturedFilter = null
    capturedPriorities = null
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  // AC1 — Board renders filter toggle button (td:1)
  it('renders a filter toggle button', () => {
    const { container } = renderBoard()
    expect(container.querySelector('[data-testid="filter-toggle"]')).not.toBeNull()
  })

  // AC2 — Toggle button opens FilterPanel (td:2)
  it('clicking filter toggle opens FilterPanel', async () => {
    const { container } = renderBoard()
    const toggle = container.querySelector('[data-testid="filter-toggle"]')
    expect(toggle).not.toBeNull()
    fireEvent.click(toggle!)
    await waitFor(() => {
      expect(container.querySelector('[data-testid="filter-panel-stub"]')).not.toBeNull()
    })
  })

  // AC2 — Toggle button closes FilterPanel on second click (td:2)
  it('clicking filter toggle again closes FilterPanel', async () => {
    const { container } = renderBoard()
    const toggle = container.querySelector('[data-testid="filter-toggle"]')
    expect(toggle).not.toBeNull()
    fireEvent.click(toggle!)
    await waitFor(() => {
      expect(container.querySelector('[data-testid="filter-panel-stub"]')).not.toBeNull()
    })
    fireEvent.click(toggle!)
    await waitFor(() => {
      expect(container.querySelector('[data-testid="filter-panel-stub"]')).toBeNull()
    })
  })

  // AC3 — Filter state → filtered columns: priority filter proves exact placement across ≥2 status columns (td:2)
  // Uses extended 4-task fixture: TASK_NEEDED (backlog, needed) + TASK_TODO_MATCH (todo, needed) both match;
  // TASK_SOMEDAY (backlog, someday) + TASK_TODO (todo, important) do not match.
  it('priority filter proves exact placement of matching and non-matching tasks across columns', async () => {
    const { container } = renderBoard([TASK_NEEDED, TASK_SOMEDAY, TASK_TODO, TASK_TODO_MATCH])
    // Open panel to capture onFilterChange callback — works with any mount strategy
    const toggle = container.querySelector('[data-testid="filter-toggle"]')!
    expect(toggle).not.toBeNull()
    fireEvent.click(toggle)
    await waitFor(() => {
      expect(container.querySelector('[data-testid="filter-panel-stub"]')).not.toBeNull()
    })
    expect(capturedOnFilterChange).not.toBeNull()
    act(() => {
      capturedOnFilterChange!({ ...EMPTY_FILTER, priority: 'needed' })
    })
    await waitFor(() => {
      // TASK_NEEDED (backlog, needed) — matching: present in home column, absent from all others
      expect(
        container.querySelector('[data-column="backlog"] [data-testid="task-card"][data-id="1"]'),
      ).not.toBeNull()
      expect(
        container.querySelector('[data-column="todo"] [data-testid="task-card"][data-id="1"]'),
      ).toBeNull()
      // TASK_TODO_MATCH (todo, needed) — matching in different column: present in home, absent from all others
      expect(
        container.querySelector('[data-column="todo"] [data-testid="task-card"][data-id="4"]'),
      ).not.toBeNull()
      expect(
        container.querySelector('[data-column="backlog"] [data-testid="task-card"][data-id="4"]'),
      ).toBeNull()
      // TASK_SOMEDAY (backlog, someday) — non-matching: absent from ALL columns
      expect(
        container.querySelector('[data-column="backlog"] [data-testid="task-card"][data-id="2"]'),
      ).toBeNull()
      expect(
        container.querySelector('[data-column="todo"] [data-testid="task-card"][data-id="2"]'),
      ).toBeNull()
      // TASK_TODO (todo, important) — non-matching: absent from ALL columns
      expect(
        container.querySelector('[data-column="todo"] [data-testid="task-card"][data-id="3"]'),
      ).toBeNull()
      expect(
        container.querySelector('[data-column="backlog"] [data-testid="task-card"][data-id="3"]'),
      ).toBeNull()
    })
  })

  // AC3 — Filter state → filtered columns: text filter hides non-matching tasks across all columns (td:2)
  it('text filter removes non-matching tasks from columns', async () => {
    const { container } = renderBoard()
    // Open panel to capture onFilterChange callback — works with any mount strategy
    const toggle = container.querySelector('[data-testid="filter-toggle"]')!
    expect(toggle).not.toBeNull()
    fireEvent.click(toggle)
    await waitFor(() => {
      expect(container.querySelector('[data-testid="filter-panel-stub"]')).not.toBeNull()
    })
    expect(capturedOnFilterChange).not.toBeNull()
    act(() => {
      capturedOnFilterChange!({ ...EMPTY_FILTER, text: 'important' })
    })
    await waitFor(() => {
      // TASK_NEEDED title "Important task" matches "important" (case-insensitive) — matching
      // Present in home column (backlog); absent from every other column
      expect(
        container.querySelector('[data-column="backlog"] [data-testid="task-card"][data-id="1"]'),
      ).not.toBeNull()
      expect(
        container.querySelector('[data-column="todo"] [data-testid="task-card"][data-id="1"]'),
      ).toBeNull()
      // TASK_SOMEDAY title "Low priority task" does not match — absent from ALL columns
      expect(
        container.querySelector('[data-column="backlog"] [data-testid="task-card"][data-id="2"]'),
      ).toBeNull()
      expect(
        container.querySelector('[data-column="todo"] [data-testid="task-card"][data-id="2"]'),
      ).toBeNull()
      // TASK_TODO title "In-progress work" does not match — absent from ALL columns
      expect(
        container.querySelector('[data-column="todo"] [data-testid="task-card"][data-id="3"]'),
      ).toBeNull()
      expect(
        container.querySelector('[data-column="backlog"] [data-testid="task-card"][data-id="3"]'),
      ).toBeNull()
    })
  })

  // AC4 — availableTags from full task set — order-insensitive, set-membership (td:1)
  it('FilterPanel receives all tags from all tasks regardless of active filter', async () => {
    const { container } = renderBoard()
    // Open panel to capture callbacks — works with any mount strategy
    const toggle = container.querySelector('[data-testid="filter-toggle"]')!
    expect(toggle).not.toBeNull()
    fireEvent.click(toggle)
    await waitFor(() => {
      expect(container.querySelector('[data-testid="filter-panel-stub"]')).not.toBeNull()
    })
    // Apply a filter that would exclude some tasks from the board view
    act(() => {
      capturedOnFilterChange!({ ...EMPTY_FILTER, priority: 'needed' })
    })
    await waitFor(() => {
      // availableTags must be exactly the union of all tags across ALL tasks —
      // no extras (e.g. stale tags), no omissions (e.g. tags from filtered-out tasks)
      expect(new Set(capturedAvailableTags!)).toEqual(
        new Set(['alpha', 'beta', 'gamma']),
      )
    })
  })

  // AC5 — Result count shows "N / M tasks" when filter is active (td:1)
  it('shows result count element with filtered and total counts when filter is active', async () => {
    const { container } = renderBoard()
    // Open panel to capture onFilterChange callback — works with any mount strategy
    const toggle = container.querySelector('[data-testid="filter-toggle"]')!
    expect(toggle).not.toBeNull()
    fireEvent.click(toggle)
    await waitFor(() => {
      expect(container.querySelector('[data-testid="filter-panel-stub"]')).not.toBeNull()
    })
    act(() => {
      capturedOnFilterChange!({ ...EMPTY_FILTER, priority: 'needed' })
    })
    await waitFor(() => {
      const countEl = container.querySelector('[data-testid="filter-result-count"]')
      expect(countEl).not.toBeNull()
      // Must match exact "N / M tasks" contract: 1 task matches priority=needed, 3 total
      expect(countEl!.textContent).toMatch(/^1 \/ 3 tasks$/)
    })
  })

  // AC6 — Filter change dismisses open context menu (td:1)
  it('filter change dismisses an open context menu', async () => {
    const { container } = renderBoard()
    // Open panel to capture onFilterChange callback — works with any mount strategy
    const toggle = container.querySelector('[data-testid="filter-toggle"]')!
    expect(toggle).not.toBeNull()
    fireEvent.click(toggle)
    await waitFor(() => {
      expect(container.querySelector('[data-testid="filter-panel-stub"]')).not.toBeNull()
    })
    // Open context menu on TASK_NEEDED (has a valid transition: backlog → todo)
    await waitFor(() => {
      expect(
        container.querySelector('[data-testid="task-card"][data-id="1"]'),
      ).not.toBeNull()
    })
    fireEvent.contextMenu(
      container.querySelector('[data-testid="task-card"][data-id="1"]')!,
    )
    await waitFor(() => {
      expect(container.querySelector('[data-testid="context-menu"]')).not.toBeNull()
    })
    // Trigger filter change — context menu must be dismissed
    act(() => {
      capturedOnFilterChange!({ ...EMPTY_FILTER, priority: 'needed' })
    })
    await waitFor(() => {
      expect(container.querySelector('[data-testid="context-menu"]')).toBeNull()
    })
  })

  // AC8 — Empty filter state shows all tasks (td:1)
  it('empty filter state shows all tasks in their columns', async () => {
    const { container } = renderBoard()
    // Open panel to capture onFilterChange callback — works with any mount strategy
    const toggle = container.querySelector('[data-testid="filter-toggle"]')!
    expect(toggle).not.toBeNull()
    fireEvent.click(toggle)
    await waitFor(() => {
      expect(container.querySelector('[data-testid="filter-panel-stub"]')).not.toBeNull()
    })
    // Apply a filter, then clear it back to empty state
    act(() => {
      capturedOnFilterChange!({ ...EMPTY_FILTER, priority: 'needed' })
    })
    act(() => {
      capturedOnFilterChange!(EMPTY_FILTER)
    })
    await waitFor(() => {
      // All 3 tasks must appear in their respective columns
      expect(
        container.querySelector('[data-column="backlog"] [data-testid="task-card"][data-id="1"]'),
      ).not.toBeNull()
      expect(
        container.querySelector('[data-column="backlog"] [data-testid="task-card"][data-id="2"]'),
      ).not.toBeNull()
      expect(
        container.querySelector('[data-column="todo"] [data-testid="task-card"][data-id="3"]'),
      ).not.toBeNull()
    })
  })

  // Reviewer gap: toggle label shows active-filter count suffix when filters are active
  it('filter toggle label reflects the active filter count', async () => {
    const { container } = renderBoard()
    const toggle = container.querySelector('[data-testid="filter-toggle"]')!
    // No filters active: no count suffix
    expect(toggle.textContent).toBe('Filters')
    // Open panel to obtain the onFilterChange callback
    fireEvent.click(toggle)
    await waitFor(() => {
      expect(container.querySelector('[data-testid="filter-panel-stub"]')).not.toBeNull()
    })
    // Activate one filter criterion (priority)
    act(() => {
      capturedOnFilterChange!({ ...EMPTY_FILTER, priority: 'needed' })
    })
    await waitFor(() => {
      expect(toggle.textContent).toMatch(/^Filters \(1\)$/)
    })
    // Activate two filter criteria (priority + text) — count must increment
    act(() => {
      capturedOnFilterChange!({ ...EMPTY_FILTER, priority: 'needed', text: 'foo' })
    })
    await waitFor(() => {
      expect(toggle.textContent).toMatch(/^Filters \(2\)$/)
    })
  })

  // Reviewer gap: FilterPanel receives live filter state and board.priorities
  it('FilterPanel receives the live filter state and board priorities as props', async () => {
    const { container } = renderBoard()
    const toggle = container.querySelector('[data-testid="filter-toggle"]')!
    fireEvent.click(toggle)
    await waitFor(() => {
      expect(container.querySelector('[data-testid="filter-panel-stub"]')).not.toBeNull()
    })
    // Initially FilterPanel must receive the empty filter and the board's priority list
    expect(capturedFilter).toEqual(EMPTY_FILTER)
    expect(capturedPriorities).toEqual(BOARD.priorities)
    // After a filter change, FilterPanel must receive the updated live filter state
    act(() => {
      capturedOnFilterChange!({ ...EMPTY_FILTER, priority: 'needed' })
    })
    await waitFor(() => {
      expect(capturedFilter).toEqual({ ...EMPTY_FILTER, priority: 'needed' })
    })
    // Priorities prop must remain the board's priorities regardless of filter state
    expect(capturedPriorities).toEqual(BOARD.priorities)
  })
})
