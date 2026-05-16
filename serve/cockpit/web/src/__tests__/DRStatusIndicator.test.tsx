/**
 * DRStatusIndicator component
 *
 * Covers: pending DR count rendering, attention/dormant status attribute,
 * popover toggle on indicator click, popover item fields (title, agent,
 * task_id, age), item click callback, and empty-state (dormant) behavior.
 */
import { describe, it, expect, vi } from 'vitest'
import { render, fireEvent } from '@testing-library/react'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'
import DRStatusIndicator from '../components/DRStatusIndicator'

// ─── Fixtures ─────────────────────────────────────────────────────────────────

interface PendingDR {
  id: string
  task_id: number
  agent: string
  request_type: string
  created: string
  title: string
  body_preview: string
}

const DR_A: PendingDR = {
  id: 'dr-001',
  task_id: 42,
  agent: 'builder',
  request_type: 'scope-decision',
  created: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
  title: 'Should we use approach A?',
  body_preview: 'Context: the builder encountered a fork in the road...',
}

const DR_B: PendingDR = {
  id: 'dr-002',
  task_id: 99,
  agent: 'researcher',
  request_type: 'user-action',
  created: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
  title: 'Confirm scope change',
  body_preview: 'Researcher requests user confirmation of revised scope...',
}

// ─── Render helper ─────────────────────────────────────────────────────────────

