import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useBoard } from '../hooks/useBoard'
import { useSSEEvent } from '../hooks/EventSourceProvider'

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

function tasksFetchCount(fetchMock: ReturnType<typeof vi.fn>): number {
  return fetchMock.mock.calls.filter((c) => (c[0] as string).includes('/api/tasks')).length
}

describe('TestFromAC_UseBoardDecisionsWiring', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    sseState.status = 'open'
    sseState.tasksMtime = null
    sseState.decisionsMtime = null
    vi.mocked(useSSEEvent).mockClear()
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  it('calls useSSEEvent for both tasks and decisions channels after mount', async () => {
    vi.stubGlobal('fetch', makeFetch())
    renderHook(() => useBoard())
    await act(async () => {})

    expect(vi.mocked(useSSEEvent)).toHaveBeenCalledWith('tasks-changed')
    expect(vi.mocked(useSSEEvent)).toHaveBeenCalledWith('decisions-changed')
  })

  it('useBoard result has lastDecisionsMtime property (initially null)', async () => {
    vi.stubGlobal('fetch', makeFetch())
    const { result } = renderHook(() => useBoard())
    await act(async () => {})

    expect(result.current).toHaveProperty('lastDecisionsMtime')
    expect(result.current.lastDecisionsMtime).toBeNull()
  })

  it('lastDecisionsMtime updates when decisions-changed mtime changes', async () => {
    vi.stubGlobal('fetch', makeFetch())
    const { result, rerender } = renderHook(() => useBoard())
    await act(async () => {})

    sseState.decisionsMtime = 88_000
    await act(async () => {
      rerender()
    })

    expect(result.current.lastDecisionsMtime).toBe(88_000)
  })

  it('decisions-changed mtime does not trigger task refetch', async () => {
    const fetchMock = makeFetch()
    vi.stubGlobal('fetch', fetchMock)
    const { rerender } = renderHook(() => useBoard())
    await act(async () => {})
    const countBeforeDecisionsChange = tasksFetchCount(fetchMock)

    sseState.decisionsMtime = 55_000
    await act(async () => {
      rerender()
    })

    expect(tasksFetchCount(fetchMock)).toBe(countBeforeDecisionsChange)
  })

  it('tasks-changed mtime triggers refetch and does not alter lastDecisionsMtime', async () => {
    const fetchMock = makeFetch()
    vi.stubGlobal('fetch', fetchMock)
    const { result, rerender } = renderHook(() => useBoard())
    await act(async () => {})

    sseState.decisionsMtime = 1_000
    await act(async () => {
      rerender()
    })
    const countBeforeTasksChange = tasksFetchCount(fetchMock)

    sseState.tasksMtime = 2_000
    await act(async () => {
      rerender()
    })

    expect(tasksFetchCount(fetchMock)).toBeGreaterThan(countBeforeTasksChange)
    expect(result.current.lastDecisionsMtime).toBe(1_000)
  })
})
