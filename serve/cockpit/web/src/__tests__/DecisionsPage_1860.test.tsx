/**
 * Task #1860 — P2-03: Request list rendering from structured fields
 *
 * AC1: Each request card ([data-testid="dr-item-{id}"]) renders from PendingDR
 *      fields directly — getDecisionBrief() removed. Card shows: kind badge (PTag:
 *      "Decision"/"Action" per item.kind), item.title heading, item.summary text,
 *      item.agent attribution, item.created via formatAge. Decision-kind cards add:
 *      option count text and one confidence bar per option (width=confidence*100%,
 *      testid confidence-bar-{option_id}).
 * AC2: Clicking [data-testid="dr-item-{id}"] opens the resolve modal showing that
 *      item's title. Mechanism: existing setSelectedDRId; no new routing components.
 * AC3: Empty state ([data-testid="decisions-empty-state"]): "No pending requests"
 *      when items empty and not loading. Sort order (oldest-first by created)
 *      preserved. Old brief-section layout (context/recommendation/consequence from
 *      body parsing) intentionally replaced by the structured-field card layout.
 *
 * RED reasons (failures against current implementation):
 *   AC1: Kind badge uses formatRequestType(request_type) not item.kind → fixtures use
 *        request_type that differs from kind (e.g. 'scope-decision' vs 'decision'),
 *        so current badge text 'Scope Decision' fails the not.toContain assertion;
 *        item.summary not shown (body-parsed context rendered instead — unique string
 *        makes toContain fail); item.agent not shown (current code excludes it);
 *        confidence bars absent entirely.
 *   AC2: item.summary assertion in combined test fails before click assertion.
 *   AC3: Empty state text is "No decisions are waiting." (not "No pending requests");
 *        dr-context, dr-recommendation, dr-consequence sections rendered from body parsing.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, fireEvent } from '@testing-library/react'
import type { PendingDR } from '../hooks/usePendingDRs'

const mockUseDRState = vi.hoisted(() => vi.fn())
const mockSetSelectedDRId = vi.hoisted(() => vi.fn())

vi.mock('../hooks/CockpitProvider', () => ({
  useDRState: mockUseDRState,
}))

import DecisionsPage from '../pages/DecisionsPage'

// ─── Fixtures ──────────────────────────────────────────────────────────────────
// DR_DECISION.request_type='scope-decision' (kind='decision'): formatRequestType
// returns 'Scope Decision', not 'Decision', so not.toContain('Scope Decision') fails.
// DR_ACTION.request_type='user-action' (kind='action'): formatRequestType returns
// 'User Action', not 'Action', so not.toContain('User Action') fails.
// DR_DECISION.body has structured sections so current dr-context / dr-recommendation /
// dr-consequence elements render and the toBeNull assertions fail.
// DR_DECISION.summary is a string unique enough not to appear in body-parsed output.

const DR_DECISION: PendingDR = {
  id: 'dr-1860-001',
  task_id: 1860,
  agent: 'builder',
  request_type: 'scope-decision',
  created: '2026-05-20T10:00:00Z',
  title: 'Should we proceed with feature X?',
  summary: 'Direct summary from item.summary — unique string not derivable from body.',
  kind: 'decision',
  options: [
    { option_id: 'opt-a', label: 'Proceed now', confidence: 0.75, recommended: true, rationale: 'Faster delivery' },
    { option_id: 'opt-b', label: 'Defer to Q3', confidence: 0.25, recommended: false, rationale: 'Less risk' },
  ],
  body: [
    '## Context',
    'Feature X implementation context from body parsing.',
    '',
    '## Recommendation',
    'Proceed now with feature X.',
    '',
    '## Consequences',
    'Faster delivery but increased scope.',
  ].join('\n'),
  body_preview: 'Feature X decision preview.',
}

const DR_ACTION: PendingDR = {
  id: 'dr-1860-002',
  task_id: 1861,
  agent: 'architect',
  request_type: 'user-action',
  created: '2026-05-21T10:00:00Z',
  title: 'Run the migration script',
  summary: 'Action summary: execute the pending migration.',
  kind: 'action',
  options: [],
  body: '',
  body_preview: '',
}

const DR_ZERO_CONFIDENCE: PendingDR = {
  id: 'dr-1860-003',
  task_id: 1862,
  agent: 'builder',
  request_type: 'decision',
  created: '2026-05-19T10:00:00Z',
  title: 'Zero confidence decision',
  summary: 'All options have zero confidence.',
  kind: 'decision',
  options: [{ option_id: 'opt-zero', label: 'Zero option', confidence: 0, recommended: false, rationale: '' }],
  body: '',
  body_preview: '',
}

const DR_FULL_CONFIDENCE: PendingDR = {
  id: 'dr-1860-004',
  task_id: 1863,
  agent: 'builder',
  request_type: 'decision',
  created: '2026-05-22T10:00:00Z',
  title: 'Full confidence decision',
  summary: 'One option at full confidence.',
  kind: 'decision',
  options: [{ option_id: 'opt-full', label: 'Full option', confidence: 1.0, recommended: true, rationale: '' }],
  body: '',
  body_preview: '',
}

const DR_OLDER: PendingDR = {
  ...DR_DECISION,
  id: 'dr-1860-older',
  created: '2026-05-18T10:00:00Z',
  title: 'Older decision',
  summary: 'Older decision summary.',
}

const DR_NEWER: PendingDR = {
  ...DR_DECISION,
  id: 'dr-1860-newer',
  created: '2026-05-23T10:00:00Z',
  title: 'Newer decision',
  summary: 'Newer decision summary.',
}

// ─── Render helper ─────────────────────────────────────────────────────────────

function renderPage(items: PendingDR[]) {
  mockUseDRState.mockReturnValue({
    count: items.length,
    items,
    isLoading: false,
    error: null,
    refetch: vi.fn(),
    selectedDRId: null,
    setSelectedDRId: mockSetSelectedDRId,
    selectedDR: null,
  })
  return render(<DecisionsPage />)
}

// ─── Tests ─────────────────────────────────────────────────────────────────────

describe('TestFromAC_RequestListRendering', () => {
  beforeEach(() => {
    mockSetSelectedDRId.mockReset()
  })

  // ── AC1: Kind badge from item.kind ──────────────────────────────────────────

  it('decision-kind card shows "Decision" badge (from item.kind, not formatRequestType)', () => {
    // FAILS: formatRequestType('scope-decision') = 'Scope Decision'; not.toContain fails
    const { container } = renderPage([DR_DECISION])
    const card = container.querySelector('[data-testid="dr-item-dr-1860-001"]')
    expect(card?.textContent).toContain('Decision')
    expect(card?.textContent).not.toContain('Scope Decision')
  })

  it('action-kind card shows "Action" badge (from item.kind, not formatRequestType)', () => {
    // FAILS: formatRequestType('user-action') = 'User Action'; not.toContain fails
    const { container } = renderPage([DR_ACTION])
    const card = container.querySelector('[data-testid="dr-item-dr-1860-002"]')
    expect(card?.textContent).toContain('Action')
    expect(card?.textContent).not.toContain('User Action')
  })

  // ── AC1: item.summary shown directly ────────────────────────────────────────

  it('card shows item.summary text directly (not body-parsed context)', () => {
    // FAILS: current code shows getDecisionBrief() context from ## Context body section;
    // unique item.summary string never appears in body-derived text
    const { container } = renderPage([DR_DECISION])
    const card = container.querySelector('[data-testid="dr-item-dr-1860-001"]')
    expect(card?.textContent).toContain('Direct summary from item.summary — unique string not derivable from body')
  })

  // ── AC1: item.agent attribution ─────────────────────────────────────────────

  it('card shows item.agent as attribution text', () => {
    // FAILS: current code excludes agent text from the card (1688 test asserts this explicitly)
    const { container } = renderPage([DR_DECISION])
    const card = container.querySelector('[data-testid="dr-item-dr-1860-001"]')
    expect(card?.textContent).toContain('builder')
  })

  // ── AC1: Confidence bars for decision-kind ───────────────────────────────────

  it('decision-kind card renders one confidence bar per option', () => {
    // FAILS: no confidence bars exist in current implementation
    const { container } = renderPage([DR_DECISION])
    expect(container.querySelector('[data-testid="confidence-bar-opt-a"]')).not.toBeNull()
    expect(container.querySelector('[data-testid="confidence-bar-opt-b"]')).not.toBeNull()
  })

  it('confidence bar width equals confidence * 100 percent', () => {
    // FAILS: confidence bars absent; when present width must match formula
    const { container } = renderPage([DR_DECISION])
    const barA = container.querySelector('[data-testid="confidence-bar-opt-a"]') as HTMLElement | null
    const barB = container.querySelector('[data-testid="confidence-bar-opt-b"]') as HTMLElement | null
    expect(barA?.style.width).toBe('75%')
    expect(barB?.style.width).toBe('25%')
  })

  it('confidence=0 option renders confidence bar with 0% width', () => {
    // FAILS: confidence bars absent
    const { container } = renderPage([DR_ZERO_CONFIDENCE])
    const bar = container.querySelector('[data-testid="confidence-bar-opt-zero"]') as HTMLElement | null
    expect(bar?.style.width).toBe('0%')
  })

  it('confidence=1.0 option renders confidence bar with 100% width', () => {
    // FAILS: confidence bars absent
    const { container } = renderPage([DR_FULL_CONFIDENCE])
    const bar = container.querySelector('[data-testid="confidence-bar-opt-full"]') as HTMLElement | null
    expect(bar?.style.width).toBe('100%')
  })

  // ── AC1: Option count text ──────────────────────────────────────────────────

  it('decision-kind card shows option count text for item.options', () => {
    // FAILS: current code shows body-parsed options (none for DR_DECISION, no numbered list
    // in body) not item.options; no "2 options" count label appears in card text
    const { container } = renderPage([DR_DECISION])
    const card = container.querySelector('[data-testid="dr-item-dr-1860-001"]')
    // DR_DECISION has 2 item.options; card should surface count text
    expect(card?.textContent).toMatch(/2\s+options?/i)
  })

  // ── AC2: Click mechanism ─────────────────────────────────────────────────────

  it('clicking card calls setSelectedDRId with item.id', () => {
    // First assertion (item.summary visible) FAILS in current impl — combined test fails.
    // Both assertions pass once builder shows item.summary from structured field.
    const { container } = renderPage([DR_DECISION])
    const card = container.querySelector('[data-testid="dr-item-dr-1860-001"]')
    // Verify card renders item.summary (new structured-field contract — fails currently)
    expect(card?.textContent).toContain('Direct summary from item.summary — unique string not derivable from body')
    // Click mechanism preserved: setSelectedDRId called with item.id
    fireEvent.click(card!)
    expect(mockSetSelectedDRId).toHaveBeenCalledWith('dr-1860-001')
  })

  // ── AC3: Empty state text ─────────────────────────────────────────────────────

  it('empty state shows "No pending requests" when items list is empty', () => {
    // FAILS: current empty state renders "No decisions are waiting."
    const { container } = renderPage([])
    const emptyState = container.querySelector('[data-testid="decisions-empty-state"]')
    expect(emptyState).not.toBeNull()
    expect(emptyState?.textContent).toContain('No pending requests')
  })

  // ── AC3: Sort order preserved (regression guard) ─────────────────────────────

  it('items are rendered oldest-first by created timestamp', () => {
    // Regression guard: sort contract preserved from existing implementation.
    // Expected to PASS against current code — included per AC3 "preserved" clause.
    const { container } = renderPage([DR_NEWER, DR_OLDER])
    const items = [...container.querySelectorAll('[data-testid^="dr-item-"]')]
    expect(items.map((el) => el.getAttribute('data-testid'))).toEqual([
      'dr-item-dr-1860-older',
      'dr-item-dr-1860-newer',
    ])
  })

  // ── AC3: Old brief-section layout removed ───────────────────────────────────

  it('card does not render brief context section (dr-context-{id} removed)', () => {
    // FAILS: current code renders dr-context-dr-1860-001 for body with ## Context
    const { container } = renderPage([DR_DECISION])
    expect(container.querySelector('[data-testid="dr-context-dr-1860-001"]')).toBeNull()
  })

  it('card does not render brief recommendation section (dr-recommendation-{id} removed)', () => {
    // FAILS: current code renders dr-recommendation-dr-1860-001 for body with ## Recommendation
    const { container } = renderPage([DR_DECISION])
    expect(container.querySelector('[data-testid="dr-recommendation-dr-1860-001"]')).toBeNull()
  })

  it('card does not render brief consequence section (dr-consequence-{id} removed)', () => {
    // FAILS: current code renders dr-consequence-dr-1860-001 for body with ## Consequences
    const { container } = renderPage([DR_DECISION])
    expect(container.querySelector('[data-testid="dr-consequence-dr-1860-001"]')).toBeNull()
  })
})
