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

const DR_OLDER: PendingDR = {
  ...DR_WITH_BRIEF,
  id: 'dr-1688-oldest',
  task_id: 1689,
  created: '2026-05-20T08:00:00Z',
  title: 'Oldest pending decision',
}

const DR_NEWER: PendingDR = {
  ...DR_WITH_BRIEF,
  id: 'dr-1688-newest',
  task_id: 1690,
  created: '2026-05-22T08:00:00Z',
  title: 'Newest pending decision',
}

const DR_SAME_CREATED_B: PendingDR = {
  ...DR_WITH_BRIEF,
  id: 'dr-1688-b',
  task_id: 1691,
  created: '2026-05-21T08:00:00Z',
  title: 'Same created B',
}

const DR_SAME_CREATED_A: PendingDR = {
  ...DR_WITH_BRIEF,
  id: 'dr-1688-a',
  task_id: 1692,
  created: '2026-05-21T08:00:00Z',
  title: 'Same created A',
}

const DR_MALFORMED_CREATED: PendingDR = {
  ...DR_WITH_BRIEF,
  id: 'dr-1688-malformed',
  task_id: 1693,
  created: 'not-a-date',
  title: 'Malformed created decision',
}

const UNSTRUCTURED_BODY = 'Decision needed later: choose ownership model for knowledge source lifecycle after #1556 and #1557 complete. Options to evaluate: MCP tools, manifest workflow, Cockpit surface, or hybrid. Default should be continue with the current owner until the lifecycle flow is explicit.'

const DR_UNSTRUCTURED: PendingDR = {
  id: 'dr-1688-plain',
  task_id: 1558,
  agent: 'copilot',
  request_type: 'decision',
  created: '2026-05-14T08:00:00Z',
  title: UNSTRUCTURED_BODY,
  body_preview: UNSTRUCTURED_BODY.slice(0, 200),
  body: UNSTRUCTURED_BODY,
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

  it('renders unstructured plain decisions as summary plus inline options instead of duplicated context', () => {
    const { container } = renderPage([DR_UNSTRUCTURED])
    const item = container.querySelector('[data-testid="dr-item-dr-1688-plain"]')
    const heading = item?.querySelector('h2')

    expect(heading?.textContent).toBe('Choose ownership model for knowledge source lifecycle')
    expect(container.querySelector('[data-testid="dr-summary-dr-1688-plain"]')?.textContent).toContain('Resolve after #1556')
    expect(container.querySelector('[data-testid="dr-options-dr-1688-plain"]')?.textContent).toContain('manifest workflow')
    expect(container.querySelector('[data-testid="dr-options-dr-1688-plain"]')?.textContent).toContain('hybrid')
    expect(container.querySelector('[data-testid="dr-context-dr-1688-plain"]')).toBeNull()
  })

  it('replaces requested-by emphasis with the actual resolver path', () => {
    const { container } = renderPage()
    const item = container.querySelector('[data-testid="dr-item-dr-1688-001"]')
    expect(item?.textContent).not.toContain('Requested by')
    expect(item?.textContent).not.toContain('ApproveNeeds infoReject')
    expect(item?.textContent).toContain('Open resolver')
  })

  it('sorts pending decisions oldest first by created timestamp', () => {
    const { container } = renderPage([DR_NEWER, DR_OLDER])
    const items = [...container.querySelectorAll('[data-testid^="dr-item-"]')]
    expect(items.map((item) => item.getAttribute('data-testid'))).toEqual([
      'dr-item-dr-1688-oldest',
      'dr-item-dr-1688-newest',
    ])
  })

  it('puts malformed created timestamps last and uses id order for exact timestamp ties', () => {
    const { container } = renderPage([DR_SAME_CREATED_B, DR_MALFORMED_CREATED, DR_SAME_CREATED_A, DR_OLDER])
    const items = [...container.querySelectorAll('[data-testid^="dr-item-"]')]

    expect(items.map((item) => item.getAttribute('data-testid'))).toEqual([
      'dr-item-dr-1688-oldest',
      'dr-item-dr-1688-a',
      'dr-item-dr-1688-b',
      'dr-item-dr-1688-malformed',
    ])
  })
})
