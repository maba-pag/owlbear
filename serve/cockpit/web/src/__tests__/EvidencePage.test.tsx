import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import EvidencePage from '../pages/EvidencePage'
import type { NativeJobProjection, NativeReceipt } from '../api/native'

const receipt = (id: string, kind = 'build'): NativeReceipt => ({
  schema_version: 1, receipt_id: id, kind, change_id: 'change', delivery_digest: 'a'.repeat(64), issued_at: '',
  impact_closure: { paths: ['serve/cockpit'], authority_targets: ['DN-011'] },
  payload: { code_revision: `sha-${id}` },
})

const currentJob = {
  job_id: 1, token: 'token', kind: 'build', priority: 1, change_id: 'change', delivery_digest: 'a'.repeat(64),
  target_node_id: 'DN-011', title: 'Build', outcome: 'Outcome', acceptance: [], modules: [], interfaces: [], proof: 'PROOF-012',
  dependency_ready: true, claim_id: null, disposition: 'pending', requests: [], block_id: null, attempt: null, finding: null,
  receipt: receipt('current'), validity: { code: 'CURRENT', detail: 'receipt is current' },
} satisfies NativeJobProjection

const hooks = vi.hoisted(() => ({
  jobs: { items: [] as NativeJobProjection[], nextCursor: null, isLoading: false, isLoadingMore: false, error: null, retryFromStart: false, loadMore: vi.fn(), retry: vi.fn() },
  receipts: { items: [] as NativeReceipt[], nextCursor: null, isLoading: false, isLoadingMore: false, error: null, retryFromStart: false, loadMore: vi.fn(), retry: vi.fn() },
  invalidation: {
    data: {
      invalidation_id: 'inv-1', supersession_receipt_id: 'supersession', issued_at: '',
      affected_receipt_ids: ['stale'], corrective_finding_ids: ['finding-1'], corrective_job_ids: [4],
    }, error: null, isLoading: false, retry: vi.fn(),
  },
}))

vi.mock('../hooks/NativeChangeProvider', () => ({
  useNativeChangeSelection: () => ({ selectedSummary: { change_id: 'change', state: 'loaded' } }),
}))
vi.mock('../hooks/useNativeResources', () => ({
  useNativeJobs: () => hooks.jobs,
  useNativeReceipts: () => hooks.receipts,
  useNativeInvalidationDetail: () => hooks.invalidation,
}))

describe('EvidencePage', () => {
  beforeEach(() => {
    hooks.jobs.items = [currentJob]
    hooks.receipts.items = [receipt('stale'), receipt('supersession', 'supersession')]
    vi.clearAllMocks()
  })

  it('defaults to current job receipts with code revision and validity', () => {
    render(<EvidencePage />)
    expect(screen.getByText('current')).toBeInTheDocument()
    expect(screen.getByText(/sha-current/)).toBeInTheDocument()
    expect(screen.getByText('CURRENT')).toBeInTheDocument()
    expect(screen.queryByText('stale')).not.toBeInTheDocument()
  })

  it('shows full history and labels supersession closure without mutations', () => {
    const { container } = render(<EvidencePage />)
    fireEvent.click(screen.getByText('Full history'))
    expect(screen.getByText('stale')).toBeInTheDocument()
    expect(screen.getByText('HISTORICAL')).toBeInTheDocument()
    fireEvent.click(screen.getByText('Inspect supersession chain'))
    expect(screen.getByTestId('supersession-chain')).toHaveTextContent('stale')
    expect(screen.getByTestId('supersession-chain')).toHaveTextContent('finding-1')
    expect(screen.getByTestId('supersession-chain')).toHaveTextContent('#4')
    expect(container).not.toHaveTextContent('Edit receipt')
    expect(container).not.toHaveTextContent('Delete receipt')
  })
})
