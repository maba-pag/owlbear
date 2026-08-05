import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { beforeEach, expect, it, vi } from 'vitest'
import {
  WorkItemApiError,
  type CompletedChangePage,
  type CompletedChangeRecord,
  type WorkItemDetailResponse,
  type WorkItemProjection,
  type WorkItemSummaryResponse,
} from '../api/workItems'
import WorkPortfolioPage from '../pages/WorkPortfolioPage'

const api = vi.hoisted(() => ({
  list: vi.fn(),
  show: vi.fn(),
  answer: vi.fn(),
  clear: vi.fn(),
  recover: vi.fn(),
  move: vi.fn(),
  retryIntegration: vi.fn(),
  listCompleted: vi.fn(),
  searchCompleted: vi.fn(),
  showCompleted: vi.fn(),
}))

vi.mock('../api/workItems', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/workItems')>()
  return {
    ...actual,
    listWorkItems: api.list,
    showWorkItem: api.show,
    answerWorkItemRequest: api.answer,
    clearWorkItemBlock: api.clear,
    recoverWorkItemClaim: api.recover,
    moveWorkItemBackward: api.move,
    retryWorkItemIntegration: api.retryIntegration,
    listCompletedChanges: api.listCompleted,
    searchCompletedChanges: api.searchCompleted,
    showCompletedChange: api.showCompleted,
  }
})

const stages = ['design', 'planning', 'implementation', 'assembly'] as const
const attention = ['user', 'agent', 'waiting', 'none'] as const

function portfolioFixture(): WorkItemSummaryResponse[] {
  return Array.from({ length: 120 }, (_, index) => {
    const card: WorkItemProjection = {
      work_item_id: `OUT-${String(index + 1).padStart(3, '0')}`,
      change_id: `change-${(index % 3) + 1}`,
      scope: 'outcome',
      title: `Outcome ${index + 1}`,
      promise: `Deliver observable outcome ${index + 1}`,
      stage: stages[index % stages.length],
      attention: attention[index % attention.length],
      dependency_ready: true,
      commitment_ids: [`COM-${index + 1}`],
      dependency_ids: [],
      replacement_ids: [],
      task_count: 4,
      reviewed_task_count: index % 5,
      next_action: 'Continue delivery',
    }
    return {
      card,
      links: {
        self: `/api/changes/${card.change_id}/outcomes/${card.work_item_id}`,
        answer_request: '/answer',
        clear_block: '/clear',
        recover_claim: '/recover',
        move_backward: '/move',
        integration_attention: '/attention',
        integration_retry: '/retry',
      },
    }
  })
}

function detailFixture(overrides: Partial<WorkItemDetailResponse['operator']> = {}): WorkItemDetailResponse {
  return {
    operator: {
      change_id: 'change-1',
      outcome_id: 'OUT-001',
      stage: 'planning',
      block: null,
      requests: [],
      active_claim: null,
      return_context: null,
      recovery_attention: null,
      integration_attention: null,
      ...overrides,
    },
    links: {
      self: '/api/changes/change-1/outcomes/OUT-001',
      answer_request: '/answer',
      clear_block: '/clear',
      recover_claim: '/recover',
      move_backward: '/move',
      integration_attention: '/attention',
      integration_retry: '/retry',
    },
  }
}

function selectValue(element: Element, value: string) {
  const host = element as HTMLElement & { value: string }
  host.value = value
  fireEvent(host, new CustomEvent('change', { detail: { value }, bubbles: true }))
}

function inputValue(element: Element, value: string) {
  const host = element as HTMLElement & { value: string }
  host.value = value
  fireEvent(host, new CustomEvent('input', { detail: { value }, bubbles: true }))
}

function renderPage() {
  return render(<MemoryRouter initialEntries={['/delivery']}><WorkPortfolioPage /></MemoryRouter>)
}

function openFilters() {
  fireEvent.click(screen.getByTestId('work-filters-toggle'))
}

