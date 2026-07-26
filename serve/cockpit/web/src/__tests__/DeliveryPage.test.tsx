import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { describe, expect, it, vi } from 'vitest'
import DeliveryPage from '../pages/DeliveryPage'
import { NativeApiError } from '../api/native'

const api = vi.hoisted(() => ({ resolve: vi.fn() }))

vi.mock('../api/native', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/native')>()
  return { ...actual, resolveNativeRequest: api.resolve }
})

const detailHooks = vi.hoisted(() => ({
  job: { data: null as null | Record<string, unknown>, error: null, isLoading: false, retry: vi.fn() },
  request: { data: null as null | Record<string, unknown>, error: null, isLoading: false, retry: vi.fn() },
}))

vi.mock('../hooks/NativeChangeProvider', () => ({
  useNativeChangeSelection: vi.fn(() => ({
    selectedChangeId: 'change-invalid',
    selectedSummary: { change_id: 'change-invalid', state: 'invalid' },
  })),
}))
vi.mock('../hooks/useNativeResources', () => ({
  useNativeJobs: vi.fn(() => ({
    items: [], nextCursor: null, isLoading: false, isLoadingMore: false, error: null,
    retryFromStart: false, loadMore: vi.fn(), retry: vi.fn(),
  })),
  useNativeJob: vi.fn(() => detailHooks.job),
  useNativeRequest: vi.fn(() => detailHooks.request),
}))

describe('DeliveryPage', () => {
  it('shows invalid authority with icon plus text and selected job identity', () => {
    const { container } = render(
      <MemoryRouter initialEntries={['/delivery?change=change-invalid&job=42']}>
        <DeliveryPage />
      </MemoryRouter>,
    )

    expect(screen.getByText('Invalid authority prevents delivery.')).toBeInTheDocument()
    expect(container.querySelector('[role="status"] p-icon')).not.toBeNull()
  })

  it('renders retained job and request detail for URL identities', () => {
    detailHooks.job.data = {
      job: { job_id: 42, kind: 'build', disposition: 'pending' },
      token: 'token-42',
      title: 'Build detail',
      outcome: 'Exact purpose',
      proof: 'PROOF-003',
    }
    detailHooks.request.data = {
      request: {
        request_id: 'request-1', kind: 'action', title: 'Resolve evidence', summary: 'Summary', body: 'Request body',
        agent: 'builder', created_at: '', change_id: 'change-invalid', delivery_digest: 'a'.repeat(64), target_node_id: null, job_ids: [42],
      },
      resolution: null,
    }

    render(
      <MemoryRouter initialEntries={['/delivery?change=change-invalid&job=42&request=request-1']}>
        <DeliveryPage />
      </MemoryRouter>,
    )

    expect(screen.getByTestId('selected-job-detail')).toHaveTextContent('Build detail')
    expect(screen.getByTestId('selected-job-detail')).toHaveTextContent('token-42')
    expect(screen.getByTestId('selected-request-detail')).toHaveTextContent('Resolve evidence')
    expect(screen.getByTestId('selected-request-detail')).toHaveTextContent('Pending resolution')
    detailHooks.job.data = null
    detailHooks.request.data = null
  })

  it('completes an action request and retains submitted response on 409', async () => {
    detailHooks.request.data = {
      request: {
        request_id: 'request-1', kind: 'action', title: 'Resolve evidence', summary: 'Summary', body: 'Request body',
        agent: 'builder', created_at: '', change_id: 'change-invalid', delivery_digest: 'a'.repeat(64), target_node_id: null, job_ids: [42],
      },
      resolution: null,
    }
    api.resolve
      .mockRejectedValueOnce(new NativeApiError(409, {
        code: 'ERR_NATIVE_REQUEST_CONFLICT', detail: 'request changed', current_delivery_digest: 'b'.repeat(64),
      }))
      .mockResolvedValueOnce({})
    const { container } = render(
      <MemoryRouter initialEntries={['/delivery?change=change-invalid&request=request-1']}>
        <DeliveryPage />
      </MemoryRouter>,
    )
    const textarea = container.querySelector('p-textarea') as HTMLElement & { value: string }
    textarea.value = 'Evidence complete'
    fireEvent.change(textarea, { target: { value: 'Evidence complete' } })
    fireEvent.click(screen.getByText('Complete request'))

    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent('ERR_NATIVE_REQUEST_CONFLICT')
    expect(alert).toHaveTextContent('Submitted: Evidence complete')
    expect(alert).toHaveTextContent(`Current digest: ${'b'.repeat(64)}`)
    expect(api.resolve).toHaveBeenCalledWith('change-invalid', 'request-1', expect.objectContaining({
      response: 'Evidence complete', disposition: 'local',
    }))
    fireEvent.click(screen.getByText('Retry resolution'))
    await waitFor(() => expect(api.resolve).toHaveBeenLastCalledWith('change-invalid', 'request-1', expect.objectContaining({
      delivery_digest: 'b'.repeat(64), response: 'Evidence complete',
    })))
    detailHooks.request.data = null
  })
})
