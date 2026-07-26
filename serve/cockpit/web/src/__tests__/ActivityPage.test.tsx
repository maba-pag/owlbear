import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import ActivityPage from '../pages/ActivityPage'
import type { NativeActivityEntry } from '../api/native'

function entry(identity: string, jobId: number | null, timestamp: string, kind: string): NativeActivityEntry {
  return { identity, job_id: jobId, timestamp, kind, attempt: null, finding: null, receipt: null, request: null }
}

const hooks = vi.hoisted(() => ({
  activity: {
    items: [] as NativeActivityEntry[], nextCursor: 'next', isLoading: false, isLoadingMore: false,
    error: null, retryFromStart: false, loadMore: vi.fn(), retry: vi.fn(),
  },
}))

vi.mock('../hooks/NativeChangeProvider', () => ({
  useNativeChangeSelection: () => ({ selectedSummary: { change_id: 'change', state: 'loaded' } }),
}))
vi.mock('../hooks/useNativeResources', () => ({ useNativeActivity: () => hooks.activity }))

describe('ActivityPage', () => {
  beforeEach(() => {
    hooks.activity.items = [
      entry('job-1-started', 1, '2026-01-01T00:00:00Z', 'attempt'),
      entry('change-finding', null, '2026-01-01T00:01:00Z', 'finding'),
      entry('job-1-released', 1, '2026-01-01T00:02:00Z', 'attempt'),
      entry('job-2-receipt', 2, '2026-01-01T00:03:00Z', 'receipt'),
    ]
    vi.clearAllMocks()
  })

  it('defaults to the latest immutable state per job plus change-level history', () => {
    render(<ActivityPage />)
    expect(screen.queryByText('job-1-started')).not.toBeInTheDocument()
    expect(screen.getByText(/job-1-released/)).toBeInTheDocument()
    expect(screen.getByText(/change-finding/)).toBeInTheDocument()
    expect(screen.getByText(/job-2-receipt/)).toBeInTheDocument()
    expect(screen.queryByText('Load more history')).not.toBeInTheDocument()
  })

  it('exposes full retained history and pagination without mutation commands', () => {
    const { container } = render(<ActivityPage />)
    fireEvent.click(screen.getByText('Full history'))
    expect(screen.getByText(/job-1-started/)).toBeInTheDocument()
    fireEvent.click(screen.getByText('Load more history'))
    expect(hooks.activity.loadMore).toHaveBeenCalledOnce()
    expect(container).not.toHaveTextContent('Edit')
    expect(container).not.toHaveTextContent('Move')
    expect(container).not.toHaveTextContent('Delete')
  })
})
