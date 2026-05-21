import { render } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import type { PendingDR } from '../hooks/usePendingDRs'

const mockUseDRState = vi.hoisted(() => vi.fn())
const mockSetSelectedDRId = vi.hoisted(() => vi.fn())

vi.mock('../hooks/CockpitProvider', () => ({
  useDRState: mockUseDRState,
}))

import DecisionsPage from '../pages/DecisionsPage'

const DR_WITH_BRIEF: PendingDR = {
  id: 'dr-1688-001',
  task_id: 1688,
  agent: 'builder',
  request_type: 'scope-decision',
  created: '2026-05-21T08:00:00Z',
  title: 'Confirm Decisions workspace shape',
  body_preview: 'Builder needs a decision on the Decisions workspace shape.',
  body: [
    '## Context',
    'The Decisions route needs enough context to resolve a request without guessing.',
    '',
    '## Options',
    '1. Keep the thin notification list.',
    '2. Show a decision brief before opening the modal.',
    '',
    '## Recommendation',
    'Show a decision brief before opening the modal.',
    '',
    '## Consequences',
    'The route becomes the primary decision workflow instead of a duplicate alert.',
  ].join('\n'),
}

function renderPage(items: PendingDR[] = [DR_WITH_BRIEF]) {
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

describe('DecisionsPage workflow brief', () => {
  it('surfaces markdown context as a distinct decision brief section', () => {
    const { container } = renderPage()
    const context = container.querySelector('[data-testid="dr-context-dr-1688-001"]')
    expect(context?.textContent).toContain('Context')
    expect(context?.textContent).toContain('without guessing')
  })

  it('surfaces numbered markdown options without flattening them into one hidden blob', () => {
    const { container } = renderPage()
    const options = container.querySelector('[data-testid="dr-options-dr-1688-001"]')
    expect(options?.textContent).toContain('Keep the thin notification list')
    expect(options?.textContent).toContain('Show a decision brief')
  })

  it('surfaces recommendation and consequence when the DR body provides them', () => {
    const { container } = renderPage()
    expect(container.querySelector('[data-testid="dr-recommendation-dr-1688-001"]')?.textContent).toContain('decision brief')
    expect(container.querySelector('[data-testid="dr-consequence-dr-1688-001"]')?.textContent).toContain('primary decision workflow')
  })

  it('replaces requested-by emphasis with the actual resolution path', () => {
    const { container } = renderPage()
    const item = container.querySelector('[data-testid="dr-item-dr-1688-001"]')
    expect(item?.textContent).not.toContain('Requested by')
    expect(item?.textContent).toContain('Approve')
    expect(item?.textContent).toContain('Needs info')
    expect(item?.textContent).toContain('Reject')
    expect(item?.textContent).toContain('Resolve decision')
  })
})