function inspectFirstItem() {
  fireEvent.click(screen.getAllByText('View details', { exact: true })[0])
}

const items = portfolioFixture()
let currentDetail: WorkItemDetailResponse
const completed: CompletedChangeRecord[] = [
  {
    change_id: 'completed-alpha',
    completion_id: 'a'.repeat(64),
    completion_path: '.owlbear/completed/completed-alpha',
    package_id: 'b'.repeat(64),
    introducing_target_commit: 'c'.repeat(40),
    source_target_commit: 'd'.repeat(40),
    title: 'Alpha delivery',
    semantic_summary: 'Shipped the bounded Alpha workflow.',
  },
  {
    change_id: 'completed-beta',
    completion_id: 'e'.repeat(64),
    completion_path: '.owlbear/completed/completed-beta',
    package_id: 'f'.repeat(64),
    introducing_target_commit: '1'.repeat(40),
    source_target_commit: '2'.repeat(40),
    title: 'Beta search',
    semantic_summary: 'Added exact semantic history search.',
  },
]

beforeEach(() => {
  currentDetail = detailFixture()
  api.list.mockReset().mockResolvedValue({
    items,
    attention_counts: { user: 30, agent: 30, waiting: 30, none: 30 },
  })
  api.show.mockReset().mockImplementation(() => Promise.resolve(currentDetail))
  api.answer.mockReset().mockResolvedValue({})
  api.clear.mockReset().mockResolvedValue({})
  api.recover.mockReset().mockResolvedValue({})
  api.move.mockReset().mockResolvedValue({ invalidated_outcome_ids: ['OUT-002'], move: {} })
  api.retryIntegration.mockReset().mockResolvedValue({})
  api.listCompleted.mockReset().mockResolvedValue({ records: completed, next_cursor: null })
  api.searchCompleted.mockReset().mockResolvedValue({ records: [completed[1]], next_cursor: null })
  api.showCompleted.mockReset().mockResolvedValue(completed[1])
})

it('searches completed history and opens one exact completion', async () => {
  const { container } = renderPage()
  await screen.findByTestId('work-portfolio-board')

  fireEvent.click(screen.getByRole('button', { name: 'Completed history' }))
  expect(screen.getByTestId('completed-history-workspace')).toHaveTextContent('Completed changes')
  expect(await screen.findByText('Alpha delivery')).toBeInTheDocument()

  const search = container.querySelector('p-input-search[name="completed-history-search"]')! as unknown as Record<string, unknown>
  expect(search.label).toBe('Search completed work')
  expect(search.hideLabel).toBe(true)
  expect(search.placeholder ?? '').toBe('')
  expect(search.indicator).toBe(true)

  await waitFor(() => {
    inputValue(container.querySelector('p-input-search[name="completed-history-search"]')!, 'beta')
    expect(api.searchCompleted).toHaveBeenCalledWith('beta')
  })
  expect(await screen.findByText('Beta search')).toBeInTheDocument()
  fireEvent.click(screen.getByText('Inspect', { exact: true }))

  await waitFor(() => expect(api.showCompleted).toHaveBeenCalledWith('completed-beta', 'e'.repeat(64)))
  expect(await screen.findByTestId('completed-change-detail')).toHaveTextContent('Added exact semantic history search.')
})

