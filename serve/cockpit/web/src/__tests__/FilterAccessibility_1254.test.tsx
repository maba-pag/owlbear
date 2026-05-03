/**
 * RED phase tests for #1254: P4-01 — Filter accessibility tests
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
 *   - AC1, AC2, AC4, AC5, AC6, AC7, AC8: KanbanBoard + mocked FilterPanel (for toggle/aria-live/focus)
 *   - AC3, AC9: KanbanBoard + real FilterPanel (unmocked) for panel-level attribute and label assertions
 *   - AC7/AC8 focus: KanbanBoard + real FilterPanel because focus must land inside the real DOM controls
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

  // ─── AC3: FilterPanel id/role/aria-label (td:1) — real FilterPanel ────────

  describe('AC3: FilterPanel has id="filter-panel", role="region", aria-label="Task filters"', () => {
    // These tests must NOT mock FilterPanel — they verify the real component's output.
    // vi.mock hoisting means we need to import without the mock for these tests.
    // Strategy: render FilterPanel directly (imported separately below the mock scope).

    it('FilterPanel root element has id="filter-panel"', async () => {
      // Import the real FilterPanel directly — mock is only on the KanbanBoard import path.
      const { default: FilterPanel } = await import('../components/FilterPanel')
      const emptyFilter: FilterState = { text: '', priority: '', tags: [], blocked: false }
      const { container } = render(
        <PorscheDesignSystemProvider>
          <FilterPanel
            filter={emptyFilter}
            onFilterChange={vi.fn()}
            priorities={BOARD.priorities}
            availableTags={['bug']}
            open={true}
          />
        </PorscheDesignSystemProvider>,
      )
      expect(container.querySelector('#filter-panel')).not.toBeNull()
    })

    it('FilterPanel root element has role="region"', async () => {
      const { default: FilterPanel } = await import('../components/FilterPanel')
      const emptyFilter: FilterState = { text: '', priority: '', tags: [], blocked: false }
      const { container } = render(
        <PorscheDesignSystemProvider>
          <FilterPanel
            filter={emptyFilter}
            onFilterChange={vi.fn()}
            priorities={BOARD.priorities}
            availableTags={['bug']}
            open={true}
          />
        </PorscheDesignSystemProvider>,
      )
      // The outermost element rendered by FilterPanel must have role="region"
      const regionEl = container.querySelector('[role="region"]')
      expect(regionEl).not.toBeNull()
    })

    it('FilterPanel root element has aria-label="Task filters"', async () => {
      const { default: FilterPanel } = await import('../components/FilterPanel')
      const emptyFilter: FilterState = { text: '', priority: '', tags: [], blocked: false }
      const { container } = render(
        <PorscheDesignSystemProvider>
          <FilterPanel
            filter={emptyFilter}
            onFilterChange={vi.fn()}
            priorities={BOARD.priorities}
            availableTags={['bug']}
            open={true}
          />
        </PorscheDesignSystemProvider>,
      )
      const regionEl = container.querySelector('[role="region"]')
      expect(regionEl?.getAttribute('aria-label')).toBe('Task filters')
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
        expect(liveRegion!.textContent.trim()).not.toBe('')
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
        expect(liveRegion?.textContent?.trim()).toMatch(/1/)
      })
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
      // The content must reflect the current filtered count
      expect(liveRegion!.textContent.trim()).not.toBe('')
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

      // Advance remaining 200ms → now 300ms after second keystroke → must fire
      await act(async () => { vi.advanceTimersByTime(200) })
      expect(liveRegion?.textContent?.trim()).not.toBe(textBefore?.trim())
      vi.useRealTimers()
    })
  })

  // ─── AC7: Focus moves to first panel control on expand (td:2) ────────────

  describe('AC7: focus moves to first panel control on expand', () => {
    it('focus moves to first focusable control inside FilterPanel when panel opens', async () => {
      // Use real FilterPanel — need actual DOM controls to receive focus.
      // Unmock by importing directly after clearing the module mock.
      // Note: vi.mock is hoisted, so we render KanbanBoard which will use the mock;
      // instead, we construct a minimal integration by rendering FilterPanel directly
      // alongside a toggle-like button to simulate the expand interaction.
      const { default: FilterPanel } = await import('../components/FilterPanel')
      const emptyFilter: FilterState = { text: '', priority: '', tags: [], blocked: false }
      const { container, rerender } = render(
        <PorscheDesignSystemProvider>
          <button data-testid="filter-toggle-real" type="button">Filters</button>
          <FilterPanel
            filter={emptyFilter}
            onFilterChange={vi.fn()}
            priorities={BOARD.priorities}
            availableTags={['bug']}
            open={false}
          />
        </PorscheDesignSystemProvider>,
      )

      // Focus the toggle button (simulates user clicking toggle)
      const toggleBtn = container.querySelector('[data-testid="filter-toggle-real"]') as HTMLElement
      toggleBtn.focus()
      expect(document.activeElement).toBe(toggleBtn)

      // Re-render with panel open — focus must move to first control inside the panel
      rerender(
        <PorscheDesignSystemProvider>
          <button data-testid="filter-toggle-real" type="button">Filters</button>
          <FilterPanel
            filter={emptyFilter}
            onFilterChange={vi.fn()}
            priorities={BOARD.priorities}
            availableTags={['bug']}
            open={true}
          />
        </PorscheDesignSystemProvider>,
      )

      await waitFor(() => {
        const activeEl = document.activeElement
        // Focus must not remain on the toggle button
        expect(activeEl).not.toBe(toggleBtn)
        // Focus must be inside the filter panel region
        const panelRegion = container.querySelector('[role="region"]')
        expect(panelRegion?.contains(activeEl)).toBe(true)
      })
    })

    it('focus does not move outside the panel when panel is already open on re-render', async () => {
      const { default: FilterPanel } = await import('../components/FilterPanel')
      const emptyFilter: FilterState = { text: '', priority: '', tags: [], blocked: false }
      const { container, rerender } = render(
        <PorscheDesignSystemProvider>
          <FilterPanel
            filter={emptyFilter}
            onFilterChange={vi.fn()}
            priorities={BOARD.priorities}
            availableTags={['bug']}
            open={true}
          />
        </PorscheDesignSystemProvider>,
      )

      const panelRegion = container.querySelector('[role="region"]')
      // Manually focus the text input (already inside panel)
      const textInput = container.querySelector('input[type="text"]') as HTMLElement
      textInput?.focus()
      expect(panelRegion?.contains(document.activeElement)).toBe(true)

      // Re-render with open=true again (e.g., tasks polling) — focus must stay inside panel
      rerender(
        <PorscheDesignSystemProvider>
          <FilterPanel
            filter={emptyFilter}
            onFilterChange={vi.fn()}
            priorities={BOARD.priorities}
            availableTags={['bug']}
            open={true}
          />
        </PorscheDesignSystemProvider>,
      )

      expect(panelRegion?.contains(document.activeElement)).toBe(true)
    })
  })

  // ─── AC8: Focus returns to toggle on collapse (td:2) ─────────────────────

  describe('AC8: focus returns to toggle button on collapse (programmatic focus restoration)', () => {
    it('pressing Escape while focus is inside the panel returns focus to toggle button', async () => {
      const { default: FilterPanel } = await import('../components/FilterPanel')
      const emptyFilter: FilterState = { text: '', priority: '', tags: [], blocked: false }
      const onClose = vi.fn()

      const { container, rerender } = render(
        <PorscheDesignSystemProvider>
          <button data-testid="filter-toggle-real" type="button">Filters</button>
          <FilterPanel
            filter={emptyFilter}
            onFilterChange={vi.fn()}
            priorities={BOARD.priorities}
            availableTags={['bug']}
            open={true}
            onClose={onClose}
          />
        </PorscheDesignSystemProvider>,
      )

      // Focus a control inside the panel
      const textInput = container.querySelector('input[type="text"]') as HTMLElement
      textInput?.focus()
      expect(document.activeElement).toBe(textInput)

      // Press Escape — panel should call onClose and focus should return to toggle
      fireEvent.keyDown(textInput, { key: 'Escape', code: 'Escape' })

      // Re-render with panel closed to simulate KanbanBoard's response to onClose
      const toggleBtn = container.querySelector('[data-testid="filter-toggle-real"]') as HTMLElement
      rerender(
        <PorscheDesignSystemProvider>
          <button data-testid="filter-toggle-real" type="button">Filters</button>
          <FilterPanel
            filter={emptyFilter}
            onFilterChange={vi.fn()}
            priorities={BOARD.priorities}
            availableTags={['bug']}
            open={false}
            onClose={onClose}
          />
        </PorscheDesignSystemProvider>,
      )

      await waitFor(() => {
        expect(document.activeElement).toBe(toggleBtn)
      })
    })

    it('re-rendering with open=false while focus is inside panel returns focus to toggle', async () => {
      const { default: FilterPanel } = await import('../components/FilterPanel')
      const emptyFilter: FilterState = { text: '', priority: '', tags: [], blocked: false }

      const { container, rerender } = render(
        <PorscheDesignSystemProvider>
          <button data-testid="filter-toggle-real" type="button">Filters</button>
          <FilterPanel
            filter={emptyFilter}
            onFilterChange={vi.fn()}
            priorities={BOARD.priorities}
            availableTags={['bug']}
            open={true}
          />
        </PorscheDesignSystemProvider>,
      )

      const toggleBtn = container.querySelector('[data-testid="filter-toggle-real"]') as HTMLElement

      // Focus an element inside the panel
      const textInput = container.querySelector('input[type="text"]') as HTMLElement
      textInput?.focus()
      expect(document.activeElement).toBe(textInput)

      // Close panel via prop change (not click — click would place focus on toggle naturally)
      rerender(
        <PorscheDesignSystemProvider>
          <button data-testid="filter-toggle-real" type="button">Filters</button>
          <FilterPanel
            filter={emptyFilter}
            onFilterChange={vi.fn()}
            priorities={BOARD.priorities}
            availableTags={['bug']}
            open={false}
          />
        </PorscheDesignSystemProvider>,
      )

      await waitFor(() => {
        expect(document.activeElement).toBe(toggleBtn)
      })
    })
  })

  // ─── AC9: All filter controls have explicit accessible labels (td:2) ──────

  describe('AC9: text input, priority select, and tags multi-select have explicit accessible labels', () => {
    // Note: blocked switch (role="switch" inside <label>) already has an accessible label.
    // These tests target the THREE unlabeled controls only.

    it('text input (search field) has an accessible label', async () => {
      const { default: FilterPanel } = await import('../components/FilterPanel')
      const emptyFilter: FilterState = { text: '', priority: '', tags: [], blocked: false }
      const { container } = render(
        <PorscheDesignSystemProvider>
          <FilterPanel
            filter={emptyFilter}
            onFilterChange={vi.fn()}
            priorities={BOARD.priorities}
            availableTags={['bug']}
            open={true}
          />
        </PorscheDesignSystemProvider>,
      )
      const textInput = container.querySelector('input[type="text"]') as HTMLElement
      expect(textInput).not.toBeNull()
      // Must have aria-label, aria-labelledby, or an associated <label> element
      const hasAriaLabel = textInput.hasAttribute('aria-label')
      const hasAriaLabelledBy = textInput.hasAttribute('aria-labelledby')
      const inputId = textInput.getAttribute('id')
      const hasAssociatedLabel = inputId
        ? container.querySelector(`label[for="${inputId}"]`) !== null
        : false
      expect(hasAriaLabel || hasAriaLabelledBy || hasAssociatedLabel).toBe(true)
    })

    it('priority select has an accessible label', async () => {
      const { default: FilterPanel } = await import('../components/FilterPanel')
      const emptyFilter: FilterState = { text: '', priority: '', tags: [], blocked: false }
      const { container } = render(
        <PorscheDesignSystemProvider>
          <FilterPanel
            filter={emptyFilter}
            onFilterChange={vi.fn()}
            priorities={BOARD.priorities}
            availableTags={['bug']}
            open={true}
          />
        </PorscheDesignSystemProvider>,
      )
      const pSelect = container.querySelector('p-select')
      expect(pSelect).not.toBeNull()
      // PDS PSelect accepts a label prop that renders as accessible label
      const hasLabel = pSelect!.hasAttribute('label') || pSelect!.hasAttribute('aria-label')
      expect(hasLabel).toBe(true)
    })

    it('tags multi-select has an accessible label', async () => {
      const { default: FilterPanel } = await import('../components/FilterPanel')
      const emptyFilter: FilterState = { text: '', priority: '', tags: [], blocked: false }
      const { container } = render(
        <PorscheDesignSystemProvider>
          <FilterPanel
            filter={emptyFilter}
            onFilterChange={vi.fn()}
            priorities={BOARD.priorities}
            availableTags={['bug', 'feature']}
            open={true}
          />
        </PorscheDesignSystemProvider>,
      )
      const pMultiSelect = container.querySelector('[data-testid="filter-tags"]')
      expect(pMultiSelect).not.toBeNull()
      // PDS PMultiSelect accepts a label prop
      const hasLabel = pMultiSelect!.hasAttribute('label') || pMultiSelect!.hasAttribute('aria-label')
      expect(hasLabel).toBe(true)
    })

    it('blocked switch already has an accessible label (regression guard)', async () => {
      const { default: FilterPanel } = await import('../components/FilterPanel')
      const emptyFilter: FilterState = { text: '', priority: '', tags: [], blocked: false }
      const { container } = render(
        <PorscheDesignSystemProvider>
          <FilterPanel
            filter={emptyFilter}
            onFilterChange={vi.fn()}
            priorities={BOARD.priorities}
            availableTags={['bug']}
            open={true}
          />
        </PorscheDesignSystemProvider>,
      )
      // The blocked switch is inside a <label> element — accessible by definition
      const switchControl = container.querySelector('[role="switch"]') ?? container.querySelector('input[type="checkbox"]')
      expect(switchControl).not.toBeNull()
      const isInsideLabel = switchControl!.closest('label') !== null
      const hasAriaLabel = switchControl!.hasAttribute('aria-label')
      const hasAriaLabelledBy = switchControl!.hasAttribute('aria-labelledby')
      expect(isInsideLabel || hasAriaLabel || hasAriaLabelledBy).toBe(true)
    })
  })
})
