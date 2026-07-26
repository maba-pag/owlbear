import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, useLocation } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { NativeApiError, type NativeJobProjection } from '../api/native'
import DeliveryJobBoard from '../components/DeliveryJobBoard'

const api = vi.hoisted(() => ({
  priority: vi.fn(),
  cancel: vi.fn(),
  release: vi.fn(),
}))

vi.mock('../api/native', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/native')>()
  return {
    ...actual,
    setNativeJobPriority: api.priority,
    cancelNativeJob: api.cancel,
    releaseNativeJob: api.release,
  }
})

function job(overrides: Partial<NativeJobProjection> = {}): NativeJobProjection {
  return {
    job_id: 20,
    token: 'token-1',
    kind: 'build',
    priority: 5,
    change_id: 'change',
    delivery_digest: 'a'.repeat(64),
    target_node_id: 'DN-003',
    title: 'Build native runtime',
    outcome: 'Immutable job purpose',
    acceptance: ['AC-1'],
    modules: ['MOD-001'],
    interfaces: ['IF-003'],
    proof: 'PROOF-003',
    dependency_ready: false,
    claim_id: null,
    disposition: 'pending',
    requests: [{
      request: {
        request_id: 'request-1', kind: 'action', title: 'Evidence', summary: 'Needed', body: 'Body', agent: 'builder',
        created_at: '2026-07-26T10:00:00Z', change_id: 'change', delivery_digest: 'a'.repeat(64), target_node_id: 'DN-003', job_ids: [20],
      },
      resolution: null,
    }],
    block_id: 'block-1',
    attempt: null,
    finding: { finding_id: 'finding-1', created_at: '2026-07-26T10:01:00Z' },
    receipt: { receipt_id: 'receipt-1', kind: 'build', issued_at: '2026-07-26T10:02:00Z' },
    validity: { code: 'ERR_RECEIPT_CODE_PATH_STALE', detail: 'stale' },
    ...overrides,
  }
}

function LocationProbe() {
  const location = useLocation()
  return <output data-testid="location">{`${location.pathname}${location.search}`}</output>
}

function renderBoard(jobs: NativeJobProjection[] = [job()], retry = vi.fn()) {
  return render(
    <MemoryRouter initialEntries={['/delivery?change=change']}>
      <DeliveryJobBoard changeId="change" jobs={jobs} isLoading={false} error={null} retry={retry} />
      <LocationProbe />
    </MemoryRouter>,
  )
}

