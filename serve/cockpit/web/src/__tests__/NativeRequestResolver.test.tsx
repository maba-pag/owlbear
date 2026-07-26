import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { NativeApiError, type NativeStoredRequest } from '../api/native'
import NativeRequestResolver from '../components/NativeRequestResolver'

const api = vi.hoisted(() => ({ resolve: vi.fn(), getRequest: vi.fn() }))
vi.mock('../api/native', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/native')>()
  return { ...actual, getNativeRequest: api.getRequest, resolveNativeRequest: api.resolve }
})

function decisionRequest(): NativeStoredRequest {
  return {
    request: {
      request_id: 'decision-1', kind: 'decision', title: 'Choose approach', summary: 'Tradeoffs', body: 'Decision body',
      agent: 'builder', created_at: '', change_id: 'change', delivery_digest: 'a'.repeat(64), target_node_id: 'DN-001', job_ids: [20],
      options: [
        {
          option_id: 'option-a', label: 'Approach A', recommended: true, confidence: 0.8, rationale: 'Fast',
          pros: ['Quick'], cons: ['Risky'], risks: ['Rollback'],
        },
        {
          option_id: 'option-b', label: 'Approach B', recommended: false, confidence: 0.6, rationale: 'Safe',
          pros: ['Safe'], cons: ['Slow'], risks: ['Delay'],
        },
      ],
    },
    resolution: null,
  }
}

function actionRequest(): NativeStoredRequest {
  return {
    request: {
      request_id: 'action-1', kind: 'action', title: 'Provide evidence', summary: 'Evidence needed', body: 'Action body',
      agent: 'builder', created_at: '', change_id: 'change', delivery_digest: 'a'.repeat(64), target_node_id: null, job_ids: [21],
      evidence: ['signature=abc'], resume_condition: 'Signature is supplied',
    },
    resolution: null,
  }
}

