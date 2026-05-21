/**
 * HealthBadge component
 *
 * Covers: green/red indicator states, issue count text, popover toggle,
 * popover item fields, aria-label contract, data-testid, and default export.
 *
 */
import { describe, it, expect } from 'vitest'
import { render, fireEvent } from '@testing-library/react'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'
import HealthBadge from '../components/HealthBadge'

// Fixtures

interface ScanItem {
  code: string
  detail: string
  file_path: string
}

const ITEM_A: ScanItem = {
  code: 'E001',
  detail: 'Missing required field',
  file_path: 'src/models/task.py',
}

const ITEM_B: ScanItem = {
  code: 'W042',
  detail: 'Unused import detected',
  file_path: 'serve/kanban/src/engine.py',
}

// Render helper

function renderBadge(items: ScanItem[]) {
  return render(
    <PorscheDesignSystemProvider>
      <HealthBadge items={items} />
    </PorscheDesignSystemProvider>,
  )
}

describe('TestFromAC_HealthBadge', () => {
  it('is exported as a default function component', () => {
    expect(typeof HealthBadge).toBe('function')
  })

  it('renders element with data-testid="health-badge"', () => {
    const { container } = renderBadge([])
    expect(container.querySelector('[data-testid="health-badge"]')).not.toBeNull()
  })

  it('renders data-testid="health-badge" when items are present', () => {
    const { container } = renderBadge([ITEM_A])
    expect(container.querySelector('[data-testid="health-badge"]')).not.toBeNull()
  })

  it('sets data-health="green" when items is empty', () => {
    const { container } = renderBadge([])
    const badge = container.querySelector('[data-testid="health-badge"]')
    expect(badge?.getAttribute('data-health')).toBe('green')
  })

  it('sets data-health="red" when items is non-empty (single item)', () => {
    const { container } = renderBadge([ITEM_A])
    const badge = container.querySelector('[data-testid="health-badge"]')
    expect(badge?.getAttribute('data-health')).toBe('red')
  })

  it('sets data-health="red" when items is non-empty (multiple items)', () => {
    const { container } = renderBadge([ITEM_A, ITEM_B])
    const badge = container.querySelector('[data-testid="health-badge"]')
    expect(badge?.getAttribute('data-health')).toBe('red')
  })

  it('sets aria-label to "Workspace status: OK" when items is empty', () => {
    const { container } = renderBadge([])
    const badge = container.querySelector('[data-testid="health-badge"]')
    expect(badge?.getAttribute('aria-label')).toBe('Workspace status: OK')
  })

  it('sets aria-label to "Workspace status: 1 issues" when items has 1 element', () => {
    const { container } = renderBadge([ITEM_A])
    const badge = container.querySelector('[data-testid="health-badge"]')
    expect(badge?.getAttribute('aria-label')).toBe('Workspace status: 1 issues')
  })

  it('sets aria-label to "Workspace status: 2 issues" when items has 2 elements', () => {
    const { container } = renderBadge([ITEM_A, ITEM_B])
    const badge = container.querySelector('[data-testid="health-badge"]')
    expect(badge?.getAttribute('aria-label')).toBe('Workspace status: 2 issues')
  })

  it('reflects exact item count in aria-label for large N', () => {
    const fiveItems = Array.from({ length: 5 }, (_, i) => ({
      code: `E00${i}`,
      detail: `Issue ${i}`,
      file_path: `file_${i}.py`,
    }))
    const { container } = renderBadge(fiveItems)
    const badge = container.querySelector('[data-testid="health-badge"]')
    expect(badge?.getAttribute('aria-label')).toBe('Workspace status: 5 issues')
  })

  it('shows issue count text when items is non-empty', () => {
    const { container } = renderBadge([ITEM_A, ITEM_B])
    const badge = container.querySelector('[data-testid="health-badge"]')
    expect(badge?.textContent).toMatch(/2/)
  })

  it('does not render popover before badge is clicked', () => {
    const { container } = renderBadge([ITEM_A])
    expect(container.querySelector('[data-testid="health-badge-popover"]')).toBeNull()
  })

  it('opens popover when badge is clicked', () => {
    const { container } = renderBadge([ITEM_A])
    const badge = container.querySelector('[data-testid="health-badge"]')!
    fireEvent.click(badge)
    expect(container.querySelector('[data-testid="health-badge-popover"]')).not.toBeNull()
  })

  it('closes popover on second click of badge', () => {
    const { container } = renderBadge([ITEM_A])
    const badge = container.querySelector('[data-testid="health-badge"]')!
    fireEvent.click(badge)
    fireEvent.click(badge)
    expect(container.querySelector('[data-testid="health-badge-popover"]')).toBeNull()
  })

  it('popover does not show item content before badge is clicked', () => {
    const { container } = renderBadge([ITEM_A])
    expect(container.textContent).not.toContain(ITEM_A.file_path)
  })

  it('popover shows file_path of each item after click', () => {
    const { container } = renderBadge([ITEM_A])
    fireEvent.click(container.querySelector('[data-testid="health-badge"]')!)
    expect(container.textContent).toContain(ITEM_A.file_path)
  })

  it('popover shows code of each item after click', () => {
    const { container } = renderBadge([ITEM_A])
    fireEvent.click(container.querySelector('[data-testid="health-badge"]')!)
    expect(container.textContent).toContain(ITEM_A.code)
  })

  it('popover shows detail of each item after click', () => {
    const { container } = renderBadge([ITEM_A])
    fireEvent.click(container.querySelector('[data-testid="health-badge"]')!)
    expect(container.textContent).toContain(ITEM_A.detail)
  })

  it('popover shows all three fields for all items when multiple present', () => {
    const { container } = renderBadge([ITEM_A, ITEM_B])
    fireEvent.click(container.querySelector('[data-testid="health-badge"]')!)
    expect(container.textContent).toContain(ITEM_A.file_path)
    expect(container.textContent).toContain(ITEM_A.code)
    expect(container.textContent).toContain(ITEM_A.detail)
    expect(container.textContent).toContain(ITEM_B.file_path)
    expect(container.textContent).toContain(ITEM_B.code)
    expect(container.textContent).toContain(ITEM_B.detail)
  })

  it('renders without error inside PorscheDesignSystemProvider', () => {
    expect(() => renderBadge([])).not.toThrow()
    expect(() => renderBadge([ITEM_A])).not.toThrow()
  })

  it('shows exact text "1 issues" for single item (not regex match)', () => {
    const { container } = renderBadge([ITEM_A])
    const badge = container.querySelector('[data-testid="health-badge"]')!
    expect(badge.textContent).toContain('1 issues')
  })

  it('shows exact text "2 issues" for two items (not regex match)', () => {
    const { container } = renderBadge([ITEM_A, ITEM_B])
    const badge = container.querySelector('[data-testid="health-badge"]')!
    expect(badge.textContent).toContain('2 issues')
  })

  it('does not show "0 issues" text when items is empty', () => {
    const { container } = renderBadge([])
    const badge = container.querySelector('[data-testid="health-badge"]')!
    expect(badge.textContent).not.toContain('0 issues')
  })

  it('popover element (not full container) shows file_path after click', () => {
    const { container } = renderBadge([ITEM_A])
    fireEvent.click(container.querySelector('[data-testid="health-badge"]')!)
    const popover = container.querySelector('[data-testid="health-badge-popover"]')
    expect(popover).not.toBeNull()
    expect(popover!.textContent).toContain(ITEM_A.file_path)
  })

  it('popover element (not full container) shows code after click', () => {
    const { container } = renderBadge([ITEM_A])
    fireEvent.click(container.querySelector('[data-testid="health-badge"]')!)
    const popover = container.querySelector('[data-testid="health-badge-popover"]')!
    expect(popover.textContent).toContain(ITEM_A.code)
  })

  it('popover element (not full container) shows detail after click', () => {
    const { container } = renderBadge([ITEM_A])
    fireEvent.click(container.querySelector('[data-testid="health-badge"]')!)
    const popover = container.querySelector('[data-testid="health-badge-popover"]')!
    expect(popover.textContent).toContain(ITEM_A.detail)
  })

  it('popover scoped to [data-testid="health-badge-popover"] shows all fields for multiple items', () => {
    const { container } = renderBadge([ITEM_A, ITEM_B])
    fireEvent.click(container.querySelector('[data-testid="health-badge"]')!)
    const popover = container.querySelector('[data-testid="health-badge-popover"]')!
    expect(popover.textContent).toContain(ITEM_A.file_path)
    expect(popover.textContent).toContain(ITEM_A.code)
    expect(popover.textContent).toContain(ITEM_A.detail)
    expect(popover.textContent).toContain(ITEM_B.file_path)
    expect(popover.textContent).toContain(ITEM_B.code)
    expect(popover.textContent).toContain(ITEM_B.detail)
  })

  it('each item in popover is in a distinct list row (li element)', () => {
    const { container } = renderBadge([ITEM_A, ITEM_B])
    fireEvent.click(container.querySelector('[data-testid="health-badge"]')!)
    const popover = container.querySelector('[data-testid="health-badge-popover"]')!
    expect(popover.querySelectorAll('li')).toHaveLength(2)
  })

  it('opens popover when badge clicked with items empty', () => {
    const { container } = renderBadge([])
    fireEvent.click(container.querySelector('[data-testid="health-badge"]')!)
    expect(container.querySelector('[data-testid="health-badge-popover"]')).not.toBeNull()
  })

  it('empty-state popover contains no list rows when items is empty', () => {
    const { container } = renderBadge([])
    fireEvent.click(container.querySelector('[data-testid="health-badge"]')!)
    const popover = container.querySelector('[data-testid="health-badge-popover"]')!
    expect(popover.querySelectorAll('li')).toHaveLength(0)
  })

  it('empty-state popover shows non-empty text content when items is empty', () => {
    const { container } = renderBadge([])
    fireEvent.click(container.querySelector('[data-testid="health-badge"]')!)
    const popover = container.querySelector('[data-testid="health-badge-popover"]')!
    expect(popover.textContent?.trim().length).toBeGreaterThan(0)
  })

  it('badge textContent is exactly "Workspace OK" when items is empty (exact toBe)', () => {
    const { container } = renderBadge([])
    const badge = container.querySelector('[data-testid="health-badge"]')!
    expect(badge.textContent).toBe('Workspace OK')
  })

  it('badge textContent is exactly "Workspace 1 issues" for single item (exact toBe)', () => {
    const { container } = renderBadge([ITEM_A])
    const badge = container.querySelector('[data-testid="health-badge"]')!
    expect(badge.textContent).toBe('Workspace 1 issues')
  })

  it('badge textContent is exactly "Workspace 2 issues" for two items (exact toBe)', () => {
    const { container } = renderBadge([ITEM_A, ITEM_B])
    const badge = container.querySelector('[data-testid="health-badge"]')!
    expect(badge.textContent).toBe('Workspace 2 issues')
  })

  it('first list row textContent contains ITEM_A file_path, code, and detail (per-row)', () => {
    const { container } = renderBadge([ITEM_A, ITEM_B])
    fireEvent.click(container.querySelector('[data-testid="health-badge"]')!)
    const popover = container.querySelector('[data-testid="health-badge-popover"]')!
    const rows = popover.querySelectorAll('li')
    expect(rows[0].textContent).toContain(ITEM_A.file_path)
    expect(rows[0].textContent).toContain(ITEM_A.code)
    expect(rows[0].textContent).toContain(ITEM_A.detail)
  })

  it('second list row textContent contains ITEM_B file_path, code, and detail (per-row)', () => {
    const { container } = renderBadge([ITEM_A, ITEM_B])
    fireEvent.click(container.querySelector('[data-testid="health-badge"]')!)
    const popover = container.querySelector('[data-testid="health-badge-popover"]')!
    const rows = popover.querySelectorAll('li')
    expect(rows[1].textContent).toContain(ITEM_B.file_path)
    expect(rows[1].textContent).toContain(ITEM_B.code)
    expect(rows[1].textContent).toContain(ITEM_B.detail)
  })

  it('each list row contains only its own item fields - no cross-row field leakage', () => {
    const { container } = renderBadge([ITEM_A, ITEM_B])
    fireEvent.click(container.querySelector('[data-testid="health-badge"]')!)
    const popover = container.querySelector('[data-testid="health-badge-popover"]')!
    const rows = popover.querySelectorAll('li')
    expect(rows[0].textContent).not.toContain(ITEM_B.file_path)
    expect(rows[0].textContent).not.toContain(ITEM_B.code)
    expect(rows[0].textContent).not.toContain(ITEM_B.detail)
    expect(rows[1].textContent).not.toContain(ITEM_A.file_path)
    expect(rows[1].textContent).not.toContain(ITEM_A.code)
    expect(rows[1].textContent).not.toContain(ITEM_A.detail)
  })
})