it('ignores an older completed page after the search query changes', async () => {
  const staleRecord = { ...completed[0], completion_id: '9'.repeat(64), title: 'Stale page' }
  let resolveOlderPage!: (page: CompletedChangePage) => void
  const olderPage = new Promise<CompletedChangePage>((resolve) => {
    resolveOlderPage = resolve
  })
  api.listCompleted.mockImplementation((cursor?: string) => cursor
    ? olderPage
    : Promise.resolve({ records: [completed[0]], next_cursor: 'older-page' }))

  const { container } = renderPage()
  await screen.findByTestId('work-portfolio-board')
  fireEvent.click(screen.getByRole('button', { name: 'Completed history' }))
  expect(screen.getByTestId('completed-history-workspace')).toHaveTextContent('Completed changes')
  expect(await screen.findByText('Alpha delivery')).toBeInTheDocument()

  fireEvent.click(screen.getByText('Load more'))
  await waitFor(() => expect(api.listCompleted).toHaveBeenCalledWith('older-page'))
  await waitFor(() => {
    inputValue(container.querySelector('p-input-search[name="completed-history-search"]')!, 'beta')
    expect(api.searchCompleted).toHaveBeenCalledWith('beta')
  })
  expect(await screen.findByText('Beta search')).toBeInTheDocument()

  await act(async () => {
    resolveOlderPage({ records: [staleRecord], next_cursor: null })
    await olderPage
  })
  expect(screen.queryByText('Stale page')).not.toBeInTheDocument()
  expect(screen.getByText('Beta search')).toBeInTheDocument()
})

it('reveals the shown-of-total relationship only while a filter narrows the board', async () => {
  const { container } = renderPage()

  await screen.findByTestId('work-portfolio-board')
  expect(screen.getByTestId('work-shown-count')).toBeEmptyDOMElement()
  expect(container.querySelectorAll('p-select')).toHaveLength(0)

  openFilters()
  const filters = container.querySelectorAll('p-select')
  selectValue(filters[0], 'change-2')
  expect(screen.getByTestId('work-shown-count')).toHaveTextContent('40 of 120')
  selectValue(filters[1], 'user')
  expect(screen.getByTestId('work-shown-count')).toHaveTextContent('10 of 120')
  expect(screen.getByTestId('work-filters-toggle')).toHaveTextContent('Filter (2)')

  inspectFirstItem()
  expect(await screen.findByText('Requests', { exact: true })).toBeInTheDocument()
  expect(screen.getByText('planning', { exact: true })).toBeInTheDocument()
  expect(api.show).toHaveBeenCalledWith('change-2', 'OUT-005')
})

it('clears one active filter from its summary chip', async () => {
  const { container } = renderPage()

  await screen.findByTestId('work-portfolio-board')
  openFilters()
  selectValue(container.querySelectorAll('p-select')[0], 'change-2')
  expect(screen.getByTestId('work-shown-count')).toHaveTextContent('40 of 120')

  fireEvent.click(screen.getByTestId('work-filter-chip-change'))

  expect(screen.getByTestId('work-shown-count')).toBeEmptyDOMElement()
  expect(screen.queryByTestId('work-filter-chip-change')).toBeNull()
})

it('summarises the portfolio as one total plus every counted attention state', async () => {
  api.list.mockResolvedValue({ items, attention_counts: { user: 1, agent: 1, waiting: 0, none: 4 } })
  renderPage()

  const summary = await screen.findByTestId('workspace-header-summary')
  expect(summary).toHaveTextContent('6work items')
  expect(summary).toHaveTextContent('1need you')
  expect(summary).toHaveTextContent('1with agents')
  expect(summary).toHaveTextContent('0waiting')
  expect(summary).toHaveTextContent('4no action needed')
  expect(summary).not.toHaveTextContent('settled')
  expect(summary).toHaveTextContent('work items have no action needed')
  expect(summary).toHaveTextContent('work items are waiting on dependencies')
  expect(summary).not.toHaveTextContent('outcome')
})

it('keeps the total consistent with the counted states and singular grammar', async () => {
  api.list.mockResolvedValue({ items, attention_counts: { user: 1, agent: 0, waiting: 0, none: 0 } })
  renderPage()

  const summary = await screen.findByTestId('workspace-header-summary')
  expect(summary).toHaveTextContent('1work item')
  expect(summary).not.toHaveTextContent('1work items')
})

