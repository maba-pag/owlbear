import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useBoard } from '../hooks/useBoard'

const sseState = vi.hoisted(() => ({
  status: 'connecting' as 'connecting' | 'open' | 'closed',
  tasksMtime: null as number | null,
  decisionsMtime: null as number | null,
}))

vi.mock('../hooks/EventSourceProvider', () => ({
  useSSEEvent: vi.fn((eventType: string) => {
    if (eventType === 'tasks-changed') {
      return { mtime: sseState.tasksMtime, status: sseState.status }
    }
    if (eventType === 'decisions-changed') {
      return { mtime: sseState.decisionsMtime, status: sseState.status }
    }
    return { mtime: null, status: sseState.status }
  }),
}))

const BOARD = {
  statuses: [{ name: 'backlog' }],
  priorities: ['important'],
  valid_transitions: { backlog: [] } as Record<string, string[]>,
}

const TASKS_V1 = {
  tasks: [
    {
      id: 1,
      title: 'T1',
      status: 'backlog',
      priority: 'important',
      tags: [],
      blocked: false,
      block_reason: null,
      claimed: false,
      updated: '2026-01-01',
    },
  ],
  mtime: 1000,
}

function makeFetch(tasksData: unknown = TASKS_V1): ReturnType<typeof vi.fn> {
  return vi.fn((url: string) => {
    if (url.includes('/api/board')) {
      return Promise.resolve({ ok: true, json: () => Promise.resolve(BOARD) })
    }
    if (url.includes('/api/tasks')) {
      return Promise.resolve({ ok: true, json: () => Promise.resolve(tasksData) })
    }
    return Promise.resolve({ ok: false, status: 404 })
  })
}

function makeFailFetch(): ReturnType<typeof vi.fn> {
  return vi.fn((url: string) => {
    if (url.includes('/api/board')) {
      return Promise.resolve({ ok: true, json: () => Promise.resolve(BOARD) })
    }
    return Promise.resolve({ ok: false, status: 503 })
  })
}

function tasksFetchCount(fetchMock: ReturnType<typeof vi.fn>): number {
  return fetchMock.mock.calls.filter((c) => (c[0] as string).includes('/api/tasks')).length
}

describe('TestFromAC_UseBoardSSEIntegration', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    sseState.status = 'connecting'
    sseState.tasksMtime = null
    sseState.decisionsMtime = null
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  it('suppresses interval polling when SSE status is open', async () => {
    const fetchMock = makeFetch()
    vi.stubGlobal('fetch', fetchMock)
    sseState.status = 'open'

    renderHook(() => useBoard())
    await act(async () => {})
    const countAfterMount = tasksFetchCount(fetchMock)

    await act(async () => {
      vi.advanceTimersByTime(3001)
    })

    expect(tasksFetchCount(fetchMock)).toBe(countAfterMount)
  })

  it('polling resumes when SSE moves from open to closed', async () => {
    const fetchMock = makeFetch()
    vi.stubGlobal('fetch', fetchMock)
    sseState.status = 'open'

    const { rerender } = renderHook(() => useBoard())
    await act(async () => {})

    await act(async () => {
      vi.advanceTimersByTime(3001)
    })
    const countWhileOpen = tasksFetchCount(fetchMock)

    sseState.status = 'closed'
    await act(async () => {
      rerender()
    })
    await act(async () => {})
    await act(async () => {
      vi.advanceTimersByTime(3001)
    })

    expect(tasksFetchCount(fetchMock)).toBeGreaterThan(countWhileOpen)
  })

  it('triggers refetch when tasks-changed mtime changes while SSE is open', async () => {
    const fetchMock = makeFetch()
    vi.stubGlobal('fetch', fetchMock)

    sseState.status = 'open'
    sseState.tasksMtime = null
    const { rerender } = renderHook(() => useBoard())
    await act(async () => {})
    const countBeforeEvent = tasksFetchCount(fetchMock)

    sseState.tasksMtime = 9001
    await act(async () => {
      rerender()
    })

    expect(tasksFetchCount(fetchMock)).toBeGreaterThan(countBeforeEvent)
  })

  it('does not trigger refetch when only decisions-changed mtime changes', async () => {
    const fetchMock = makeFetch()
    vi.stubGlobal('fetch', fetchMock)

    sseState.status = 'open'
    const { rerender } = renderHook(() => useBoard())
    await act(async () => {})
    const countBeforeDecisionsEvent = tasksFetchCount(fetchMock)

    sseState.decisionsMtime = 9100
    await act(async () => {
      rerender()
    })

    expect(tasksFetchCount(fetchMock)).toBe(countBeforeDecisionsEvent)
  })

  it('returns health=green while SSE status is open', async () => {
    vi.stubGlobal('fetch', makeFailFetch())
    sseState.status = 'open'

    const { result } = renderHook(() => useBoard())
    await act(async () => {})

    expect(result.current.health).toBe('green')
  })

  it('returns health=yellow while SSE status is connecting', async () => {
    vi.stubGlobal('fetch', makeFetch())
    sseState.status = 'connecting'

    const { result } = renderHook(() => useBoard())
    await act(async () => {})

    expect(result.current.health).toBe('yellow')
  })

  it('falls through to polling health when SSE status is closed', async () => {
    vi.stubGlobal('fetch', makeFetch())
    sseState.status = 'closed'

    const { result } = renderHook(() => useBoard())
    await act(async () => {})

    expect(result.current.health).toBe('green')
  })

  it('returns all UseBoardResult fields including health', async () => {
    vi.stubGlobal('fetch', makeFetch())

    const { result } = renderHook(() => useBoard())
    await act(async () => {})

    expect(result.current).toHaveProperty('board')
    expect(result.current).toHaveProperty('tasks')
    expect(result.current).toHaveProperty('loading')
    expect(result.current).toHaveProperty('error')
    expect(result.current).toHaveProperty('isFetching')
    expect(result.current).toHaveProperty('isStale')
    expect(result.current).toHaveProperty('refetchTasks')
    expect(result.current).toHaveProperty('health')
    expect(['green', 'yellow', 'red']).toContain(result.current.health)
  })
})

