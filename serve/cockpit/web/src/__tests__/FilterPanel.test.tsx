/**
 * FilterPanel component tests
 *
 * Covers all 7 AC lines for FilterPanel:
 *   AC1 (td:2) — renders text input, priority select, tags multi-select,
 *                 blocked switch, reset button when open=true
 *   AC2 (td:1) — priority select populated from priorities prop
 *   AC3 (td:1) — hides tag control entirely when availableTags is empty
 *   AC4 (td:1) — reset button visible only when at least one filter is active
 *   AC5 (td:1) — reset button clears all filter values (calls onFilterChange
 *                 with empty FilterState)
 *   AC6 (td:2) — each control interaction fires onFilterChange with updated FilterState
 *   AC7 (td:1) — does not render controls when open=false — controls absent from DOM
 *
 *
 * Expected component interface (architect-reviewed):
 *   interface FilterPanelProps {
 *     filter: FilterState
 *     onFilterChange: (filter: FilterState) => void
 *     priorities: string[]
 *     availableTags: string[]
 *     open: boolean
 *   }
 *
 * Note: reset button visibility is derived from whether filter differs from
 * emptyState — not from an activeCount prop.
 *
 * Selector strategy: role/label queries preferred; data-testid for tags
 * multi-select (PDS web component — last resort).
 */
import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, fireEvent, within } from '@testing-library/react'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'
import type { FilterState } from '../utils/filterTasks'
import FilterPanel from '../components/FilterPanel'

// ─── Fixtures ─────────────────────────────────────────────────────────────────

const PRIORITIES = ['someday', 'nice-to-have', 'important', 'needed', 'critical']
const TAGS = ['bug', 'feature', 'phase-2']

const emptyFilter: FilterState = { text: '', priority: '', tags: [], blocked: false }

// ─── Render helper ────────────────────────────────────────────────────────────

interface RenderOpts {
  filter?: FilterState
  onFilterChange?: ReturnType<typeof vi.fn>
  priorities?: string[]
  availableTags?: string[]
  open?: boolean
}

function renderPanel({
  filter = emptyFilter,
  onFilterChange = vi.fn(),
  priorities = PRIORITIES,
  availableTags = TAGS,
  open = true,
}: RenderOpts = {}) {
  const utils = render(
    <PorscheDesignSystemProvider>
      <FilterPanel
        filter={filter}
        onFilterChange={onFilterChange}
        priorities={priorities}
        availableTags={availableTags}
        open={open}
      />
    </PorscheDesignSystemProvider>,
  )
  return { ...utils, onFilterChange }
}

function getTextInput(container: HTMLElement): HTMLElement | null {
  return within(container).queryByRole('textbox')
}

function getPrioritySelect(container: HTMLElement): Element | null {
  return container.querySelector('p-select')
}

function getTagsControl(container: HTMLElement): Element | null {
  return container.querySelector('[data-testid="filter-tags"]')
}

function getBlockedControl(container: HTMLElement): Element | null {
  // PDS switch renders as role="switch" or a native checkbox in jsdom
  return container.querySelector('[role="switch"]') ?? container.querySelector('input[type="checkbox"]')
}

