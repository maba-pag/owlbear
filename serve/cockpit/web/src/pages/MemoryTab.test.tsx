import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import MemoryTab from './MemoryTab'

vi.mock('../hooks/useCleanupFlow', () => ({
  useMemoryPurgeFlow: () => ({
    phase: 'idle',
    threshold: '30',
    preview: null,
    receipt: null,
    error: null,
    setThreshold: vi.fn(),
    requestPreview: vi.fn(),
    confirmPurge: vi.fn(),
    cancelPurge: vi.fn(),
  }),
}))

function response(body: unknown, ok = true, status = 200): Response {
  return {
    ok,
    status,
    json: async () => body,
  } as Response
}

describe('MemoryTab load state', () => {
  it('shows retry instead of the empty state when the initial load fails', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(response({ message: 'Memory service unavailable' }, false, 503))
      .mockResolvedValueOnce(response({ entries: [], parse_errors: 0 }))
    vi.stubGlobal('fetch', fetchMock)

    render(<MemoryTab />)

    expect(await screen.findByRole('alert')).toHaveTextContent('Memory service unavailable')
    expect(screen.queryByTestId('memory-empty-state')).not.toBeInTheDocument()

    fireEvent.click(screen.getByTestId('memory-retry'))

    await waitFor(() => expect(screen.getByTestId('memory-empty-state')).toBeInTheDocument())
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })

  it('shows an error for a malformed successful response', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response({ entries: null })))

    render(<MemoryTab />)

    expect(await screen.findByRole('alert')).toHaveTextContent('Malformed memory response')
    expect(screen.queryByTestId('memory-empty-state')).not.toBeInTheDocument()
  })

  it('shows an error when the network request rejects', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))

    render(<MemoryTab />)

    expect(await screen.findByRole('alert')).toHaveTextContent('Failed to fetch')
    expect(screen.queryByTestId('memory-empty-state')).not.toBeInTheDocument()
  })

  it('shows the successful empty state for a valid empty response', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response({ entries: [], parse_errors: 0 })))

    render(<MemoryTab />)

    expect(await screen.findByTestId('memory-empty-state')).toBeInTheDocument()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('keeps prior entries and marks them stale after a failed refresh', async () => {
    const entries = [{
      id: 'entry-1',
      title: 'Existing memory',
      content: 'Existing content',
      categories: ['process'],
      confidence: 0.9,
      state: 'approved',
      outstanding_count: 0,
      score: 0.9,
      scope_agents: [],
      source_agent: 'builder',
      created_at: '2026-01-01T00:00:00+00:00',
      updated_at: '2026-01-01T00:00:00+00:00',
      approved_at: '2026-01-01T00:00:00+00:00',
      contested_by_task: null,
    }]
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(response({ entries, parse_errors: 0 }))
      .mockResolvedValueOnce(response({ message: 'Memory service unavailable' }, false, 503))
    vi.stubGlobal('fetch', fetchMock)

    render(<MemoryTab />)
    expect(await screen.findByText('Existing memory')).toBeInTheDocument()
    Object.defineProperty(document, 'visibilityState', { configurable: true, value: 'visible' })
    document.dispatchEvent(new Event('visibilitychange'))

    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('Memory entries may be stale'))
    expect(screen.getByRole('alert')).toHaveTextContent('Memory service unavailable')
    expect(screen.getByText('Existing memory')).toBeInTheDocument()
  })

  it('keeps parse-error diagnostics distinct after a failed refresh', async () => {
    const entries = [{
      id: 'entry-1', title: 'Existing memory', content: 'Existing content', categories: ['process'], confidence: 0.9,
      state: 'approved', outstanding_count: 0, score: 0.9, scope_agents: [], source_agent: 'builder',
      created_at: '2026-01-01T00:00:00+00:00', updated_at: '2026-01-01T00:00:00+00:00',
      approved_at: '2026-01-01T00:00:00+00:00', contested_by_task: null,
    }]
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(response({ entries, parse_errors: 2 }))
      .mockResolvedValueOnce(response({ message: 'Network unavailable' }, false, 503))
    vi.stubGlobal('fetch', fetchMock)

    render(<MemoryTab />)
    expect(await screen.findByTestId('parse-errors-warning')).toHaveTextContent('2 entries')
    Object.defineProperty(document, 'visibilityState', { configurable: true, value: 'visible' })
    document.dispatchEvent(new Event('visibilitychange'))

    await waitFor(() => expect(screen.getByRole('alert')).toBeInTheDocument())
    expect(screen.getByTestId('parse-errors-warning')).toHaveTextContent('2 entries')
  })
})
