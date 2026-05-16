// @vitest-environment jsdom

/**
 * FilterPanel PDS controls — task #1617
 * P2-09: Filter panel PDS controls (blocked checkbox + priority select + flex layout)
 *
 * AC1 — Blocked checkbox uses PCheckbox React wrapper with checked prop and onChange handler
 *        (replaces raw <p-checkbox> web component with onClick)
 * AC2 — Priority PSelect uses PSelectOption children (replaces native <option> elements)
 * AC3 — Filter panel .filter-panel uses flex layout:
 *        display: flex; flex-wrap: wrap; gap: var(--pds-spacing-sm); align-items: flex-end
 *
 * All tests in this file are RED-phase: they FAIL against the current implementation
 * and PASS only after the builder completes #1617.
 */

import * as fs from 'node:fs'
import * as path from 'node:path'
import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, fireEvent } from '@testing-library/react'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'
import type { FilterState } from '../utils/filterTasks'
import FilterPanel from '../components/FilterPanel'

// ─── CSS path ─────────────────────────────────────────────────────────────────

const FILTER_PANEL_CSS = path.resolve(__dirname, '../components/FilterPanel.css')

// ─── Fixtures ─────────────────────────────────────────────────────────────────

const PRIORITIES = ['critical', 'needed', 'important', 'nice-to-have', 'someday']
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

// ─── AC1: PCheckbox React wrapper with checked prop + onChange handler ─────────

describe('TestFromAC_PCheckboxWrapper', () => {
  afterEach(() => {
    vi.resetAllMocks()
  })

  it('blocked control checked DOM property is true when filter.blocked is true', () => {
    // AC1: PCheckbox passes checked={filter.blocked} to the p-checkbox custom element.
    // React 19 sets it as a DOM property (el.checked = true) not an attribute.
    // Current code uses aria-checked and does NOT set the checked property → FAILS.
    const { container } = renderPanel({ filter: { ...emptyFilter, blocked: true } })
    // Note: PDS name attr is not reflected as a DOM attribute in jsdom; use tag selector.
    const el = container.querySelector('p-checkbox') as (Element & { checked?: boolean }) | null
    expect(el, 'p-checkbox must be present in the filter panel').not.toBeNull()
    expect(el!.checked).toBe(true)
  })

  it('change CustomEvent with detail.checked=true fires onFilterChange with blocked: true', () => {
    // AC1: onChange handler (not onClick). PDS PCheckbox fires change CustomEvent with
    // CheckboxChangeEventDetail = { checked: boolean }.
    // Current code uses onClick — change CustomEvent bypasses it → FAILS.
    const onFilterChange = vi.fn()
    const { container } = renderPanel({ filter: emptyFilter, onFilterChange })
    const el = container.querySelector('p-checkbox') as HTMLElement | null
    expect(el, 'p-checkbox must be present in the filter panel').not.toBeNull()
    fireEvent(el!, new CustomEvent('change', { bubbles: true, detail: { checked: true } }))
    expect(onFilterChange).toHaveBeenCalledTimes(1)
    expect(onFilterChange).toHaveBeenCalledWith({ ...emptyFilter, blocked: true })
  })

  it('change CustomEvent with detail.checked=false fires onFilterChange with blocked: false', () => {
    // AC1: onChange toggle-off path. The handler reads e.detail.checked directly,
    // not !filter.blocked, so explicit false must produce blocked: false.
    // Current code uses onClick → change CustomEvent is not handled → FAILS.
    const onFilterChange = vi.fn()
    const { container } = renderPanel({
      filter: { ...emptyFilter, blocked: true },
      onFilterChange,
    })
    const el = container.querySelector('p-checkbox') as HTMLElement | null
    expect(el, 'p-checkbox must be present in the filter panel').not.toBeNull()
    fireEvent(el!, new CustomEvent('change', { bubbles: true, detail: { checked: false } }))
    expect(onFilterChange).toHaveBeenCalledTimes(1)
    expect(onFilterChange).toHaveBeenCalledWith({ ...emptyFilter, blocked: false })
  })

  it('blocked control has no aria-checked attribute (PCheckbox uses checked prop)', () => {
    // AC1 falsifiability guard: the raw <p-checkbox> web component set aria-checked as a React prop.
    // The PCheckbox React wrapper uses checked instead; aria-checked is NOT passed.
    // Current code sets aria-checked="true" → hasAttribute('aria-checked') is true → FAILS.
    const { container } = renderPanel({ filter: { ...emptyFilter, blocked: true } })
    const el = container.querySelector('p-checkbox')
    expect(el, 'p-checkbox must be present in the filter panel').not.toBeNull()
    expect(
      el!.hasAttribute('aria-checked'),
      'aria-checked must not be set by PCheckbox (deprecated raw web-component pattern)',
    ).toBe(false)
  })

  it('onChange fires onFilterChange preserving sibling fields when blocked toggles on', () => {
    // AC1: onChange handler must spread existing filter state.
    // Current code uses onClick → change CustomEvent bypasses handler → FAILS.
    const onFilterChange = vi.fn()
    const multiActive: FilterState = { text: 'search', priority: 'needed', tags: ['bug'], blocked: false }
    const { container } = renderPanel({ filter: multiActive, onFilterChange })
    const el = container.querySelector('p-checkbox') as HTMLElement | null
    expect(el, 'p-checkbox must be present in the filter panel').not.toBeNull()
    fireEvent(el!, new CustomEvent('change', { bubbles: true, detail: { checked: true } }))
    expect(onFilterChange).toHaveBeenCalledWith({
      text: 'search',
      priority: 'needed',
      tags: ['bug'],
      blocked: true,
    })
  })
})

