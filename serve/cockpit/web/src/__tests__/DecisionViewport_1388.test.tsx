/**
 * RED phase tests for #1388: P2-13 Test Cockpit decision viewport UX
 *
 * Covers AC1, AC4 (PDS / viewport structure), AC5 (keyboard reachability),
 * and AC6 (viewport-level error indicator).
 *
 * All tests FAIL because DecisionViewport does not yet exist.
 * Import error is valid RED evidence for new-file tasks (test-writer discipline).
 *
 * Builder counterpart: #1389.
 */
import { describe, it, expect, vi } from 'vitest'
import { render, fireEvent } from '@testing-library/react'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'
import type { PendingDR } from '../hooks/usePendingDRs'

// ─── Component under test (does not exist yet — RED phase) ───────────────────
import DecisionViewport from '../components/DecisionViewport'

// ─── Fixtures ─────────────────────────────────────────────────────────────────

const DR_A: PendingDR = {
  id: 'dr-vp-001',
  task_id: 42,
  agent: 'builder',
  request_type: 'scope-decision',
  created: new Date(Date.now() - 3 * 3_600_000).toISOString(), // 3 h ago
  title: 'Should we refactor the cache layer?',
  // body_preview is NOT a substring of body — discriminating fixture (AC1)
  body: '## Context\n\nThe cache layer has grown too complex. Multiple refactors are planned.',
  body_preview: 'Consider architectural simplification for long-term maintainability.',
}

const DR_B: PendingDR = {
  id: 'dr-vp-002',
  task_id: 99,
  agent: 'architect',
  request_type: 'user-action',
  created: new Date(Date.now() - 25 * 3_600_000).toISOString(), // 25 h ago
  title: 'Confirm scope change for phase 2',
  // body_preview is NOT a substring of body — discriminating fixture (AC1)
  body: '## Scope\n\nPhase 2 scope needs confirmation from the product owner.',
  body_preview: 'Confirm the feature boundary before implementation begins.',
}

// ─── Render helper ────────────────────────────────────────────────────────────

