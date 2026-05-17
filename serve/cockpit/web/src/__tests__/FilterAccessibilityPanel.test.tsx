/**
 * Filter accessibility tests
 * Part 2 of 2 — Real FilterPanel (unmocked) for panel-level assertions
 *
 * vi.mock() is hoisted by Vitest — dynamic import() in a file with vi.mock always resolves
 * to the mock, even for the "real" module path. These tests therefore live in a separate
 * file with NO vi.mock('../components/FilterPanel'), so the real component is used.
 *
 * Covers:
 *   AC3 (td:1) — FilterPanel has id="filter-panel", role="region", aria-label="Task filters"
 *   AC7 (td:2) — Focus moves to first panel control on expand
 *   AC8 (td:2) — Focus returns to toggle button on collapse (programmatic restoration)
 *   AC9 (td:2) — All filter controls have explicit accessible labels
 *
 */
import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, fireEvent, waitFor } from '@testing-library/react'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'
import FilterPanel from '../components/FilterPanel'
import type { FilterState } from '../utils/filterTasks'
import type { FilterPanelProps } from '../components/FilterPanel'

// ─── Fixtures ─────────────────────────────────────────────────────────────────

const BOARD_PRIORITIES = ['someday', 'nice-to-have', 'important', 'needed', 'critical']
const EMPTY_FILTER: FilterState = { text: '', priority: '', tags: [], blocked: false }

// Extended props type: AC8 requires onClose — not yet in FilterPanelProps (RED)
type FilterPanelExtended = FilterPanelProps & { onClose?: () => void }
const FP = FilterPanel as React.ComponentType<FilterPanelExtended>

// ─── Render helpers ───────────────────────────────────────────────────────────

function renderPanel(open = true, availableTags = ['bug']) {
  return render(
    <PorscheDesignSystemProvider>
      <FilterPanel
        filter={EMPTY_FILTER}
        onFilterChange={vi.fn()}
        priorities={BOARD_PRIORITIES}
        availableTags={availableTags}
        open={open}
      />
    </PorscheDesignSystemProvider>,
  )
}