// ─── AC2: PSelect uses PSelectOption children (not native <option>) ───────────

describe('TestFromAC_PSelectOption', () => {
  afterEach(() => {
    vi.resetAllMocks()
  })

  it('priority p-select contains at least one p-select-option child', () => {
    // AC2 positive: PSelectOption renders as <p-select-option> in jsdom.
    // Current code renders native <option> children, not <p-select-option> → FAILS.
    // Note: PDS name attr is not reflected as a DOM attribute in jsdom; use tag selector.
    const { container } = renderPanel({ priorities: PRIORITIES })
    const pSelect = container.querySelector('p-select')
    expect(pSelect, 'p-select must be present in the filter panel').not.toBeNull()
    expect(
      pSelect!.querySelector('p-select-option'),
      'p-select must contain at least one p-select-option child',
    ).not.toBeNull()
  })

  it('priority p-select contains p-select-option for each priority value', () => {
    // AC2: all priority values must map to PSelectOption children. A placeholder for
    // empty-value selection is allowed in addition.
    const custom = ['low', 'medium', 'high']
    const { container } = renderPanel({ priorities: custom })
    const pSelect = container.querySelector('p-select')
    expect(pSelect, 'p-select must be present in the filter panel').not.toBeNull()
    const optionEls = Array.from(pSelect!.querySelectorAll('p-select-option'))
    expect(optionEls.length).toBeGreaterThanOrEqual(custom.length)
  })

  it('priority p-select contains no native option elements (dual-render falsifiability)', () => {
    // AC2 falsifiability guard: a dual-render state (both p-select-option and native <option>)
    // would make the positive test above pass green while the contract is violated.
    // Current code renders native <option> children → nativeCount > 0 → FAILS.
    // Use el.children (raw DOM, not CSS engine) to count OPTION nodes.
    const { container } = renderPanel({ priorities: PRIORITIES })
    const pSelect = container.querySelector('p-select')
    expect(pSelect, 'p-select must be present in the filter panel').not.toBeNull()
    const nativeCount = Array.from(pSelect!.children).filter((c) => c.tagName === 'OPTION').length
    expect(nativeCount).toBe(0)
  })

  it('each p-select-option child carries the correct priority value attribute', () => {
    // AC2: PSelectOption value prop must match the priority string.
    const custom = ['low', 'high']
    const { container } = renderPanel({ priorities: custom })
    const pSelect = container.querySelector('p-select')
    expect(pSelect, 'p-select must be present in the filter panel').not.toBeNull()
    const opts = Array.from(pSelect!.querySelectorAll('p-select-option'))
    // Map to value attribute or DOM property.
    const values = opts.map(
      (o) => o.getAttribute('value') ?? (o as Element & { value?: unknown }).value,
    )
    for (const p of custom) {
      expect(values, `p-select-option with value="${p}" must be present`).toContain(p)
    }
  })
})

// ─── AC3: .filter-panel flex layout CSS declarations ─────────────────────────

describe('TestFromAC_FilterPanelFlexLayout', () => {
  it('FilterPanel.css declares display: flex inside the .filter-panel selector block', () => {
    // AC3: horizontal flex layout required. Current CSS has only background/border/padding → FAILS.
    const css = fs.readFileSync(FILTER_PANEL_CSS, 'utf-8')
    expect(
      /\.filter-panel\s*\{[^}]*display\s*:\s*flex/s.test(css),
      '.filter-panel CSS block must contain display: flex',
    ).toBe(true)
  })

  it('FilterPanel.css declares flex-wrap: wrap inside the .filter-panel selector block', () => {
    // AC3: wrap allows controls to flow to a second line on narrow viewports.
    // Current CSS has no flex-wrap declaration → FAILS.
    const css = fs.readFileSync(FILTER_PANEL_CSS, 'utf-8')
    expect(
      /\.filter-panel\s*\{[^}]*flex-wrap\s*:\s*wrap/s.test(css),
      '.filter-panel CSS block must contain flex-wrap: wrap',
    ).toBe(true)
  })

  it('FilterPanel.css declares gap: var(--pds-spacing-sm) inside the .filter-panel selector block', () => {
    // AC3: PDS token-based spacing between filter controls.
    // Current CSS has no gap declaration → FAILS.
    const css = fs.readFileSync(FILTER_PANEL_CSS, 'utf-8')
    expect(
      /\.filter-panel\s*\{[^}]*gap\s*:\s*var\(--pds-spacing-sm\)/s.test(css),
      '.filter-panel CSS block must contain gap: var(--pds-spacing-sm)',
    ).toBe(true)
  })

  it('FilterPanel.css declares align-items: flex-end inside the .filter-panel selector block', () => {
    // AC3: baseline alignment so controls of different heights align to their bottom edge.
    // Current CSS has no align-items declaration → FAILS.
    const css = fs.readFileSync(FILTER_PANEL_CSS, 'utf-8')
    expect(
      /\.filter-panel\s*\{[^}]*align-items\s*:\s*flex-end/s.test(css),
      '.filter-panel CSS block must contain align-items: flex-end',
    ).toBe(true)
  })
})