function getResetButton(container: HTMLElement): HTMLButtonElement | null {
  return container.querySelector('[data-testid="filter-reset"]')
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('TestFromAC_FilterPanel', () => {
  afterEach(() => {
    vi.resetAllMocks()
  })

  // ─── AC1: Renders all controls when open=true ──────────────────────────────

  describe('AC1: renders text input, priority select, tags, blocked switch, reset when open=true', () => {
    // td:2 — happy path + edge

    it('renders a text input when open=true', () => {
      const { container } = renderPanel()
      expect(getTextInput(container)).not.toBeNull()
    })

    it('renders a priority select when open=true', () => {
      const { container } = renderPanel()
      expect(getPrioritySelect(container)).not.toBeNull()
    })

    it('renders a tags control when open=true and availableTags is non-empty', () => {
      const { container } = renderPanel({ availableTags: TAGS })
      expect(getTagsControl(container)).not.toBeNull()
    })

    it('renders a blocked toggle control when open=true', () => {
      const { container } = renderPanel()
      expect(getBlockedControl(container)).not.toBeNull()
    })

    it('renders a reset button when open=true and a filter is active', () => {
      const { container } = renderPanel({ filter: { ...emptyFilter, text: 'alpha' } })
      expect(getResetButton(container)).not.toBeNull()
    })

    // Edge: open=false — all controls absent (shared with AC7)
    it('no controls rendered when open=false', () => {
      const { container } = renderPanel({ open: false })
      expect(getTextInput(container)).toBeNull()
      expect(getPrioritySelect(container)).toBeNull()
      expect(getBlockedControl(container)).toBeNull()
    })
  })

  // ─── AC2: Priority select populated from priorities prop ──────────────────

  describe('AC2: priority select populated from priorities prop', () => {
    // td:1 — smoke test

    it('priority select contains all option values from the priorities prop', () => {
      const { container } = renderPanel({ priorities: PRIORITIES })
      const pSelect = getPrioritySelect(container)!
      const optionValues = Array.from(pSelect.querySelectorAll('option')).map((o) => (o as HTMLOptionElement).value)
      for (const p of PRIORITIES) {
        expect(optionValues).toContain(p)
      }
    })

    it('priority select has exactly priorities.length options (plus at most one empty placeholder)', () => {
      const custom = ['low', 'medium', 'high']
      const { container } = renderPanel({ priorities: custom })
      const pSelect = getPrioritySelect(container)!
      const options = Array.from(pSelect.querySelectorAll('option')) as HTMLOptionElement[]
      // Total must be exactly custom.length or custom.length+1 (one empty placeholder at most)
      expect(options.length).toBeGreaterThanOrEqual(custom.length)
      expect(options.length).toBeLessThanOrEqual(custom.length + 1)
      // Non-placeholder options must be an exact ordered match to the priorities prop
      const nonEmptyValues = options.filter((o) => o.value !== '').map((o) => o.value)
      expect(nonEmptyValues).toHaveLength(custom.length)
      expect(nonEmptyValues).toEqual(custom)
      // If a placeholder exists it must be at index 0 with an empty string value
      if (options.length > custom.length) {
        expect(options[0].value).toBe('')
      }
    })

    it('priority select reflects a custom priorities list', () => {
      const custom = ['low', 'high']
      const { container } = renderPanel({ priorities: custom })
      const pSelect = getPrioritySelect(container)!
      const optionValues = Array.from(pSelect.querySelectorAll('option')).map((o) => (o as HTMLOptionElement).value)
      expect(optionValues).toContain('low')
      expect(optionValues).toContain('high')
    })
  })

  // ─── AC3: Hides tag control when availableTags is empty ───────────────────

  describe('AC3: hides tag control entirely when availableTags is empty', () => {
    // td:1 — smoke test

    it('tag control is absent from DOM when availableTags is empty', () => {
      const { container } = renderPanel({ availableTags: [] })
      expect(getTagsControl(container)).toBeNull()
    })

    it('tag control is present in DOM when availableTags is non-empty', () => {
      const { container } = renderPanel({ availableTags: ['bug'] })
      expect(getTagsControl(container)).not.toBeNull()
    })
  })

  // ─── AC4: Reset button visible only when a filter is active ───────────────

  describe('AC4: reset button visible only when at least one filter is active', () => {
    // td:1 — smoke test

    it('reset button is absent when filter equals empty state', () => {
      const { container } = renderPanel({ filter: emptyFilter })
      expect(getResetButton(container)).toBeNull()
    })

    it('reset button is present when text filter is non-empty', () => {
      const { container } = renderPanel({ filter: { ...emptyFilter, text: 'alpha' } })
      expect(getResetButton(container)).not.toBeNull()
    })

    it('reset button is present when priority filter is set', () => {
      const { container } = renderPanel({ filter: { ...emptyFilter, priority: 'needed' } })
      expect(getResetButton(container)).not.toBeNull()
    })

    it('reset button is present when blocked filter is enabled', () => {
      const { container } = renderPanel({ filter: { ...emptyFilter, blocked: true } })
      expect(getResetButton(container)).not.toBeNull()
    })

    it('reset button is present when tags filter is non-empty', () => {
      const { container } = renderPanel({ filter: { ...emptyFilter, tags: ['bug'] } })
      expect(getResetButton(container)).not.toBeNull()
    })
  })

  // ─── AC5: Reset button calls onFilterChange with empty FilterState ─────────

  describe('AC5: reset button calls onFilterChange with empty FilterState', () => {
    // td:1 — smoke test

    it('clicking reset calls onFilterChange with the empty FilterState', () => {
      const onFilterChange = vi.fn()
      const { container } = renderPanel({
        filter: { text: 'alpha', priority: 'needed', tags: ['bug'], blocked: true },
        onFilterChange,
      })
      const reset = getResetButton(container)
      expect(reset).not.toBeNull()
      fireEvent.click(reset!)
      expect(onFilterChange).toHaveBeenCalledTimes(1)
      expect(onFilterChange).toHaveBeenCalledWith(emptyFilter)
    })
  })

  // ─── AC6: Control interactions fire onFilterChange ────────────────────────

  describe('AC6: each control interaction fires onFilterChange with updated FilterState', () => {
    // td:2 — happy paths + edge

    it('text input change fires onFilterChange with updated text', () => {
      const onFilterChange = vi.fn()
      const { container } = renderPanel({ filter: emptyFilter, onFilterChange })
      const input = getTextInput(container) as HTMLInputElement
      fireEvent.change(input, { target: { value: 'alpha' } })
      expect(onFilterChange).toHaveBeenCalledTimes(1)
      expect(onFilterChange).toHaveBeenCalledWith({ ...emptyFilter, text: 'alpha' })
    })

    it('clearing text input fires onFilterChange with text: ""', () => {
      const onFilterChange = vi.fn()
      const { container } = renderPanel({
        filter: { ...emptyFilter, text: 'prev' },
        onFilterChange,
      })
      const input = getTextInput(container) as HTMLInputElement
      fireEvent.change(input, { target: { value: '' } })
      expect(onFilterChange).toHaveBeenCalledTimes(1)
      expect(onFilterChange).toHaveBeenCalledWith({ ...emptyFilter, text: '' })
    })

    it('priority select change fires onFilterChange with updated priority', () => {
      const onFilterChange = vi.fn()
      const { container } = renderPanel({ filter: emptyFilter, onFilterChange })
      const pSelect = getPrioritySelect(container)!
      fireEvent(pSelect, new CustomEvent('change', { detail: { value: 'needed' }, bubbles: true }))
      expect(onFilterChange).toHaveBeenCalledTimes(1)
      expect(onFilterChange).toHaveBeenCalledWith({ ...emptyFilter, priority: 'needed' })
    })

    it('clearing priority select fires onFilterChange with priority: ""', () => {
      const onFilterChange = vi.fn()
      const { container } = renderPanel({
        filter: { ...emptyFilter, priority: 'needed' },
        onFilterChange,
      })
      const pSelect = getPrioritySelect(container)!
      fireEvent(pSelect, new CustomEvent('change', { detail: { value: '' }, bubbles: true }))
      expect(onFilterChange).toHaveBeenCalledTimes(1)
      expect(onFilterChange).toHaveBeenCalledWith({ ...emptyFilter, priority: '' })
    })

    it('blocked control interaction fires onFilterChange with blocked: true', () => {
      const onFilterChange = vi.fn()
      const { container } = renderPanel({ filter: emptyFilter, onFilterChange })
      const blocked = getBlockedControl(container) as HTMLElement
      fireEvent.click(blocked)
      expect(onFilterChange).toHaveBeenCalledTimes(1)
      expect(onFilterChange).toHaveBeenCalledWith({ ...emptyFilter, blocked: true })
    })

    it('blocked control interaction fires onFilterChange with blocked: false when currently true', () => {
      const onFilterChange = vi.fn()
      const { container } = renderPanel({
        filter: { ...emptyFilter, blocked: true },
        onFilterChange,
      })
      const blocked = getBlockedControl(container) as HTMLElement
      fireEvent.click(blocked)
      expect(onFilterChange).toHaveBeenCalledTimes(1)
      expect(onFilterChange).toHaveBeenCalledWith({ ...emptyFilter, blocked: false })
    })

    it('tag selection fires onFilterChange with updated tags array', () => {
      const onFilterChange = vi.fn()
      const { container } = renderPanel({ filter: emptyFilter, onFilterChange, availableTags: TAGS })
      const tagsControl = getTagsControl(container) as Element
      // PDS p-multi-select fires a CustomEvent('update', { detail: { value: string[] } })
      fireEvent(tagsControl, new CustomEvent('update', { bubbles: true, detail: { value: ['bug'] } }))
      expect(onFilterChange).toHaveBeenCalledTimes(1)
      expect(onFilterChange).toHaveBeenCalledWith({ ...emptyFilter, tags: ['bug'] })
    })

    it('clearing tag selection fires onFilterChange with tags: []', () => {
      const onFilterChange = vi.fn()
      const { container } = renderPanel({
        filter: { ...emptyFilter, tags: ['bug'] },
        onFilterChange,
        availableTags: TAGS,
      })
      const tagsControl = getTagsControl(container) as Element
      fireEvent(tagsControl, new CustomEvent('update', { bubbles: true, detail: { value: [] } }))
      expect(onFilterChange).toHaveBeenCalledTimes(1)
      expect(onFilterChange).toHaveBeenCalledWith({ ...emptyFilter, tags: [] })
    })

    it('changing text from a multi-field active state preserves priority, tags, and blocked', () => {
      // Sibling-field preservation: start from all-active state, change only text
      const onFilterChange = vi.fn()
      const multiActive: FilterState = { text: 'old', priority: 'needed', tags: ['bug'], blocked: true }
      const { container } = renderPanel({ filter: multiActive, onFilterChange })
      const input = getTextInput(container) as HTMLInputElement
      fireEvent.change(input, { target: { value: 'new' } })
      expect(onFilterChange).toHaveBeenCalledTimes(1)
      expect(onFilterChange).toHaveBeenCalledWith({
        text: 'new',
        priority: 'needed',
        tags: ['bug'],
        blocked: true,
      })
    })

    it('changing priority from a multi-field active state preserves text, tags, and blocked', () => {
      // Sibling-field preservation: start from all-active state, change only priority
      const onFilterChange = vi.fn()
      const multiActive: FilterState = { text: 'search', priority: 'needed', tags: ['bug'], blocked: true }
      const { container } = renderPanel({ filter: multiActive, onFilterChange })
      const pSelect = getPrioritySelect(container)!
      fireEvent(pSelect, new CustomEvent('change', { detail: { value: 'critical' }, bubbles: true }))
      expect(onFilterChange).toHaveBeenCalledTimes(1)
      expect(onFilterChange).toHaveBeenCalledWith({
        text: 'search',
        priority: 'critical',
        tags: ['bug'],
        blocked: true,
      })
    })

    it('toggling blocked from a multi-field active state preserves text, priority, and tags', () => {
      // Sibling-field preservation: start from all-active state, toggle only blocked
      const onFilterChange = vi.fn()
      const multiActive: FilterState = { text: 'search', priority: 'needed', tags: ['bug'], blocked: true }
      const { container } = renderPanel({ filter: multiActive, onFilterChange })
      const blocked = getBlockedControl(container) as HTMLElement
      fireEvent.click(blocked)
      expect(onFilterChange).toHaveBeenCalledTimes(1)
      expect(onFilterChange).toHaveBeenCalledWith({
        text: 'search',
        priority: 'needed',
        tags: ['bug'],
        blocked: false,
      })
    })

    it('changing tags from a multi-field active state preserves text, priority, and blocked', () => {
      // Sibling-field preservation: start from all-active state, change only tags
      const onFilterChange = vi.fn()
      const multiActive: FilterState = { text: 'search', priority: 'needed', tags: ['bug'], blocked: true }
      const { container } = renderPanel({ filter: multiActive, onFilterChange, availableTags: TAGS })
      const tagsControl = getTagsControl(container) as Element
      fireEvent(tagsControl, new CustomEvent('update', { bubbles: true, detail: { value: ['feature'] } }))
      expect(onFilterChange).toHaveBeenCalledTimes(1)
      expect(onFilterChange).toHaveBeenCalledWith({
        text: 'search',
        priority: 'needed',
        tags: ['feature'],
        blocked: true,
      })
    })
  })

  // ─── AC7: Does not render controls when open=false ────────────────────────

  describe('AC7: controls absent from DOM when open=false', () => {
    // td:1 — smoke test

    it('text input is absent from DOM when open=false', () => {
      const { container } = renderPanel({ open: false })
      expect(container.querySelector('input[type="text"]')).toBeNull()
    })

    it('priority select is absent from DOM when open=false', () => {
      const { container } = renderPanel({ open: false })
      expect(container.querySelector('p-select')).toBeNull()
    })

    it('blocked control is absent from DOM when open=false', () => {
      const { container } = renderPanel({ open: false })
      expect(getBlockedControl(container)).toBeNull()
    })

    it('tag control is absent from DOM when open=false (regardless of availableTags)', () => {
      const { container } = renderPanel({ open: false, availableTags: TAGS })
      expect(getTagsControl(container)).toBeNull()
    })

    it('reset button is absent from DOM when open=false (even when filter is active)', () => {
      const { container } = renderPanel({
        open: false,
        filter: { text: 'active', priority: 'needed', tags: ['bug'], blocked: true },
      })
      expect(getResetButton(container)).toBeNull()
    })
  })

  // ─── AC controlled (retry #1251): Rendered state mirrors incoming filter prop ─
  //
  // These tests prove the controlled-component contract: each field of the
  // incoming `filter` prop is reflected in the rendered DOM — not only emitted
  // via callbacks.  Regression guard: removing any value/checked binding from
  // FilterPanel.tsx must cause at least one test below to fail.

  describe('AC controlled: rendered control state mirrors incoming filter prop', () => {
    it('text input value reflects filter.text', () => {
      const { container } = renderPanel({ filter: { ...emptyFilter, text: 'hello world' } })
      const input = getTextInput(container) as HTMLInputElement
      expect(input.value).toBe('hello world')
    })

    it('priority select value attribute reflects filter.priority', () => {
      const { container } = renderPanel({ filter: { ...emptyFilter, priority: 'needed' } })
      const pSelect = getPrioritySelect(container)!
      // PDS React wrapper sets value as a DOM property on the custom element
      type WithValue = Element & { value?: unknown }
      expect((pSelect as WithValue).value).toBe('needed')
    })

    it('priority select value is empty when filter.priority is empty', () => {
      const { container } = renderPanel({ filter: emptyFilter })
      const pSelect = getPrioritySelect(container)!
      type WithValue = Element & { value?: unknown }
      const val = (pSelect as WithValue).value
      expect(val === '' || val === undefined || val === null).toBe(true)
    })

    it('blocked checkbox checked state reflects filter.blocked true', () => {
      const { container } = renderPanel({ filter: { ...emptyFilter, blocked: true } })
      const blocked = getBlockedControl(container) as HTMLInputElement
      expect(blocked.checked).toBe(true)
    })

    it('blocked checkbox checked state reflects filter.blocked false', () => {
      const { container } = renderPanel({ filter: { ...emptyFilter, blocked: false } })
      const blocked = getBlockedControl(container) as HTMLInputElement
      expect(blocked.checked).toBe(false)
    })

    it('tags multi-select value prop reflects filter.tags', () => {
      const { container } = renderPanel({
        filter: { ...emptyFilter, tags: ['bug', 'feature'] },
        availableTags: TAGS,
      })
      const tagsControl = getTagsControl(container)!
      // React 19 sets array props as DOM properties on custom elements.
      // The value property on the p-multi-select element must equal the incoming tags array.
      type WithValue = Element & { value?: unknown }
      expect((tagsControl as WithValue).value).toEqual(['bug', 'feature'])
    })
  })
})