function renderIndicator(
  count: number,
  items: PendingDR[],
  onItemClick = vi.fn(),
) {
  return render(
    <PorscheDesignSystemProvider>
      <DRStatusIndicator count={count} items={items} onItemClick={onItemClick} />
    </PorscheDesignSystemProvider>,
  )
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('TestFromAC_DRStatusIndicator', () => {
  // ─── AC: is exported as a default component ────────────────────────────────

  it('is exported as a default function component', () => {
    expect(typeof DRStatusIndicator).toBe('function')
  })

  // ─── AC: Test StatusBarIndicator renders pending DR count ─────────────────

  it('renders element with data-testid="dr-indicator"', () => {
    const { container } = renderIndicator(0, [])
    expect(container.querySelector('[data-testid="dr-indicator"]')).not.toBeNull()
  })

  it('renders the pending count in the indicator text when count is 1', () => {
    const { container } = renderIndicator(1, [DR_A])
    const indicator = container.querySelector('[data-testid="dr-indicator"]')!
    expect(indicator.textContent).toContain('1')
  })

  it('renders the pending count in the indicator text when count is 2', () => {
    const { container } = renderIndicator(2, [DR_A, DR_B])
    const indicator = container.querySelector('[data-testid="dr-indicator"]')!
    expect(indicator.textContent).toContain('2')
  })

  // ─── AC: Test indicator uses attention color when count > 0, dormant when count = 0 ───

  it('sets data-status="attention" when count > 0 (single DR)', () => {
    const { container } = renderIndicator(1, [DR_A])
    const indicator = container.querySelector('[data-testid="dr-indicator"]')!
    expect(indicator.getAttribute('data-status')).toBe('attention')
  })

  it('sets data-status="attention" when count > 0 (multiple DRs)', () => {
    const { container } = renderIndicator(2, [DR_A, DR_B])
    const indicator = container.querySelector('[data-testid="dr-indicator"]')!
    expect(indicator.getAttribute('data-status')).toBe('attention')
  })

  it('sets data-status="dormant" when count = 0', () => {
    const { container } = renderIndicator(0, [])
    const indicator = container.querySelector('[data-testid="dr-indicator"]')!
    expect(indicator.getAttribute('data-status')).toBe('dormant')
  })

  // ─── AC: Test empty state (0 pending) renders dormant indicator ────────────

  it('renders dormant indicator for empty state with zero items', () => {
    const { container } = renderIndicator(0, [])
    const indicator = container.querySelector('[data-testid="dr-indicator"]')!
    expect(indicator.getAttribute('data-status')).toBe('dormant')
  })

  it('does not render popover before indicator is clicked (empty state)', () => {
    const { container } = renderIndicator(0, [])
    expect(container.querySelector('[data-testid="dr-popover"]')).toBeNull()
  })

  // ─── AC: Test indicator click opens popover ────────────────────────────────

  it('does not render popover before indicator is clicked', () => {
    const { container } = renderIndicator(1, [DR_A])
    expect(container.querySelector('[data-testid="dr-popover"]')).toBeNull()
  })

  it('opens popover when indicator is clicked', () => {
    const { container } = renderIndicator(1, [DR_A])
    const indicator = container.querySelector('[data-testid="dr-indicator"]')!
    fireEvent.click(indicator)
    expect(container.querySelector('[data-testid="dr-popover"]')).not.toBeNull()
  })

  it('closes popover on second click of indicator (toggle behavior)', () => {
    const { container } = renderIndicator(1, [DR_A])
    const indicator = container.querySelector('[data-testid="dr-indicator"]')!
    fireEvent.click(indicator)
    fireEvent.click(indicator)
    expect(container.querySelector('[data-testid="dr-popover"]')).toBeNull()
  })

  it('popover does not show item content before indicator is clicked', () => {
    const { container } = renderIndicator(1, [DR_A])
    expect(container.textContent).not.toContain(DR_A.title)
  })

  // ─── AC: Test popover list renders DR items: title, agent, task_id, age ───

  it('popover shows title of each DR item after click', () => {
    const { container } = renderIndicator(1, [DR_A])
    fireEvent.click(container.querySelector('[data-testid="dr-indicator"]')!)
    expect(container.textContent).toContain(DR_A.title)
  })

  it('popover shows agent of each DR item after click', () => {
    const { container } = renderIndicator(1, [DR_A])
    fireEvent.click(container.querySelector('[data-testid="dr-indicator"]')!)
    expect(container.textContent).toContain(DR_A.agent)
  })

  it('popover shows task_id of each DR item after click', () => {
    const { container } = renderIndicator(1, [DR_A])
    fireEvent.click(container.querySelector('[data-testid="dr-indicator"]')!)
    expect(container.textContent).toContain(String(DR_A.task_id))
  })

  it('popover shows a non-empty age string derived from created timestamp', () => {
    const { container } = renderIndicator(1, [DR_A])
    fireEvent.click(container.querySelector('[data-testid="dr-indicator"]')!)
    const popover = container.querySelector('[data-testid="dr-popover"]')!
    // Age is computed from created — must render some non-empty string
    expect(popover.textContent?.trim().length).toBeGreaterThan(0)
  })

  // ─── AC8: age field renders specific formatted text with frozen clock ──────
  // The assertion above is preserved for backwards compatibility; this test
  // provides a stronger item-specific, time-stable proof that fails when the
  // age <span> is removed or formatAge produces the wrong output.

  it('popover item renders the exact computed age text when clock is frozen (AC8)', () => {
    // Freeze Date.now() so formatAge returns a deterministic value.
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-04-30T12:00:00.000Z'))
    const drAgeProbe: PendingDR = {
      id: 'dr-age-probe',
      task_id: 77,
      agent: 'tester',
      request_type: 'scope-decision',
      created: '2026-04-30T10:00:00.000Z', // exactly 2 h before frozen "now"
      title: 'Age probe title',
      body_preview: '',
    }
    try {
      const { container } = renderIndicator(1, [drAgeProbe])
      fireEvent.click(container.querySelector('[data-testid="dr-indicator"]')!)
      const item = container.querySelector('[data-testid="dr-item-dr-age-probe"]')!
      expect(item).not.toBeNull()
      // title='Age probe title', agent='tester', task_id='77' — none contains '2h ago'.
      // This assertion fails if the age span is removed or formatAge is broken.
      expect(item.textContent).toContain('2h ago')
    } finally {
      vi.useRealTimers()
    }
  })

  it('each popover item has data-testid="dr-item-{id}"', () => {
    const { container } = renderIndicator(1, [DR_A])
    fireEvent.click(container.querySelector('[data-testid="dr-indicator"]')!)
    expect(container.querySelector(`[data-testid="dr-item-${DR_A.id}"]`)).not.toBeNull()
  })

  it('popover shows all fields for all items when multiple DRs present', () => {
    const { container } = renderIndicator(2, [DR_A, DR_B])
    fireEvent.click(container.querySelector('[data-testid="dr-indicator"]')!)
    expect(container.textContent).toContain(DR_A.title)
    expect(container.textContent).toContain(DR_A.agent)
    expect(container.textContent).toContain(String(DR_A.task_id))
    expect(container.textContent).toContain(DR_B.title)
    expect(container.textContent).toContain(DR_B.agent)
    expect(container.textContent).toContain(String(DR_B.task_id))
  })

  it('renders item elements for both DRs when two are present', () => {
    const { container } = renderIndicator(2, [DR_A, DR_B])
    fireEvent.click(container.querySelector('[data-testid="dr-indicator"]')!)
    expect(container.querySelector(`[data-testid="dr-item-${DR_A.id}"]`)).not.toBeNull()
    expect(container.querySelector(`[data-testid="dr-item-${DR_B.id}"]`)).not.toBeNull()
  })

  // ─── AC: Test popover item click triggers navigation/modal open ────────────

  it('calls onItemClick with the DR id when a popover item is clicked', () => {
    const onItemClick = vi.fn()
    const { container } = renderIndicator(1, [DR_A], onItemClick)
    fireEvent.click(container.querySelector('[data-testid="dr-indicator"]')!)
    const item = container.querySelector(`[data-testid="dr-item-${DR_A.id}"]`)!
    fireEvent.click(item)
    expect(onItemClick).toHaveBeenCalledOnce()
    expect(onItemClick).toHaveBeenCalledWith(DR_A.id)
  })

  it('calls onItemClick with correct id when second item is clicked in multi-item list', () => {
    const onItemClick = vi.fn()
    const { container } = renderIndicator(2, [DR_A, DR_B], onItemClick)
    fireEvent.click(container.querySelector('[data-testid="dr-indicator"]')!)
    const item = container.querySelector(`[data-testid="dr-item-${DR_B.id}"]`)!
    fireEvent.click(item)
    expect(onItemClick).toHaveBeenCalledWith(DR_B.id)
  })

  it('renders without error inside PorscheDesignSystemProvider (empty state)', () => {
    expect(() => renderIndicator(0, [])).not.toThrow()
  })

  it('renders without error inside PorscheDesignSystemProvider (with items)', () => {
    expect(() => renderIndicator(1, [DR_A])).not.toThrow()
  })
})
