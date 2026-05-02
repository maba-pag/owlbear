/**
 * Tests for #1252: P3-01: RED — KanbanBoard filter integration tests.
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

vi.mock('../components/FilterPanel', () => ({
  default: vi.fn(
    ({ onFilterChange, availableTags, open }: FilterPanelStubProps) => {
      capturedOnFilterChange = onFilterChange
      capturedAvailableTags = availableTags
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

  // AC3 — Filter state → filtered columns: priority filter hides non-matching tasks (td:2)
  it('priority filter removes non-matching tasks from columns', async () => {
    const { container } = renderBoard()
    // FilterPanel must be rendered for onFilterChange to be captured
    expect(capturedOnFilterChange).not.toBeNull()
    act(() => {
      capturedOnFilterChange!({ ...EMPTY_FILTER, priority: 'needed' })
    })
    await waitFor(() => {
      // TASK_NEEDED (priority=needed) should remain
      expect(
        container.querySelector('[data-column="backlog"] [data-testid="task-card"][data-id="1"]'),
      ).not.toBeNull()
      // TASK_SOMEDAY (priority=someday) should be hidden
      expect(
        container.querySelector('[data-column="backlog"] [data-testid="task-card"][data-id="2"]'),
      ).toBeNull()
    })
  })

  // AC3 — Filter state → filtered columns: text filter hides non-matching tasks (td:2)
  it('text filter removes non-matching tasks from columns', async () => {
    const { container } = renderBoard()
    expect(capturedOnFilterChange).not.toBeNull()
    act(() => {
      capturedOnFilterChange!({ ...EMPTY_FILTER, text: 'important' })
    })
    await waitFor(() => {
      // TASK_NEEDED title "Important task" matches "important" (case-insensitive)
      expect(
        container.querySelector('[data-column="backlog"] [data-testid="task-card"][data-id="1"]'),
      ).not.toBeNull()
      // TASK_SOMEDAY title "Low priority task" does not match
      expect(
        container.querySelector('[data-column="backlog"] [data-testid="task-card"][data-id="2"]'),
      ).toBeNull()
    })
  })

  // AC4 — availableTags from full task set — order-insensitive, set-membership (td:1)
  it('FilterPanel receives all tags from all tasks regardless of active filter', async () => {
    renderBoard()
    // FilterPanel must be rendered (with open=false) so tags are captured immediately
    expect(capturedAvailableTags).not.toBeNull()
    // Apply a filter that would exclude some tasks from the board view
    act(() => {
      capturedOnFilterChange!({ ...EMPTY_FILTER, priority: 'needed' })
    })
    await waitFor(() => {
      // Even after filtering, availableTags must include tags from ALL tasks
      const tags = new Set(capturedAvailableTags!)
      expect(tags.has('alpha')).toBe(true)  // from TASK_NEEDED (matches filter)
      expect(tags.has('beta')).toBe(true)   // from TASK_SOMEDAY (excluded by filter)
      expect(tags.has('gamma')).toBe(true)  // from TASK_TODO (excluded by filter)
    })
  })

  // AC5 — Result count shows "N / M tasks" when filter is active (td:1)
  it('shows result count element with filtered and total counts when filter is active', async () => {
    const { container } = renderBoard()
    expect(capturedOnFilterChange).not.toBeNull()
    act(() => {
      capturedOnFilterChange!({ ...EMPTY_FILTER, priority: 'needed' })
    })
    await waitFor(() => {
      const countEl = container.querySelector('[data-testid="filter-result-count"]')
      expect(countEl).not.toBeNull()
      // 1 task matches priority=needed out of 3 total tasks
      expect(countEl!.textContent).toMatch(/1/)
      expect(countEl!.textContent).toMatch(/3/)
    })
  })

  // AC6 — Filter change dismisses open context menu (td:1)
  it('filter change dismisses an open context menu', async () => {
    const { container } = renderBoard()
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
    expect(capturedOnFilterChange).not.toBeNull()
    act(() => {
      capturedOnFilterChange!({ ...EMPTY_FILTER, priority: 'needed' })
    })
    await waitFor(() => {
      expect(container.querySelector('[data-testid="context-menu"]')).toBeNull()
    })
  })

  // AC7 — Filter change cancels active drag — drop targets deactivated (td:1)
  it('filter change deactivates drop targets by cancelling active drag', async () => {
    const { container } = renderBoard()
    // Start drag on TASK_NEEDED (backlog → todo is a valid transition)
    await waitFor(() => {
      expect(
        container.querySelector('[data-testid="task-card"][data-id="1"]'),
      ).not.toBeNull()
    })
    const card = container.querySelector('[data-testid="task-card"][data-id="1"]')!
    fireEvent.dragStart(card)
    // Verify the todo column is an active drag target before filter change
    const todoColumn = container.querySelector('[data-column="todo"]')!
    fireEvent.dragOver(todoColumn)
    await waitFor(() => {
      expect(todoColumn.getAttribute('data-drag-over')).toBe('true')
    })
    // Filter change must cancel the drag; drop targets should be deactivated
    expect(capturedOnFilterChange).not.toBeNull()
    act(() => {
      capturedOnFilterChange!({ ...EMPTY_FILTER, priority: 'needed' })
    })
    // Reset hover state, then re-enter to check isValidDragTarget is now false
    fireEvent.dragLeave(todoColumn)
    fireEvent.dragOver(todoColumn)
    await waitFor(() => {
      expect(todoColumn.getAttribute('data-drag-over')).toBeNull()
    })
  })

  // AC8 — Empty filter state shows all tasks (td:1)
  it('empty filter state shows all tasks in their columns', async () => {
    const { container } = renderBoard()
    expect(capturedOnFilterChange).not.toBeNull()
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
})