describe('NativeRequestResolver', () => {
  afterEach(() => vi.clearAllMocks())

  it('shows decision tradeoffs, recommendation, confidence, and submits selected option', async () => {
    api.resolve.mockResolvedValue({
      request: decisionRequest(), resumed_jobs: [{ job: { job_id: 20 }, token: 'token' }],
      resume: { disposition: 'resume-linked-jobs', request_id: 'decision-1', target_node_id: 'DN-001', job_ids: [20] },
      design_reentry: null,
    })
    const onResolved = vi.fn(() => {
      expect(screen.getByText('Resumed linked jobs: #20')).toBeInTheDocument()
    })
    render(<NativeRequestResolver stored={decisionRequest()} onResolved={onResolved} />)

    expect(screen.getByText('Recommended')).toBeInTheDocument()
    expect(screen.getByText('Confidence 80%')).toBeInTheDocument()
    const recommended = screen.getByRole('button', { name: /Approach A/ })
    expect(within(recommended).getByText(/Pros:/).parentElement).toHaveTextContent('Quick')
    expect(within(recommended).getByText(/Cons:/).parentElement).toHaveTextContent('Risky')
    expect(within(recommended).getByText(/Risks:/).parentElement).toHaveTextContent('Rollback')
    fireEvent.click(recommended)
    fireEvent.click(screen.getByText('Complete request'))

    await waitFor(() => expect(api.resolve).toHaveBeenCalledWith('change', 'decision-1', expect.objectContaining({
      delivery_digest: 'a'.repeat(64), selected_option_id: 'option-a', disposition: 'local',
    })))
    expect(await screen.findByText('Resumed linked jobs: #20')).toBeInTheDocument()
    await waitFor(() => expect(onResolved).toHaveBeenCalledOnce())
  })

  it('shows action evidence/resume condition and material design re-entry', async () => {
    api.resolve.mockResolvedValue({
      request: actionRequest(), resumed_jobs: [], resume: null,
      design_reentry: {
        disposition: 'design-reentry', request_id: 'action-1', change_id: 'change', delivery_digest: 'a'.repeat(64),
        target_node_id: 'DN-001', job_ids: [21],
      },
    })
    const { container } = render(<NativeRequestResolver stored={actionRequest()} onResolved={vi.fn()} />)
    expect(screen.getByText(/signature=abc/)).toBeInTheDocument()
    expect(screen.getByText(/Signature is supplied/)).toBeInTheDocument()
    const textarea = container.querySelector('p-textarea') as HTMLElement & { value: string }
    textarea.value = 'done'
    fireEvent.change(textarea, { target: { value: 'done' } })
    const select = container.querySelector('p-select') as HTMLElement & { value: string }
    select.value = 'material'
    fireEvent.change(select, { target: { value: 'material' } })
    fireEvent.click(screen.getByText('Complete request'))

    await waitFor(() => expect(api.resolve).toHaveBeenLastCalledWith('change', 'action-1', expect.objectContaining({
      response: 'done', disposition: 'material',
    })))
    expect(await screen.findByText('Design re-entry: DN-001')).toBeInTheDocument()
  })

  it('retains submitted response/current snapshot and adopts digest on Retry', async () => {
    api.resolve
      .mockRejectedValueOnce(new NativeApiError(409, {
        code: 'ERR_NATIVE_REQUEST_CONFLICT', detail: 'changed', current_delivery_digest: 'b'.repeat(64),
        current: { request: { request_id: 'action-1' }, resolution: { response: 'server value' } },
      }))
      .mockResolvedValueOnce({
        request: actionRequest(), resumed_jobs: [],
        resume: { disposition: 'resume-linked-jobs', request_id: 'action-1', target_node_id: null, job_ids: [21] },
        design_reentry: null,
      })
    const { container } = render(<NativeRequestResolver stored={actionRequest()} onResolved={vi.fn()} />)
    const textarea = container.querySelector('p-textarea') as HTMLElement & { value: string }
    textarea.value = 'my response'
    fireEvent.change(textarea, { target: { value: 'my response' } })
    fireEvent.click(screen.getByText('Complete request'))

    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent('Submitted: my response')
    expect(alert).toHaveTextContent('server value')
    await waitFor(() => expect(alert).toHaveFocus())
    fireEvent.click(screen.getByText('Retry resolution'))
    await waitFor(() => expect(api.resolve).toHaveBeenLastCalledWith('change', 'action-1', expect.objectContaining({
      delivery_digest: 'b'.repeat(64), response: 'my response',
    })))
  })

  it.each(['ERR_CHANGE_REVISION_CONFLICT', 'ERR_NATIVE_REQUEST_REFERENCE'])(
    'fetches current request authority for %s while retaining input, Retry, and Return focus',
    async (code) => {
      const current = actionRequest()
      current.request.summary = `Current authority for ${code}`
      api.getRequest.mockResolvedValue(current)
      api.resolve.mockRejectedValue(new NativeApiError(409, {
        code, detail: 'authority changed', current_delivery_digest: 'c'.repeat(64),
      }))
      const onReturn = vi.fn()
      const { container } = render(
        <NativeRequestResolver stored={actionRequest()} onResolved={vi.fn()} onReturn={onReturn} />,
      )
      const textarea = container.querySelector('p-textarea') as HTMLElement & { value: string }
      textarea.value = 'retained response'
      fireEvent.change(textarea, { target: { value: 'retained response' } })
      fireEvent.click(screen.getByText('Complete request'))

      const alert = await screen.findByRole('alert')
      await waitFor(() => expect(alert).toHaveFocus())
      expect(alert).toHaveTextContent(code)
      expect(alert).toHaveTextContent('Submitted: retained response')
      expect(alert).toHaveTextContent('Current authority')
      expect(api.getRequest).toHaveBeenCalledWith('change', 'action-1')
      fireEvent.click(within(alert).getByText('Return', { exact: true }))
      expect(onReturn).toHaveBeenCalledOnce()
      fireEvent.click(screen.getByText('Retry resolution'))
      await waitFor(() => expect(api.resolve).toHaveBeenLastCalledWith('change', 'action-1', expect.objectContaining({
        delivery_digest: 'c'.repeat(64), response: 'retained response',
      })))
    },
  )

  it('preserves complete decision context after resolution', () => {
    const stored = decisionRequest()
    stored.resolution = {
      request_id: 'decision-1', disposition: 'local', resolved_at: '', resolved_by: 'operator',
      selected_option_id: 'option-a', response: null, rationale: 'Selected for speed',
    }
    render(<NativeRequestResolver stored={stored} onResolved={vi.fn()} />)

    expect(screen.getByText('Recommended')).toBeInTheDocument()
    expect(screen.getByText('Confidence 80%')).toBeInTheDocument()
    expect(screen.getByTestId('persisted-resolution')).toHaveTextContent('Selected for speed')
    expect(screen.getByText('Resolved by operator.')).toBeInTheDocument()
    expect(screen.queryByText('Complete request')).not.toBeInTheDocument()
  })

  it('preserves action evidence, resume condition, response, and rationale after resolution', () => {
    const stored = actionRequest()
    stored.resolution = {
      request_id: 'action-1', disposition: 'material', resolved_at: '', resolved_by: 'operator',
      selected_option_id: null, response: 'signature=abc', rationale: 'Evidence accepted',
    }
    render(<NativeRequestResolver stored={stored} onResolved={vi.fn()} />)

    expect(screen.getAllByText(/signature=abc/)).toHaveLength(2)
    expect(screen.getByText(/Signature is supplied/)).toBeInTheDocument()
    expect(screen.getByText(/Response:/).parentElement).toHaveTextContent('signature=abc')
    expect(screen.getByText(/Rationale:/).parentElement).toHaveTextContent('Evidence accepted')
  })
})
