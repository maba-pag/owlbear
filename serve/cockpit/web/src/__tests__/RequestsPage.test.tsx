import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, useLocation } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import RequestsPage from '../pages/RequestsPage'
import type { NativeStoredRequest } from '../api/native'

const pending: NativeStoredRequest = {
  request: {
    request_id: 'pending-1', kind: 'decision', title: 'Pending decision', summary: 'Choose', body: 'Body', agent: 'builder',
    created_at: '', change_id: 'change', delivery_digest: 'a'.repeat(64), target_node_id: 'DN-001', job_ids: [20],
    options: [
      { option_id: 'a', label: 'A', recommended: true, confidence: 0.8, rationale: '', pros: [], cons: [], risks: [] },
      { option_id: 'b', label: 'B', recommended: false, confidence: 0.6, rationale: '', pros: [], cons: [], risks: [] },
    ],
  },
  resolution: null,
}
const resolved: NativeStoredRequest = {
  request: {
    request_id: 'resolved-1', kind: 'action', title: 'Resolved action', summary: 'Done', body: 'Body', agent: 'builder',
    created_at: '', change_id: 'change', delivery_digest: 'a'.repeat(64), target_node_id: null, job_ids: [21],
    evidence: ['done'], resume_condition: 'Done',
  },
  resolution: {
    request_id: 'resolved-1', disposition: 'local', resolved_at: '', resolved_by: 'user', selected_option_id: null,
    response: 'done', rationale: 'done',
  },
}

const hooks = vi.hoisted(() => ({
  list: {
    items: [] as NativeStoredRequest[], nextCursor: null, isLoading: false, isLoadingMore: false,
    error: null, retryFromStart: false, loadMore: vi.fn(), retry: vi.fn(),
  },
  detail: { data: null as NativeStoredRequest | null, error: null, isLoading: false, retry: vi.fn() },
}))
hooks.list.items = [pending, resolved]

vi.mock('../hooks/NativeChangeProvider', () => ({
  useNativeChangeSelection: () => ({ selectedSummary: { change_id: 'change', state: 'loaded' } }),
}))
vi.mock('../hooks/useNativeResources', () => ({
  useNativeRequests: () => hooks.list,
  useNativeRequest: (_changeId: string, requestId: string | null) => (
    requestId === null ? { ...hooks.detail, data: null } : hooks.detail
  ),
}))
vi.mock('../components/NativeRequestResolver', () => ({
  default: ({ onReturn }: { onReturn: () => void }) => <button type="button" onClick={onReturn}>Return</button>,
}))

function LocationProbe() {
  const location = useLocation()
  return <output data-testid="location">{`${location.pathname}${location.search}`}</output>
}

function renderPage(entry = '/requests?change=change') {
  return render(
    <MemoryRouter initialEntries={[entry]}>
      <RequestsPage />
      <LocationProbe />
    </MemoryRouter>,
  )
}

describe('RequestsPage', () => {
  afterEach(() => {
    hooks.detail.data = null
    vi.clearAllMocks()
  })

  it('filters pending and resolved request lists', () => {
    renderPage()
    expect(screen.getByText('Pending decision')).toBeInTheDocument()
    expect(screen.queryByText('Resolved action')).not.toBeInTheDocument()

    fireEvent.click(screen.getByText('Resolved'))
    expect(screen.queryByText('Pending decision')).not.toBeInTheDocument()
    expect(screen.getByText('Resolved action')).toBeInTheDocument()
  })

  it('shows full context and working node/job deep links', () => {
    hooks.detail.data = pending
    renderPage('/requests?change=change&request=pending-1')

    expect(screen.getByTestId('request-detail')).toHaveTextContent('Pending decision')
    expect(screen.getByTestId('request-detail')).toHaveTextContent('change')
    expect(screen.getByTestId('request-detail')).toHaveTextContent('DN-001')
    expect(screen.getByTestId('request-detail')).toHaveTextContent('#20')
    fireEvent.click(screen.getByText('Open node'))
    expect(screen.getByTestId('location')).toHaveTextContent('/?change=change&node=DN-001')
  })

  it('returns focus to the originating request card', async () => {
    hooks.detail.data = pending
    renderPage('/requests?change=change&request=pending-1')
    fireEvent.click(screen.getByText('Return'))
    await waitFor(() => expect(document.activeElement).toHaveAttribute('data-request-id', 'pending-1'))
  })
})
