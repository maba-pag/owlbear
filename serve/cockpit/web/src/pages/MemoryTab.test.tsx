import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import type { MemoryEntry } from '../api/memories'
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

function memoryEntry(overrides: Partial<MemoryEntry> = {}): MemoryEntry {
  return {
    id: 'entry-1',
    title: 'Draft title',
    content: 'Draft content',
    categories: ['process'],
    confidence: 0.9,
    state: 'approved',
    outstanding_count: 0,
    score: 0.9,
    scope_agents: ['builder'],
    source_agent: 'builder',
    created_at: '2026-01-01T00:00:00+00:00',
    updated_at: '2026-01-01T00:00:00+00:00',
    approved_at: '2026-01-01T00:00:00+00:00',
    contested_by_task: null,
    ...overrides,
  }
}

async function openMemoryEntry(): Promise<void> {
  await waitFor(() => expect(document.querySelector('p-accordion')).toHaveClass('hydrated'))
  const accordion = document.querySelector('p-accordion')
  if (!accordion) {
    throw new Error('Memory entry accordion was not rendered')
  }
  accordion.dispatchEvent(new CustomEvent('update', { detail: { open: true } }))
  await waitFor(() => expect(screen.getByTestId('memory-edit-btn')).toBeInTheDocument())
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

  it('preserves a draft and supports explicit reapply after a structured conflict', async () => {
    const initialEntry = memoryEntry()
    const currentEntry = memoryEntry({
      title: 'Server title',
      content: 'Server content',
      updated_at: '2026-01-02T00:00:00+00:00',
    })
    const savedEntry = memoryEntry({ updated_at: '2026-01-03T00:00:00+00:00' })
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(response({ entries: [initialEntry], parse_errors: 0 }))
      .mockResolvedValueOnce(response({ code: 'MEM_CONFLICT', message: 'Entry revision is stale' }, false, 409))
      .mockResolvedValueOnce(response({ entries: [currentEntry], parse_errors: 0 }))
      .mockResolvedValueOnce(response({ entry: savedEntry }))
      .mockResolvedValueOnce(response({ entries: [savedEntry], parse_errors: 0 }))
    vi.stubGlobal('fetch', fetchMock)

    render(<MemoryTab />)
    expect(await screen.findByText('Draft title')).toBeInTheDocument()
    await openMemoryEntry()
    fireEvent.click(screen.getByTestId('memory-edit-btn'))
    fireEvent.click(await screen.findByTestId('memory-edit-save-btn'))

    expect(await screen.findByTestId('memory-conflict-current-title')).toHaveTextContent('Server title')
    expect(screen.getByTestId('memory-conflict-current-content')).toHaveTextContent('Server content')
    expect(screen.getByTestId('memory-conflict-draft-title')).toHaveTextContent('Draft title')
    expect(screen.getByTestId('memory-conflict-draft-content')).toHaveTextContent('Draft content')
    expect((screen.getByTestId('memory-edit-save-btn') as HTMLElement & { disabled?: boolean }).disabled).toBe(true)

    fireEvent.click(screen.getByTestId('memory-conflict-reapply'))
    await waitFor(() => expect(screen.queryByTestId('memory-conflict-panel')).not.toBeInTheDocument())
    fireEvent.click(screen.getByTestId('memory-edit-save-btn'))

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(5))
    const saveBody = JSON.parse(String(fetchMock.mock.calls[3][1]?.body)) as Record<string, unknown>
    expect(saveBody.expected_updated_at).toBe(currentEntry.updated_at)
    expect(saveBody.title).toBe(initialEntry.title)
  })

  it('supports generic conflict reload without resubmitting the stale revision', async () => {
    const initialEntry = memoryEntry()
    const currentEntry = memoryEntry({
      title: 'Reloaded title',
      content: 'Reloaded content',
      updated_at: '2026-01-02T00:00:00+00:00',
    })
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(response({ entries: [initialEntry], parse_errors: 0 }))
      .mockResolvedValueOnce(response({ message: 'Conflict' }, false, 409))
      .mockResolvedValueOnce(response({ entries: [currentEntry], parse_errors: 0 }))
      .mockResolvedValueOnce(response({ entry: currentEntry }))
      .mockResolvedValueOnce(response({ entries: [currentEntry], parse_errors: 0 }))
    vi.stubGlobal('fetch', fetchMock)

    render(<MemoryTab />)
    expect(await screen.findByText('Draft title')).toBeInTheDocument()
    await openMemoryEntry()
    fireEvent.click(screen.getByTestId('memory-edit-btn'))
    fireEvent.click(await screen.findByTestId('memory-edit-save-btn'))

    expect(await screen.findByTestId('memory-conflict-current-title')).toHaveTextContent('Reloaded title')
    fireEvent.click(screen.getByTestId('memory-conflict-reload'))
    await waitFor(() => expect(screen.queryByTestId('memory-conflict-panel')).not.toBeInTheDocument())
    fireEvent.click(screen.getByTestId('memory-edit-save-btn'))

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(5))
    const saveBody = JSON.parse(String(fetchMock.mock.calls[3][1]?.body)) as Record<string, unknown>
    expect(saveBody.expected_updated_at).toBe(currentEntry.updated_at)
    expect(saveBody.title).toBe(currentEntry.title)
    expect(saveBody.content).toBe(currentEntry.content)
  })

  it('keeps the draft visible after a validation mutation failure', async () => {
    const initialEntry = memoryEntry()
    const validationFetch = vi
      .fn()
      .mockResolvedValueOnce(response({ entries: [initialEntry], parse_errors: 0 }))
      .mockResolvedValueOnce(response({ detail: [{ loc: ['body', 'title'], msg: 'title is required' }] }, false, 422))
    vi.stubGlobal('fetch', validationFetch)

    render(<MemoryTab />)
    expect(await screen.findByText('Draft title')).toBeInTheDocument()
    await openMemoryEntry()
    fireEvent.click(screen.getByTestId('memory-edit-btn'))
    fireEvent.click(await screen.findByTestId('memory-edit-save-btn'))

    expect(await screen.findByTestId('memory-validation-errors')).toHaveTextContent('title is required')
    expect(screen.getByTestId('memory-edit-form')).toBeInTheDocument()
  })

  it('keeps the draft visible after a network mutation failure', async () => {
    const initialEntry = memoryEntry()
    const networkFetch = vi
      .fn()
      .mockResolvedValueOnce(response({ entries: [initialEntry], parse_errors: 0 }))
      .mockRejectedValueOnce(new TypeError('Failed to fetch'))
    vi.stubGlobal('fetch', networkFetch)

    render(<MemoryTab />)
    expect(await screen.findByText('Draft title')).toBeInTheDocument()
    await openMemoryEntry()
    fireEvent.click(screen.getByTestId('memory-edit-btn'))
    fireEvent.click(await screen.findByTestId('memory-edit-save-btn'))

    expect(await screen.findByTestId('memory-occ-banner')).toHaveTextContent('Memory mutation failed')
    expect(screen.getByTestId('memory-edit-form')).toBeInTheDocument()
  })
})
