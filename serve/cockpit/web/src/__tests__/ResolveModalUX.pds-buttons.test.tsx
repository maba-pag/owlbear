/**
 * v2: AC4 — PButton controls in ResolveModal
 *
 * AC4 (td:2): ResolveModal submit and cancel controls use <PButton> (not raw
 * <button>): submit with variant="primary", cancel with variant="secondary".
 *
 * All tests FAIL against the current implementation which uses raw <button>
 * elements. Builder must replace both controls with PDS PButton components.
 *
 * AC2 v2 (keyword assertions) and AC5 v2 (Shell close-cycle) are excluded
 * because current implementation already satisfies them — new tests for those
 */
import { describe, it, expect, vi, afterEach } from 'vitest'
import { render } from '@testing-library/react'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'
import ResolveModal from '../components/ResolveModal'
import type { PendingDRWithBody } from '../components/ResolveModal'

// ─── react-markdown mock ──────────────────────────────────────────────────────

vi.mock('react-markdown', () => ({
  default: ({ children }: { children: string }) => (
    <div data-testid="markdown-body">{children}</div>
  ),
}))

// ─── Fixture ──────────────────────────────────────────────────────────────────

const DR_FIXTURE: PendingDRWithBody = {
  id: 'dr-1389-001',
  task_id: 42,
  agent: 'builder',
  request_type: 'scope-decision',
  created: '2026-05-01T10:00:00Z',
  title: 'Confirm caching approach',
  body_preview: 'Builder needs guidance on caching.',
  body: '## Context\n\nShould we use Redis or in-memory cache?',
}

// ─── Render helper ────────────────────────────────────────────────────────────

function renderModal(
  dr: PendingDRWithBody | null = DR_FIXTURE,
  onClose = vi.fn(),
  onResolved = vi.fn(),
) {
  return render(
    <PorscheDesignSystemProvider>
      <ResolveModal dr={dr} onClose={onClose} onResolved={onResolved} />
    </PorscheDesignSystemProvider>,
  )
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('TestFromAC_ResolveModalPDSButtons', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    vi.clearAllMocks()
  })

  // ─── AC4 (td:2): Submit uses p-button, not raw button ────────────────────
  //
  // Current code: <button type="button" data-testid="resolve-submit"> → FAIL

  it('submit control is rendered as a p-button custom element', () => {
    const { container } = renderModal()
    const pBtn = container.querySelector('p-button[data-testid="resolve-submit"]')
    expect(pBtn).not.toBeNull()
  })

  it('no raw button element carries data-testid="resolve-submit"', () => {
    // After PButton migration, the data-testid must be on the p-button outer
    // element — not on a raw <button> that sits in its shadow DOM
    const { container } = renderModal()
    const rawBtn = container.querySelector('button[data-testid="resolve-submit"]')
    expect(rawBtn).toBeNull()
  })

  it('submit p-button has variant="primary" (not secondary or unset)', () => {
    // PDS v4 stores variant as a DOM property, not a reflected attribute.
    // getAttribute('variant') always returns null — use element.variant instead.
    const { container } = renderModal()
    const pBtn = container.querySelector(
      'p-button[data-testid="resolve-submit"]',
    ) as (HTMLElement & { variant: string }) | null
    expect(pBtn).not.toBeNull()
    expect(pBtn!.variant).toBe('primary')
  })

  // ─── AC4 (td:2): Cancel uses p-button, not raw button ────────────────────
  //
  // Current code: <button type="button" data-testid="resolve-cancel"> → FAIL

  it('cancel control is rendered as a p-button custom element', () => {
    const { container } = renderModal()
    const pBtn = container.querySelector('p-button[data-testid="resolve-cancel"]')
    expect(pBtn).not.toBeNull()
  })

  it('no raw button element carries data-testid="resolve-cancel"', () => {
    const { container } = renderModal()
    const rawBtn = container.querySelector('button[data-testid="resolve-cancel"]')
    expect(rawBtn).toBeNull()
  })

  it('cancel p-button has variant="secondary" (not primary or unset)', () => {
    const { container } = renderModal()
    const pBtn = container.querySelector(
      'p-button[data-testid="resolve-cancel"]',
    ) as (HTMLElement & { variant: string }) | null
    expect(pBtn).not.toBeNull()
    expect(pBtn!.variant).toBe('secondary')
  })
})