it('uses one attention vocabulary across cards, filters, and detail', async () => {
  const { container } = renderPage()
  await screen.findByTestId('work-portfolio-board')

  const board = screen.getByTestId('work-portfolio-board')
  expect(board).toHaveTextContent('Waiting on dependencies')
  expect(board).toHaveTextContent('No action needed')
  expect(board).not.toHaveTextContent('No attention')
  expect(board).not.toHaveTextContent('Nobody yet')

  openFilters()
  const attentionSelect = container.querySelectorAll('p-select')[1] as HTMLElement & { label: string }
  expect(attentionSelect.label).toBe('Attention')
  const attentionOptions = [...attentionSelect.querySelectorAll('p-select-option')]
    .map((option) => option.textContent)
  expect(attentionOptions).toEqual(['Any attention', 'Needs you', 'Agent working', 'Waiting on dependencies', 'No action needed'])

  selectValue(container.querySelectorAll('p-select')[1], 'waiting')
  const chip = screen.getByTestId('work-filter-chip-attention') as HTMLElement & { label: string }
  expect(chip.label).toBe('Attention: Waiting on dependencies')

  inspectFirstItem()
  expect(await screen.findByTestId('work-item-detail')).toHaveTextContent('Waiting on dependencies')
})

it('answers decision and action requests then refetches current resolution', async () => {
  currentDetail = detailFixture({
    requests: [
      {
        request_id: 'decision-one',
        kind: 'decision',
        outcome_id: 'OUT-001',
        summary: 'Choose deployment mode',
        options: [{ option_id: 'safe', label: 'Safe mode' }],
        resolution: null,
      },
      {
        request_id: 'action-one',
        kind: 'action',
        outcome_id: 'OUT-001',
        summary: 'Provide release note',
        options: [],
        resolution: null,
      },
    ],
  })
  api.answer.mockImplementation((_changeId: string, requestId: string) => {
    currentDetail = detailFixture({
      requests: currentDetail.operator.requests.map((request) => request.request_id === requestId
        ? { ...request, resolution: { selected_option_id: requestId === 'decision-one' ? 'safe' : null, response_text: requestId === 'action-one' ? 'Ready' : null } }
        : request),
    })
    return Promise.resolve({})
  })
  const { container } = renderPage()
  await screen.findByTestId('work-portfolio-board')
  inspectFirstItem()
  await screen.findByText('Choose deployment mode')

  const decisionArticle = screen.getByText('Choose deployment mode').closest('article')!
  await waitFor(() => {
    selectValue(container.querySelector('p-select[name="request-decision-one-option"]')!, 'safe')
    expect((decisionArticle.querySelector('p-button') as HTMLElement & { disabled: boolean }).disabled).toBe(false)
  })
  fireEvent.click(decisionArticle.querySelector('p-button')!)
  await waitFor(() => expect(api.answer).toHaveBeenCalledWith(
    'change-1',
    'decision-one',
    { selected_option_id: 'safe', response_text: null },
  ))
  expect(await screen.findByText('Safe mode')).toBeInTheDocument()

  const actionArticle = screen.getByText('Provide release note').closest('article')!
  await waitFor(() => {
    inputValue(container.querySelector('p-input-text[name="request-action-one-answer"]')!, 'Ready')
    expect((actionArticle.querySelector('p-button') as HTMLElement & { disabled: boolean }).disabled).toBe(false)
  })
  fireEvent.click(actionArticle.querySelector('p-button')!)
  await waitFor(() => expect(api.answer).toHaveBeenCalledWith(
    'change-1',
    'action-one',
    { selected_option_id: null, response_text: 'Ready' },
  ))
  expect(await screen.findByText('Ready')).toBeInTheDocument()
  expect(api.show).toHaveBeenCalledTimes(3)
})