function getPdsLabel(element: Element): string | null {
  return (element as HTMLElement & { label?: string }).label ?? element.getAttribute('label')
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('TestFromAC_FilterA11yPanel', () => {
  afterEach(() => {
    vi.clearAllMocks()
  })

  // ─── AC3: FilterPanel id/role/aria-label (td:1) ──────────────────────────

  describe('AC3: FilterPanel has id="filter-panel", role="region", aria-label="Task filters"', () => {
    it('a single root element carries id="filter-panel", role="region", and aria-label="Task filters" together', () => {
      const { container } = renderPanel(true)
      const panel = container.querySelector('#filter-panel')
      expect(panel).not.toBeNull()
      expect(panel).toHaveAttribute('role', 'region')
      expect(panel).toHaveAttribute('aria-label', 'Task filters')
    })
  })

  // ─── AC7: Focus moves to first panel control on expand (td:2) ────────────

  describe('AC7: focus moves to first panel control on expand', () => {
    it('focus moves to first focusable control inside FilterPanel when panel opens', async () => {
      const { container, rerender } = render(
        <PorscheDesignSystemProvider>
          <button data-testid="filter-toggle-real" type="button">Filters</button>
          <FilterPanel
            filter={EMPTY_FILTER}
            onFilterChange={vi.fn()}
            priorities={BOARD_PRIORITIES}
            availableTags={['bug']}
            open={false}
          />
        </PorscheDesignSystemProvider>,
      )

      // Focus the toggle button (simulates user about to click toggle)
      const toggleBtn = container.querySelector('[data-testid="filter-toggle-real"]') as HTMLElement
      toggleBtn.focus()
      expect(document.activeElement).toBe(toggleBtn)

      // Re-render with panel open — focus must move to first control inside the panel
      rerender(
        <PorscheDesignSystemProvider>
          <button data-testid="filter-toggle-real" type="button">Filters</button>
          <FilterPanel
            filter={EMPTY_FILTER}
            onFilterChange={vi.fn()}
            priorities={BOARD_PRIORITIES}
            availableTags={['bug']}
            open={true}
          />
        </PorscheDesignSystemProvider>,
      )

      await waitFor(() => {
        // Focus must move to the text input — the first focusable control in the panel
        const textInput = container.querySelector('p-input-search') as HTMLElement
        expect(textInput).not.toBeNull()
        expect(document.activeElement).toBe(textInput)
      })
    })

    it('focus does not move when panel is re-rendered with open=true and focus is already inside', async () => {
      const { container, rerender } = render(
        <PorscheDesignSystemProvider>
          <FilterPanel
            filter={EMPTY_FILTER}
            onFilterChange={vi.fn()}
            priorities={BOARD_PRIORITIES}
            availableTags={['bug']}
            open={true}
          />
        </PorscheDesignSystemProvider>,
      )

      const panelRegion = container.querySelector('[role="region"]')
      // Manually focus the text input (already inside panel)
      const textInput = container.querySelector('p-input-search') as HTMLElement
      textInput?.focus()
      expect(panelRegion?.contains(document.activeElement)).toBe(true)

      // Re-render with open=true again (e.g., tasks polling) — focus must stay inside panel
      rerender(
        <PorscheDesignSystemProvider>
          <FilterPanel
            filter={EMPTY_FILTER}
            onFilterChange={vi.fn()}
            priorities={BOARD_PRIORITIES}
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
      const onClose = vi.fn()

      const { container, rerender } = render(
        <PorscheDesignSystemProvider>
          <button data-testid="filter-toggle-real" type="button">Filters</button>
          <FP
            filter={EMPTY_FILTER}
            onFilterChange={vi.fn()}
            priorities={BOARD_PRIORITIES}
            availableTags={['bug']}
            open={true}
            onClose={onClose}
          />
        </PorscheDesignSystemProvider>,
      )

      // Focus a control inside the panel
      const textInput = container.querySelector('p-input-search') as HTMLElement
      textInput?.focus()
      expect(document.activeElement).toBe(textInput)

      // Press Escape — panel must invoke onClose callback
      fireEvent.keyDown(textInput, { key: 'Escape', code: 'Escape' })
      expect(onClose).toHaveBeenCalledTimes(1)

      // Re-render with panel closed (KanbanBoard's response to onClose)
      const toggleBtn = container.querySelector('[data-testid="filter-toggle-real"]') as HTMLElement
      rerender(
        <PorscheDesignSystemProvider>
          <button data-testid="filter-toggle-real" type="button">Filters</button>
          <FP
            filter={EMPTY_FILTER}
            onFilterChange={vi.fn()}
            priorities={BOARD_PRIORITIES}
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
      const { container, rerender } = render(
        <PorscheDesignSystemProvider>
          <button data-testid="filter-toggle-real" type="button">Filters</button>
          <FilterPanel
            filter={EMPTY_FILTER}
            onFilterChange={vi.fn()}
            priorities={BOARD_PRIORITIES}
            availableTags={['bug']}
            open={true}
          />
        </PorscheDesignSystemProvider>,
      )

      const toggleBtn = container.querySelector('[data-testid="filter-toggle-real"]') as HTMLElement

      // Focus an element inside the panel
      const textInput = container.querySelector('p-input-search') as HTMLElement
      textInput?.focus()
      expect(document.activeElement).toBe(textInput)

      // Close panel via prop change (not click — click would place focus on toggle naturally)
      rerender(
        <PorscheDesignSystemProvider>
          <button data-testid="filter-toggle-real" type="button">Filters</button>
          <FilterPanel
            filter={EMPTY_FILTER}
            onFilterChange={vi.fn()}
            priorities={BOARD_PRIORITIES}
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

    it('text input (search field) has an accessible label', () => {
      const { container } = renderPanel(true)
      const textInput = container.querySelector('p-input-search') as HTMLElement
      expect(textInput).not.toBeNull()
      expect(getPdsLabel(textInput)).toBe('Search tasks')
    })

    it('priority select has an accessible label', () => {
      const { container } = renderPanel(true)
      const pSelect = container.querySelector('p-select')
      expect(pSelect).not.toBeNull()
      expect(getPdsLabel(pSelect!)).toBe('Priority')
    })

    it('tags multi-select has an accessible label', () => {
      const { container } = renderPanel(true, ['bug', 'feature'])
      const pMultiSelect = container.querySelector('[data-testid="filter-tags"]')
      expect(pMultiSelect).not.toBeNull()
      expect(getPdsLabel(pMultiSelect!)).toBe('Tags')
    })

  })
})