describe('DeliveryJobBoard', () => {
  afterEach(() => {
    vi.clearAllMocks()
  })

  it('groups immutable job kinds and exposes complete operational signals', () => {
    renderBoard([
      job({ kind: 'plan', job_id: 1 }),
      job({ kind: 'build', job_id: 2 }),
      job({ kind: 'accept', job_id: 3 }),
      job({ kind: 'audit', job_id: 4 }),
    ])

    expect(screen.getByText('plan')).toBeInTheDocument()
    expect(screen.getByText('build')).toBeInTheDocument()
    expect(screen.getByText('accept')).toBeInTheDocument()
    expect(screen.getByText('audit')).toBeInTheDocument()
    expect(screen.getAllByText('Waiting')).toHaveLength(4)
    expect(screen.getAllByText('ERR_RECEIPT_CODE_PATH_STALE')).toHaveLength(4)
    expect(screen.getAllByText('finding-1')).toHaveLength(4)
    expect(screen.getAllByText('receipt-1')).toHaveLength(4)
    expect(document.querySelectorAll('[data-job-id]')).toHaveLength(4)
    for (const card of document.querySelectorAll('[data-job-id]')) {
      expect(card).toHaveTextContent('DN-003')
    }
  })

  it('offers only intent-specific commands and no drag/status/edit surface', () => {
    const { container } = renderBoard()

    for (const command of ['Prioritize', 'Cancel', 'Inspect', 'Resolve request']) {
      expect(screen.getByText(command)).toBeInTheDocument()
    }
    expect(screen.getByText('Release claim').closest('p-button')).toHaveProperty('disabled', true)
    expect(container.querySelector('[draggable="true"]')).toBeNull()
    expect(screen.queryByText('Move')).not.toBeInTheDocument()
    expect(screen.queryByText('Edit fields')).not.toBeInTheDocument()
    expect(screen.queryByText('Change kind')).not.toBeInTheDocument()
  })

  it('refreshes after priority success with exact OCC identity', async () => {
    api.priority.mockResolvedValue({ job: {} })
    const retry = vi.fn()
    renderBoard([job()], retry)

    fireEvent.click(screen.getByText('Prioritize'))

    await waitFor(() => expect(api.priority).toHaveBeenCalledOnce())
    expect(api.priority).toHaveBeenCalledWith('change', expect.objectContaining({
      job_id: 20,
      delivery_digest: 'a'.repeat(64),
      expected_token: 'token-1',
      priority: 5,
    }))
    expect(retry).toHaveBeenCalledOnce()
  })

  it('retains card and submitted priority intent on 409 with current authority and Retry', async () => {
    api.priority.mockRejectedValue(
      new NativeApiError(409, {
        code: 'ERR_JOB_ADMIN_OCC_STALE',
        detail: 'job OCC token is stale',
        current_delivery_digest: 'b'.repeat(64),
        current: {
          job: {
            schema_version: 1, job_id: 20, kind: 'build', priority: 8, created_at: '', updated_at: '',
            change_id: 'change', delivery_digest: 'b'.repeat(64), target_node_id: 'DN-003', disposition: 'pending',
            claim_id: null, attempt_id: null, pending_request_ids: [], predecessor_job_ids: [], receipt_id: null,
          },
          token: 'token-2',
        },
      }),
    )
    renderBoard()

    fireEvent.click(screen.getByText('Prioritize'))

    const conflict = await screen.findByTestId('job-conflict-20')
    expect(conflict).toHaveTextContent('ERR_JOB_ADMIN_OCC_STALE')
    expect(conflict).toHaveTextContent('Submitted: priority 5')
    expect(conflict).toHaveTextContent('Current token: token-2')
    expect(conflict).toHaveTextContent(`Current digest: ${'b'.repeat(64)}`)
    expect(conflict).toHaveTextContent('Current job: priority 8, pending, unclaimed')
    expect(screen.getByText('Build native runtime')).toBeInTheDocument()
    fireEvent.click(screen.getByText('Retry'))
    await waitFor(() => expect(api.priority).toHaveBeenLastCalledWith('change', expect.objectContaining({
      expected_token: 'token-2', delivery_digest: 'b'.repeat(64), priority: 5,
    })))
  })

  it('sends release identity for claimed jobs and navigates inspect/request links', async () => {
    api.release.mockResolvedValue({ job: {} })
    const claimed = job({
      claim_id: 'claim-1',
      attempt: {
        attempt_id: 'attempt-1', claim_id: 'claim-1', job_id: 20, actor_id: 'builder', process_id: 'process-1',
        timestamp: new Date().toISOString(), kind: 'started',
      },
    })
    renderBoard([claimed])

    fireEvent.click(screen.getByText('Release claim'))
    await waitFor(() => expect(api.release).toHaveBeenCalledWith('change', expect.objectContaining({
      job_id: 20, attempt_id: 'attempt-1', claim_id: 'claim-1', actor_id: 'builder', process_id: 'process-1',
    })))
    fireEvent.click(screen.getByText('Inspect'))
    expect(screen.getByTestId('location')).toHaveTextContent('/delivery?change=change&job=20')
    fireEvent.click(screen.getByText('Resolve request'))
    expect(screen.getByTestId('location')).toHaveTextContent('/delivery?change=change&request=request-1')
  })

  it('disables administration for terminal jobs and sends exact cancel identity for eligible jobs', async () => {
    const terminal = job({ job_id: 30, disposition: 'cancelled' })
    const eligible = job({ job_id: 31, token: 'token-31', requests: [] })
    api.cancel.mockResolvedValue({ job: {} })
    renderBoard([terminal, eligible])

    const terminalCommands = screen.getByLabelText('Commands for job 30')
    expect(terminalCommands.querySelector('p-button')?.disabled).toBe(true)
    fireEvent.click(screen.getByLabelText('Commands for job 31').querySelectorAll('p-button')[1])

    await waitFor(() => expect(api.cancel).toHaveBeenCalledWith('change', expect.objectContaining({
      job_id: 31,
      delivery_digest: 'a'.repeat(64),
      expected_token: 'token-31',
    })))
  })

  it('treats released historical attempts as unclaimed and hides resolved request actions', () => {
    const released = job({
      claim_id: null,
      attempt: {
        attempt_id: 'attempt-old', claim_id: 'claim-old', job_id: 20, actor_id: 'builder', process_id: 'process-old',
        timestamp: '2026-07-26T10:00:00Z', kind: 'released',
      },
      requests: [{
        ...job().requests[0],
        resolution: { disposition: 'material' },
      }],
    })
    renderBoard([released])

    const commands = screen.getByLabelText('Commands for job 20')
    const buttons = commands.querySelectorAll('p-button')
    expect(buttons[0].disabled).toBe(false)
    expect(buttons[1].disabled).toBe(false)
    expect(buttons[2].disabled).toBe(true)
    expect(screen.queryByText('Resolve request')).not.toBeInTheDocument()
    expect(screen.getByText('Unclaimed')).toBeInTheDocument()
    expect(screen.getByText('released attempt-old')).toBeInTheDocument()
  })

  it('requires authority refresh when release ownership identity changes', async () => {
    const claimed = job({
      claim_id: 'claim-old',
      attempt: {
        attempt_id: 'attempt-old', claim_id: 'claim-old', job_id: 20, actor_id: 'builder', process_id: 'process-old',
        timestamp: new Date().toISOString(), kind: 'started',
      },
    })
    api.release
      .mockRejectedValueOnce(new NativeApiError(409, {
        code: 'ERR_RELEASE_NON_OWNER', detail: 'claim changed', current_delivery_digest: 'b'.repeat(64),
        current: {
          job: {
            schema_version: 1, job_id: 20, kind: 'build', priority: 5, created_at: '', updated_at: '', change_id: 'change',
            delivery_digest: 'b'.repeat(64), target_node_id: 'DN-003', disposition: 'pending', claim_id: 'claim-new',
            attempt_id: 'attempt-new', pending_request_ids: [], predecessor_job_ids: [], receipt_id: null,
          },
          token: 'token-new',
        },
      }))
    const refresh = vi.fn()
    renderBoard([claimed], refresh)

    fireEvent.click(screen.getByText('Release claim'))
    const conflict = await screen.findByTestId('job-conflict-20')
    expect(conflict).toHaveTextContent('Current job: priority 5, pending, claimed')
    expect(screen.queryByText('Retry')).not.toBeInTheDocument()
    fireEvent.click(screen.getByText('Refresh authority'))
    expect(refresh).toHaveBeenCalledOnce()
    expect(api.release).toHaveBeenCalledTimes(1)
  })

  it('never retries ERR_RELEASE_NON_OWNER when actor/process authority is unavailable', async () => {
    const claimed = job({
      claim_id: 'claim-1',
      attempt: {
        attempt_id: 'attempt-1', claim_id: 'claim-1', job_id: 20, actor_id: 'old-actor', process_id: 'old-process',
        timestamp: new Date().toISOString(), kind: 'started',
      },
    })
    api.release.mockRejectedValue(new NativeApiError(409, {
      code: 'ERR_RELEASE_NON_OWNER', detail: 'actor changed', current_delivery_digest: claimed.delivery_digest,
      current: {
        job: {
          schema_version: 1, job_id: 20, kind: 'build', priority: 5, created_at: '', updated_at: '', change_id: 'change',
          delivery_digest: claimed.delivery_digest, target_node_id: 'DN-003', disposition: 'pending', claim_id: 'claim-1',
          attempt_id: 'attempt-1', pending_request_ids: [], predecessor_job_ids: [], receipt_id: null,
        }, token: 'token-current',
      },
    }))
    const refresh = vi.fn()
    renderBoard([claimed], refresh)

    fireEvent.click(screen.getByText('Release claim'))
    await screen.findByTestId('job-conflict-20')

    expect(screen.queryByText('Retry')).not.toBeInTheDocument()
    const primaryRelease = screen.getByLabelText('Commands for job 20').querySelectorAll('p-button')[2]
    expect(primaryRelease.disabled).toBe(true)
    fireEvent.click(primaryRelease)
    expect(api.release).toHaveBeenCalledTimes(1)
    fireEvent.click(screen.getByText('Refresh authority'))
    expect(refresh).toHaveBeenCalledOnce()
  })
})