it('requires note and locator before clearing a requestless block', async () => {
  currentDetail = detailFixture({
    block: {
      block_id: 'block-one',
      reason: 'Proof is missing',
      unblock_condition: 'Verify external evidence',
      expected_evidence: ['Evidence locator'],
      locators: ['request:REQ-001'],
      request_id: null,
      resolution_note: null,
      resolution_locators: [],
      resume_commit: null,
    },
  })
  const { container } = renderPage()
  await screen.findByTestId('work-portfolio-board')
  inspectFirstItem()
  expect((await screen.findByText('Clear block') as HTMLElement & { disabled: boolean }).disabled).toBe(true)

  await waitFor(() => {
    inputValue(container.querySelector('p-input-text[name="block-note"]')!, 'Verified externally')
    inputValue(container.querySelector('p-input-text[name="block-locator"]')!, 'request:REQ-001')
    expect((screen.getByText('Clear block') as HTMLElement & { disabled: boolean }).disabled).toBe(false)
  })
  fireEvent.click(screen.getByText('Clear block'))

  await waitFor(() => expect(api.clear).toHaveBeenCalledWith(
    'change-1',
    'OUT-001',
    'block-one',
    'Verified externally',
    ['request:REQ-001'],
  ))
  expect(await screen.findByText('Block cleared.')).toBeInTheDocument()
})

it('cancels or explicitly confirms recovery using exact claim identity', async () => {
  currentDetail = detailFixture({
    active_claim: {
      attempt_id: 'attempt-one',
      claim_id: 'claim-one',
      started_at: '2026-08-04T12:00:00Z',
      worker_role: 'builder',
      task_id: 'TASK-001',
    },
  })
  renderPage()
  await screen.findByTestId('work-portfolio-board')
  inspectFirstItem()
  expect(await screen.findByText(/ago$/)).toBeInTheDocument()

  fireEvent.click(screen.getByText('Recover confirmed-lost claim'))
  expect(screen.getByText('attempt-one')).toBeInTheDocument()
  fireEvent.click(screen.getByText('Cancel'))
  expect(api.recover).not.toHaveBeenCalled()

  fireEvent.click(screen.getByText('Recover confirmed-lost claim'))
  fireEvent.click(screen.getByText('Confirm lost and recover'))
  await waitFor(() => expect(api.recover).toHaveBeenCalledWith(
    'change-1',
    'OUT-001',
    'attempt-one',
    'claim-one',
  ))
})

it('shows typed Integration failure and confirms an earlier-stage move', async () => {
  currentDetail = detailFixture({
    stage: 'implementation',
    return_context: { target: 'planning', reason: 'Plan changed', locators: ['request:REQ-002'] },
    recovery_attention: {
      attempt_id: 'attempt-one',
      claim_id: 'claim-one',
      reason: 'Custody needs review',
      custody_retained: true,
      retry_condition: 'Resolve custody',
    },
    integration_attention: {
      code: 'revision-pending',
      diagnostics: ['New revision requires review.'],
      retry_condition: 'Review the new revision',
    },
  })
  api.retryIntegration.mockRejectedValue(new WorkItemApiError(
    409,
    'ERR_DELIVERY_RUNTIME_CONFLICT',
    'Integration is not ready',
    'delivery',
    true,
  ))
  const { container } = renderPage()
  await screen.findByTestId('work-portfolio-board')
  inspectFirstItem()
  expect(await screen.findByText('Returned to planning')).toBeInTheDocument()
  expect(screen.getByText('Recovery attention')).toBeInTheDocument()
  expect(screen.getByText('Integration: revision-pending')).toBeInTheDocument()

  fireEvent.click(screen.getByText('Retry Integration'))
  expect(await screen.findByRole('alert')).toHaveTextContent('ERR_DELIVERY_RUNTIME_CONFLICT: Integration is not ready')

  await waitFor(() => {
    selectValue(container.querySelector('p-select[name="backward-stage"]')!, 'planning')
    inputValue(container.querySelector('p-input-text[name="backward-reason"]')!, 'Authority changed')
    expect((screen.getByText('Review backward move') as HTMLElement & { disabled: boolean }).disabled).toBe(false)
  })
  fireEvent.click(screen.getByText('Review backward move'))
  fireEvent.click(screen.getByText('Confirm backward move'))
  await waitFor(() => expect(api.move).toHaveBeenCalledWith('change-1', 'OUT-001', 'planning', 'Authority changed'))
  expect(await screen.findByText('Moved backward. Reset: OUT-002.')).toBeInTheDocument()
})