function renderViewport({
  items = [] as PendingDR[],
  isLoading = false,
  error = null as Error | null,
  onItemClick = vi.fn(),
} = {}) {
  return render(
    <PorscheDesignSystemProvider>
      <DecisionViewport
        items={items}
        isLoading={isLoading}
        error={error}
        onItemClick={onItemClick}
      />
    </PorscheDesignSystemProvider>,
  )
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('TestFromAC_DecisionViewport', () => {
  // ─── AC1 (td:2): Component export ─────────────────────────────────────────

  it('DecisionViewport is exported as a default function component', () => {
    expect(typeof DecisionViewport).toBe('function')
  })

  // ─── AC1 (td:2): Loading state ────────────────────────────────────────────

  it('renders a loading indicator when isLoading is true', () => {
    const { container } = renderViewport({ isLoading: true })
    const loading = container.querySelector('[data-testid="decision-loading"]')
    expect(loading).not.toBeNull()
  })

  it('loading indicator has non-empty text or aria-label to announce state', () => {
    const { container } = renderViewport({ isLoading: true })
    const loading = container.querySelector('[data-testid="decision-loading"]')!
    const accessible =
      (loading.textContent?.trim().length ?? 0) > 0 ||
      loading.hasAttribute('aria-label') ||
      loading.hasAttribute('role')
    expect(accessible).toBe(true)
  })

  it('does not render item list when loading', () => {
    const { container } = renderViewport({ isLoading: true, items: [DR_A] })
    // Items should not appear while loading to prevent flicker/partial data
    expect(container.querySelector('[data-testid="decision-item-dr-vp-001"]')).toBeNull()
  })

  // ─── AC1 (td:2): Error state ─────────────────────────────────────────────

  it('renders a user-visible error indicator when error is provided', () => {
    const { container } = renderViewport({ error: new Error('Polling failed') })
    const errEl = container.querySelector('[data-testid="decision-error"]')
    expect(errEl).not.toBeNull()
  })

  it('error indicator surfaces the error message content', () => {
    const { container } = renderViewport({ error: new Error('Decision service unavailable') })
    const errEl = container.querySelector('[data-testid="decision-error"]')!
    expect(errEl.textContent).toContain('Decision service unavailable')
  })

  it('error indicator is distinct from the loading indicator', () => {
    const { container } = renderViewport({ error: new Error('500') })
    expect(container.querySelector('[data-testid="decision-loading"]')).toBeNull()
    expect(container.querySelector('[data-testid="decision-error"]')).not.toBeNull()
  })

  // ─── AC1 (td:2): Empty state ──────────────────────────────────────────────

  it('renders a distinct empty-state indicator when there are no items and no error', () => {
    const { container } = renderViewport({ items: [], isLoading: false, error: null })
    const empty = container.querySelector('[data-testid="decision-empty"]')
    expect(empty).not.toBeNull()
  })

  it('empty state has non-empty visible text', () => {
    const { container } = renderViewport({ items: [] })
    const empty = container.querySelector('[data-testid="decision-empty"]')!
    expect(empty.textContent?.trim().length).toBeGreaterThan(0)
  })

  it('does not render loading indicator in empty state', () => {
    const { container } = renderViewport({ items: [], isLoading: false })
    expect(container.querySelector('[data-testid="decision-loading"]')).toBeNull()
  })

  // ─── AC1 (td:2): Item rendering — task-id clickable reference ─────────────

  it('renders a clickable task-id reference for each item', () => {
    const { container } = renderViewport({ items: [DR_A] })
    const ref = container.querySelector('[data-testid="decision-task-ref-dr-vp-001"]')
    expect(ref).not.toBeNull()
  })

  it('task-id reference displays the task_id value', () => {
    const { container } = renderViewport({ items: [DR_A] })
    const ref = container.querySelector('[data-testid="decision-task-ref-dr-vp-001"]')!
    expect(ref.textContent).toContain('42')
  })

  it('task-id reference is a clickable element (button or link)', () => {
    const { container } = renderViewport({ items: [DR_A] })
    const ref = container.querySelector('[data-testid="decision-task-ref-dr-vp-001"]')!
    const tag = ref.tagName.toLowerCase()
    const role = ref.getAttribute('role')?.toLowerCase()
    const isClickable = tag === 'button' || tag === 'a' || role === 'button' || role === 'link'
    expect(isClickable).toBe(true)
  })

  // ─── AC1 (td:2): Item rendering — agent and request_type ─────────────────

  it('renders agent field for each item', () => {
    const { container } = renderViewport({ items: [DR_A] })
    const item = container.querySelector('[data-testid="decision-item-dr-vp-001"]')!
    expect(item).not.toBeNull()
    expect(item.textContent).toContain(DR_A.agent)
  })

  it('renders request_type field for each item', () => {
    const { container } = renderViewport({ items: [DR_A] })
    const item = container.querySelector('[data-testid="decision-item-dr-vp-001"]')!
    expect(item.textContent).toContain(DR_A.request_type)
  })

  // ─── AC1 (td:2): Item rendering — age ─────────────────────────────────────
  // AC1 requires age rendered in a dedicated data-testid="decision-age-{id}" element.
  // Reading from whole-item textContent is not discriminating (other fields differ too).

  it('renders a non-empty age string in a dedicated decision-age-{id} element', () => {
    const { container } = renderViewport({ items: [DR_A] })
    const ageEl = container.querySelector('[data-testid="decision-age-dr-vp-001"]')
    expect(ageEl).not.toBeNull()
    expect(ageEl!.textContent?.trim().length).toBeGreaterThan(0)
  })

  it('age string differs between items with different created timestamps (read from dedicated age elements)', () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-05-08T12:00:00.000Z'))
    const recent: PendingDR = { ...DR_A, id: 'dr-recent', created: '2026-05-08T11:00:00.000Z' } // 1h
    const old: PendingDR = { ...DR_B, id: 'dr-old', created: '2026-05-07T12:00:00.000Z' } // 24h
    try {
      const { container } = renderViewport({ items: [recent, old] })
      const recentAge = container.querySelector('[data-testid="decision-age-dr-recent"]')?.textContent ?? ''
      const oldAge = container.querySelector('[data-testid="decision-age-dr-old"]')?.textContent ?? ''
      // Dedicated age elements must show different text — not whole-item textContent (discriminating proof)
      expect(recentAge).not.toBe(oldAge)
    } finally {
      vi.useRealTimers()
    }
  })

  // ─── AC1 (td:2): Item rendering — body_preview ───────────────────────────

  it('renders body_preview for each item', () => {
    const { container } = renderViewport({ items: [DR_A] })
    const item = container.querySelector('[data-testid="decision-item-dr-vp-001"]')!
    expect(item.textContent).toContain(DR_A.body_preview)
  })

  // ─── AC1 (td:2): Multiple items ──────────────────────────────────────────

  it('renders all items when multiple decisions are pending', () => {
    const { container } = renderViewport({ items: [DR_A, DR_B] })
    expect(container.querySelector('[data-testid="decision-item-dr-vp-001"]')).not.toBeNull()
    expect(container.querySelector('[data-testid="decision-item-dr-vp-002"]')).not.toBeNull()
  })

  it('each item renders its own task-id reference', () => {
    const { container } = renderViewport({ items: [DR_A, DR_B] })
    expect(container.querySelector('[data-testid="decision-task-ref-dr-vp-001"]')).not.toBeNull()
    expect(container.querySelector('[data-testid="decision-task-ref-dr-vp-002"]')).not.toBeNull()
  })

  // ─── AC1 (td:2): onItemClick callback fires from task-id reference ──────────
  // AC1 requires onItemClick fires when the task-id reference element is clicked
  // (not just any click on the item container).

  it('calls onItemClick with item id when task-id reference element is clicked', () => {
    const onItemClick = vi.fn()
    const { container } = renderViewport({ items: [DR_A], onItemClick })
    const taskRef = container.querySelector('[data-testid="decision-task-ref-dr-vp-001"]')!
    expect(taskRef).not.toBeNull()
    fireEvent.click(taskRef)
    expect(onItemClick).toHaveBeenCalledWith('dr-vp-001')
  })

  // ─── AC4 (td:1): PDS components used ─────────────────────────────────────

  it('viewport structure includes at least one PDS component (p-* element)', () => {
    const { container } = renderViewport({ items: [DR_A] })
    const pdsElements = container.querySelectorAll('[class*="p-"], p-button, p-text, p-heading, p-spinner, p-icon, p-inline-notification, p-tag')
    // At least one PDS component must be present
    expect(pdsElements.length).toBeGreaterThan(0)
  })

  // ─── AC5 (td:2): Decision list items are keyboard-reachable ──────────────

  it('each decision item is reachable via keyboard (button semantics)', () => {
    const { container } = renderViewport({ items: [DR_A, DR_B] })
    const items = container.querySelectorAll('[data-testid^="decision-item-"]')
    expect(items.length).toBe(2)
    for (const item of Array.from(items)) {
      const tag = item.tagName.toLowerCase()
      const role = item.getAttribute('role')?.toLowerCase()
      // Item must be focusable: either a <button>, <a>, or have role=button/link
      const isFocusable = tag === 'button' || tag === 'a' || role === 'button' || role === 'link'
      expect(isFocusable).toBe(true)
    }
  })

  it('decision-item elements have no tabindex=-1 — both focusable semantics AND tab-reachability on the same element', () => {
    // AC5 requires both assertions on the same decision-item-* element (not split across task-ref)
    const { container } = renderViewport({ items: [DR_A, DR_B] })
    const items = container.querySelectorAll('[data-testid^="decision-item-"]')
    expect(items.length).toBe(2)
    for (const item of Array.from(items)) {
      expect(item.getAttribute('tabindex')).not.toBe('-1')
    }
  })

  // ─── AC6 (td:1): Viewport-level error is user-visible ────────────────────

  it('viewport error indicator has a visible role for screen readers (role=alert or status)', () => {
    const { container } = renderViewport({ error: new Error('Backend unreachable') })
    const errEl = container.querySelector('[data-testid="decision-error"]')!
    const role = errEl.getAttribute('role')
    expect(['alert', 'status']).toContain(role)
  })
})
