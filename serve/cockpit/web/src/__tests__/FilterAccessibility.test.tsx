/**
 * Workflow behavior tests1254: P4-01 — Filter accessibility tests
 *
 * Covers all 9 AC items for filter accessibility (td:0 "all fail" AC is meta):
 *   AC1 (td:2) — Toggle button has aria-expanded reflecting panelOpen state
 *   AC2 (td:1) — Toggle button has aria-controls="filter-panel"
 *   AC3 (td:1) — FilterPanel has id="filter-panel", role="region", aria-label="Task filters"
 *   AC4 (td:1) — Result count region has aria-live="polite"
 *   AC5 (td:2) — aria-live announces only on user-initiated changes; polling must NOT trigger announcement
 *   AC6 (td:2) — aria-live debounced: fires 300ms after last text input keystroke
 *   AC7 (td:2) — Focus moves to first panel control on expand
 *   AC8 (td:2) — Focus returns to toggle button on collapse (programmatic restoration)
 *   AC9 (td:2) — All filter controls have explicit accessible labels (text input, priority select, tags multi-select)
 *
 * All tests FAIL (RED) — no accessibility attributes exist on FilterPanel or the toggle button.
 *
 * Strategy:
 *   - AC1, AC2, AC4, AC5, AC6: KanbanBoard + mocked FilterPanel (for toggle/aria-live/debounce)
 *   - AC3, AC7, AC8, AC9: see FilterAccessibilityPanel_1254.test.tsx (real FilterPanel, no vi.mock)
 *     vi.mock() is hoisted — dynamic import() in a mocked file always resolves to the mock,
 *     so panel-level / focus / label assertions live in a separate unmocked file.
 *
 * Note: AC9 targets text input, priority select, and tags multi-select — the blocked switch
 * (role="switch" inside <label>) already has an accessible label and is not tested here.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, fireEvent, waitFor, act } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'
import KanbanBoard from '../KanbanBoard'
import type { FilterState } from '../utils/filterTasks'

// ─── Fixtures ─────────────────────────────────────────────────────────────────

const BOARD = {
  statuses: [{ name: 'backlog' }, { name: 'todo' }],
  priorities: ['someday', 'nice-to-have', 'important', 'needed', 'critical'],
  valid_transitions: {
    backlog: ['todo'],
    todo: ['backlog'],
  } as Record<string, string[]>,
}

const TASK_A = {
  id: 1,
  title: 'Alpha task',
  status: 'backlog',
  priority: 'needed',
  updated: '2026-01-01T00:00:00+00:00',
  tags: ['bug'],
  blocked: false,
  block_reason: null,
  claimed: false,
}

const TASK_B = {
  id: 2,
  title: 'Beta task',
  status: 'backlog',
  priority: 'someday',
  updated: '2026-01-02T00:00:00+00:00',
  tags: ['feature'],
  blocked: false,
  block_reason: null,
  claimed: false,
}

// ─── Stub & capture state for mocked-FilterPanel tests ───────────────────────

interface FilterPanelStubProps {
  filter: FilterState
  onFilterChange: (filter: FilterState) => void
  priorities: string[]
  availableTags: string[]
  open: boolean
}

let capturedOnFilterChange: ((filter: FilterState) => void) | null = null

vi.mock('../components/FilterPanel', () => ({
  default: vi.fn(({ filter, onFilterChange, open }: FilterPanelStubProps) => {
    capturedOnFilterChange = onFilterChange
    if (!open) return null
    return <div data-testid="filter-panel-stub" data-filter={JSON.stringify(filter)} />
  }),
}))

vi.mock('../components/ArchivalModal', () => ({
  default: vi.fn(() => null),
}))

// ─── Render helpers ───────────────────────────────────────────────────────────

function renderBoard(tasks = [TASK_A, TASK_B]) {
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

function getToggle(container: HTMLElement): HTMLElement {
  const el = container.querySelector('[data-testid="filter-toggle"]')
  if (!el) throw new Error('filter-toggle not found')
  return el as HTMLElement
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('TestFromAC_FilterA11y', () => {
  beforeEach(() => {
    capturedOnFilterChange = null
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.clearAllTimers()
  })

  // ─── AC1: Toggle button aria-expanded (td:2) ─────────────────────────────

  describe('AC1: toggle button has aria-expanded reflecting panelOpen state', () => {
    it('aria-expanded is "false" when panel is closed (initial state)', () => {
      const { container } = renderBoard()
      const toggle = getToggle(container)
      expect(toggle.getAttribute('aria-expanded')).toBe('false')
    })

    it('aria-expanded is "true" after clicking toggle to open panel', async () => {
      const { container } = renderBoard()
      const toggle = getToggle(container)
      fireEvent.click(toggle)
      await waitFor(() => {
        expect(toggle.getAttribute('aria-expanded')).toBe('true')
      })
    })

    it('aria-expanded returns to "false" after toggling panel closed', async () => {
      const { container } = renderBoard()
      const toggle = getToggle(container)
      fireEvent.click(toggle)
      await waitFor(() => expect(toggle.getAttribute('aria-expanded')).toBe('true'))
      fireEvent.click(toggle)
      await waitFor(() => {
        expect(toggle.getAttribute('aria-expanded')).toBe('false')
      })
    })
  })

  // ─── AC2: Toggle button aria-controls (td:1) ─────────────────────────────

  describe('AC2: toggle button has aria-controls="filter-panel"', () => {
    it('toggle button has aria-controls="filter-panel"', () => {
      const { container } = renderBoard()
      const toggle = getToggle(container)
      expect(toggle.getAttribute('aria-controls')).toBe('filter-panel')
    })
  })

  // ─── AC4: Result count region has aria-live="polite" (td:1) ──────────────

  describe('AC4: result count region has aria-live="polite"', () => {
    it('result count region has aria-live="polite" when filter is active', async () => {
      const { container } = renderBoard()
      // Apply a filter to make the result count visible
      fireEvent.click(getToggle(container))
      await waitFor(() => expect(capturedOnFilterChange).not.toBeNull())
      act(() => {
        capturedOnFilterChange!({ text: 'Alpha', priority: '', tags: [], blocked: false })
      })
      await waitFor(() => {
        const liveRegion = container.querySelector('[aria-live="polite"]')
        expect(liveRegion).not.toBeNull()
      })
    })

    it('result count aria-live region is present in DOM even when filter is inactive (always rendered)', () => {
      // aria-live regions must be pre-rendered in DOM before announcements fire correctly.
      // The region may be visually hidden but must exist from initial mount.
      const { container } = renderBoard()
      const liveRegion = container.querySelector('[aria-live="polite"]')
      expect(liveRegion).not.toBeNull()
    })
  })

  // ─── AC5: aria-live user-initiated only — NOT polling (td:2) ─────────────

  describe('AC5: aria-live region updates on user filter change but NOT on polling-driven task updates', () => {
    it('aria-live region text updates when user applies a filter', async () => {
      const { container } = renderBoard([TASK_A, TASK_B])
      fireEvent.click(getToggle(container))
      await waitFor(() => expect(capturedOnFilterChange).not.toBeNull())
      act(() => {
        capturedOnFilterChange!({ text: 'Alpha', priority: '', tags: [], blocked: false })
      })
      await waitFor(() => {
        const liveRegion = container.querySelector('[aria-live="polite"]')
        expect(liveRegion).not.toBeNull()
        expect(liveRegion!.textContent.trim()).toBe('1 / 2 tasks')
      })
    })

    it('aria-live region text does NOT change when tasks prop updates without filter state change (polling)', async () => {
      const { container, rerender } = renderBoard([TASK_A, TASK_B])
      // Ensure panel is closed and no user filter is active
      const liveRegion = container.querySelector('[aria-live="polite"]')
      expect(liveRegion).not.toBeNull()
      const initialText = liveRegion!.textContent

      // Simulate polling: add a new task without changing filter state
      const TASK_C = {
        id: 3,
        title: 'Gamma task',
        status: 'backlog',
        priority: 'important',
        updated: '2026-01-03T00:00:00+00:00',
        tags: [],
        blocked: false,
        block_reason: null,
        claimed: false,
      }
      rerender(
        <PorscheDesignSystemProvider>
          <MemoryRouter>
            <KanbanBoard
              board={BOARD}
              tasks={[TASK_A, TASK_B, TASK_C]}
              loading={false}
              error={null}
            />
          </MemoryRouter>
        </PorscheDesignSystemProvider>,
      )

      // aria-live region must remain unchanged — polling must not trigger an announcement
      expect(liveRegion!.textContent).toBe(initialText)
    })

    it('aria-live region updates immediately (no debounce) when non-text filter (priority) changes', async () => {
      const { container } = renderBoard([TASK_A, TASK_B])
      fireEvent.click(getToggle(container))
      await waitFor(() => expect(capturedOnFilterChange).not.toBeNull())

      // Priority change is a non-text filter — must fire immediately without waiting 300ms
      act(() => {
        capturedOnFilterChange!({ text: '', priority: 'needed', tags: [], blocked: false })
      })

      // No waitFor needed — announcement is synchronous for non-text changes
      const liveRegion = container.querySelector('[aria-live="polite"]')
      expect(liveRegion!.textContent.trim()).toBe('1 / 2 tasks')
    })

    it('aria-live region text updates after user-initiated filter change even after prior polling update', async () => {
      const { container, rerender } = renderBoard([TASK_A, TASK_B])
      fireEvent.click(getToggle(container))
      await waitFor(() => expect(capturedOnFilterChange).not.toBeNull())

      // First: simulate polling update (no filter change)
      rerender(
        <PorscheDesignSystemProvider>
          <MemoryRouter>
            <KanbanBoard
              board={BOARD}
              tasks={[TASK_A, TASK_B]}
              loading={false}
              error={null}
            />
          </MemoryRouter>
        </PorscheDesignSystemProvider>,
      )

      // Then: user applies filter → aria-live MUST update
      act(() => {
        capturedOnFilterChange!({ text: 'Alpha', priority: '', tags: [], blocked: false })
      })
      await waitFor(() => {
        const liveRegion = container.querySelector('[aria-live="polite"]')
        expect(liveRegion?.textContent?.trim()).toBe('1 / 2 tasks')
      })
    })

    it('aria-live does not update when polling changes visible count while active filter is already applied', async () => {
      vi.useFakeTimers()
      const { container, rerender } = renderBoard([TASK_A, TASK_B])
      fireEvent.click(getToggle(container))
      await act(async () => { vi.advanceTimersByTime(0) })
      expect(capturedOnFilterChange).not.toBeNull()

      // Apply text filter 'A' — both TASK_A ('Alpha task') and TASK_B ('Beta task')
      // match case-insensitively → '2 / 2 tasks' announced after 300ms debounce
      act(() => {
        capturedOnFilterChange!({ text: 'A', priority: '', tags: [], blocked: false })
      })
      await act(async () => { vi.advanceTimersByTime(300) })
      const liveRegion = container.querySelector('[aria-live="polite"]')
      expect(liveRegion!.textContent.trim()).toBe('2 / 2 tasks')
      const announcedText = liveRegion!.textContent

      // Simulate polling: add a task that ALSO matches 'A' — visible count would become 3
      const TASK_ANOTHER = {
        id: 4,
        title: 'Another task',
        status: 'backlog',
        priority: 'important',
        updated: '2026-01-04T00:00:00+00:00',
        tags: [],
        blocked: false,
        block_reason: null,
        claimed: false,
      }
      rerender(
        <PorscheDesignSystemProvider>
          <MemoryRouter>
            <KanbanBoard
              board={BOARD}
              tasks={[TASK_A, TASK_B, TASK_ANOTHER]}
              loading={false}
              error={null}
            />
          </MemoryRouter>
        </PorscheDesignSystemProvider>,
      )

      // aria-live region must remain unchanged — polling must NOT trigger re-announcement
      expect(liveRegion!.textContent).toBe(announcedText)
      vi.useRealTimers()
    })
  })

  // ─── AC6: aria-live debounce 300ms (td:2) ────────────────────────────────

  describe('AC6: aria-live fires 300ms after last text input keystroke', () => {
    it('aria-live region does not update immediately after text input change', async () => {
      vi.useFakeTimers()
      const { container } = renderBoard()
      fireEvent.click(getToggle(container))
      await act(async () => { vi.advanceTimersByTime(0) })

      expect(capturedOnFilterChange).not.toBeNull()
      const liveRegion = container.querySelector('[aria-live="polite"]')
      expect(liveRegion).not.toBeNull()
      const textBefore = liveRegion!.textContent

      act(() => {
        capturedOnFilterChange!({ text: 'Al', priority: '', tags: [], blocked: false })
      })
      // Advance only 299ms — should NOT have fired yet
      await act(async () => { vi.advanceTimersByTime(299) })

      expect(liveRegion!.textContent).toBe(textBefore)
      vi.useRealTimers()
    })

    it('aria-live region updates after 300ms following last text keystroke', async () => {
      vi.useFakeTimers()
      const { container } = renderBoard()
      fireEvent.click(getToggle(container))
      await act(async () => { vi.advanceTimersByTime(0) })

      expect(capturedOnFilterChange).not.toBeNull()

      act(() => {
        capturedOnFilterChange!({ text: 'Al', priority: '', tags: [], blocked: false })
      })
      // Advance full 300ms — announcement must fire
      await act(async () => { vi.advanceTimersByTime(300) })

      const liveRegion = container.querySelector('[aria-live="polite"]')
      expect(liveRegion).not.toBeNull()
      // The content must reflect the current filtered count — text='Al' matches TASK_A ('Alpha task')
      expect(liveRegion!.textContent.trim()).toBe('1 / 2 tasks')
      vi.useRealTimers()
    })

    it('rapid keystrokes restart the 300ms debounce — only one announcement fires', async () => {
      vi.useFakeTimers()
      const { container } = renderBoard()
      fireEvent.click(getToggle(container))
      await act(async () => { vi.advanceTimersByTime(0) })

      expect(capturedOnFilterChange).not.toBeNull()
      const liveRegion = container.querySelector('[aria-live="polite"]')
      const textBefore = liveRegion?.textContent

      // Two rapid keystrokes within 300ms of each other
      act(() => {
        capturedOnFilterChange!({ text: 'A', priority: '', tags: [], blocked: false })
      })
      await act(async () => { vi.advanceTimersByTime(100) })
      act(() => {
        capturedOnFilterChange!({ text: 'Al', priority: '', tags: [], blocked: false })
      })
      // 100ms after second keystroke → still within debounce window
      await act(async () => { vi.advanceTimersByTime(100) })

      // Should NOT have fired yet (debounce reset on second keystroke)
      expect(liveRegion?.textContent).toBe(textBefore)

      // Advance 100ms more → t=300 from start; this is where the FIRST timer would fire
      // if it was NOT cancelled when the second keystroke reset the debounce.
      // If timer cancellation is broken, '2 / 2 tasks' would appear here.
      await act(async () => { vi.advanceTimersByTime(100) })
      // First timer must be cancelled — no announcement at the stale boundary
      expect(liveRegion?.textContent).toBe(textBefore)

      // Advance final 100ms → t=400; now 300ms after SECOND keystroke → announcement must fire
      await act(async () => { vi.advanceTimersByTime(100) })
      // text='Al' matches TASK_A ('Alpha task') → exactly '1 / 2 tasks'
      expect(liveRegion?.textContent?.trim()).toBe('1 / 2 tasks')
      vi.useRealTimers()
    })
  })
})
