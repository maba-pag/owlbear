import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { beforeEach, expect, it, vi } from 'vitest'
import type { WorkItemDetailResponse, WorkItemProjection } from '../api/workItems'
import WorkPortfolioPage from '../pages/WorkPortfolioPage'

const api = vi.hoisted(() => ({
  list: vi.fn(),
  show: vi.fn(),
  requests: vi.fn(),
  trace: vi.fn(),
  createRequest: vi.fn(),
}))

vi.mock('../api/workItems', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/workItems')>()
  return {
    ...actual,
    listWorkItems: api.list,
    showWorkItem: api.show,
    listWorkItemRequests: api.requests,
    showWorkItemTrace: api.trace,
    createWorkItemRequest: api.createRequest,
  }
})

const stages = ['design', 'planning', 'implementation', 'assembly'] as const
const attention = ['user', 'agent', 'waiting', 'none'] as const

function portfolioFixture(): WorkItemProjection[] {
  return Array.from({ length: 120 }, (_, index) => ({
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
  }))
}

function detailFixture(item: WorkItemProjection): WorkItemDetailResponse {
  return {
    card: item,
    authority_identity: 'a'.repeat(64),
    commitments: [{
      commitment_id: item.commitment_ids[0],
      commitment_class: 'protected-request',
      provenance: 'user request',
      statement: `Preserve ${item.title}`,
    }],
    acceptance: [`Observe ${item.title}`],
    task_progress: [{ scope_id: 'PLAN-001', task_count: 4, reviewed_task_count: item.reviewed_task_count }],
    correction_history: [],
    semantic_updates: [],
    completion_summary: null,
    trace_links: { activity: '/trace', evidence: '/trace', requests: '/requests' },
  }
}

function selectValue(element: Element, value: string) {
  const host = element as HTMLElement & { value: string }
  host.value = value
  fireEvent(host, new CustomEvent('change', { detail: { value } }))
}

const items = portfolioFixture()

beforeEach(() => {
  api.list.mockReset().mockResolvedValue({
    items,
    attention_counts: { user: 30, agent: 30, waiting: 30, none: 30 },
  })
  api.show.mockReset().mockImplementation((_workItemId: string, changeId: string) => {
    const item = items.find((candidate) => candidate.work_item_id === _workItemId && candidate.change_id === changeId)
    return Promise.resolve(detailFixture(item!))
  })
  api.requests.mockReset().mockResolvedValue({ requests: [] })
  api.trace.mockReset().mockResolvedValue({
    activity: [{ kind: 'reviewed' }],
    evidence: [{ kind: 'receipt' }],
  })
  api.createRequest.mockReset().mockResolvedValue({ request_id: 'request-created' })
})

it('filters 120 cards while preserving composite selection and shown count', async () => {
  const { container } = render(
    <MemoryRouter initialEntries={['/work']}>
      <WorkPortfolioPage />
    </MemoryRouter>,
  )

  expect(await screen.findByTestId('work-shown-count')).toHaveTextContent('Showing 120 of 120')
  for (const label of ['Design', 'Planning', 'Implementation', 'Assembly']) {
    expect(screen.getByText(label, { exact: true })).toBeInTheDocument()
  }
  const filters = container.querySelectorAll('p-select')
  selectValue(filters[0], 'change-2')
  expect(screen.getByTestId('work-shown-count')).toHaveTextContent('Showing 40 of 120')
  selectValue(filters[1], 'user')
  expect(screen.getByTestId('work-shown-count')).toHaveTextContent('Showing 10 of 120')

  fireEvent.click(screen.getAllByText('Inspect', { exact: true })[0])
  expect(await screen.findByText('Specification', { exact: true })).toBeInTheDocument()
  expect(screen.getByText('Requests', { exact: true })).toBeInTheDocument()
  expect(api.show).toHaveBeenCalledWith('OUT-005', 'change-2')
  expect(screen.getByText('Selected', { exact: true })).toBeInTheDocument()
})

it('creates a scoped request and loads technical trace only on demand', async () => {
  const { container } = render(
    <MemoryRouter initialEntries={['/work']}>
      <WorkPortfolioPage />
    </MemoryRouter>,
  )
  await screen.findByTestId('work-shown-count')
  fireEvent.click(screen.getAllByText('Inspect', { exact: true })[0])
  await screen.findByText('Requests', { exact: true })
  expect(api.trace).not.toHaveBeenCalled()
  expect(screen.queryByTestId('work-technical-trace')).not.toBeInTheDocument()

  const input = container.querySelector('p-input-text[name="work-request-summary"]') as HTMLElement & { value: string }
  input.value = 'Clarify the proof boundary'
  fireEvent(input, new CustomEvent('change', { detail: { value: input.value } }))
  const createButton = screen.getByText('Create request').closest('p-button')
  await waitFor(() => expect(createButton).not.toHaveAttribute('disabled'))
  fireEvent.click(createButton!)
  await waitFor(() => expect(api.createRequest).toHaveBeenCalledWith(
    'OUT-001',
    'change-1',
    expect.objectContaining({
      authority_digest: 'a'.repeat(64),
      commitment_id: 'COM-1',
      summary: 'Clarify the proof boundary',
    }),
  ))

  fireEvent.click(screen.getByText('Show technical trace'))
  expect(await screen.findByTestId('work-technical-trace')).toBeInTheDocument()
  expect(screen.getByRole('heading', { name: 'Activity' })).toBeInTheDocument()
  expect(screen.getByRole('heading', { name: 'Evidence' })).toBeInTheDocument()
  expect(api.trace).toHaveBeenCalledWith('OUT-001', 'change-1')
})

it('does not expose obsolete job administration commands', async () => {
  render(
    <MemoryRouter initialEntries={['/work']}>
      <WorkPortfolioPage />
    </MemoryRouter>,
  )
  await screen.findByTestId('work-shown-count')

  for (const command of ['Priority', 'Cancel', 'Release claim', 'Accept job', 'Audit job']) {
    expect(screen.queryByText(command, { exact: true })).not.toBeInTheDocument()
  }
})
