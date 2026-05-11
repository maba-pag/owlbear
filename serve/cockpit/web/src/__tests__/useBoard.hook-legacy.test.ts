/**
 * Workflow behavior tests967: useBoard hook extracted to hooks/useBoard.ts.
 *
 * Covers: 3s setInterval polling, mtime-aware skip (no re-render on same
 * mtime), /api/board single-mount fetch, full return interface including
 * isFetching/isStale/refetchTasks, skip-when-in-flight (AC #5), AbortController
 * on unmount, and error/stale traffic-light states.
 *
 * All tests are RED (failing) until the builder creates hooks/useBoard.ts and
 * updates KanbanBoard.tsx to import from there.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useBoard } from '../hooks/useBoard'

vi.mock('../hooks/EventSourceProvider', () => ({
  useSSEEvent: vi.fn(() => ({ mtime: null, status: 'closed' as const })),
}))

// ─── Expected hook interface ──────────────────────────────────────────────────

interface UseBoardResult {
  board: unknown
  tasks: unknown[]
  loading: boolean
  error: string | null
  isFetching: boolean
  isStale: boolean
  health: string
  refetchTasks: () => void
}

// ─── Fixtures ─────────────────────────────────────────────────────────────────

const BOARD = {
  statuses: [{ name: 'backlog' }],
  priorities: ['important'],
  valid_transitions: { backlog: [] } as Record<string, string[]>,
}

const TASK_1 = {
  id: 1,
  title: 'T1',
  status: 'backlog',
  priority: 'important',
  tags: [],
  blocked: false,
  block_reason: null,
  claimed: false,
}

const TASK_2 = {
  id: 2,
  title: 'T2',
  status: 'backlog',
  priority: 'important',
  tags: [],
  blocked: false,
  block_reason: null,
  claimed: false,
}

const TASKS_R1 = { tasks: [TASK_1], mtime: 1000 }
const TASKS_R2 = { tasks: [TASK_2], mtime: 2000 }

function boardFetch(tasksPayload: unknown) {
  return vi.fn((url: string) => {
    if ((url as string).includes('/api/board')) {
      return Promise.resolve({ ok: true, json: () => Promise.resolve(BOARD) })
    }
    return Promise.resolve({ ok: true, json: () => Promise.resolve(tasksPayload) })
  })
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('TestFromAC_useBoardHook967', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  // ─── AC1: 3-second polling via setInterval ─────────────────────────────────

  describe('3-second polling interval', () => {
    it('fetches /api/tasks on mount and polls again after 3 seconds', async () => {
      const fetchMock = boardFetch(TASKS_R1)
      vi.stubGlobal('fetch', fetchMock)
      renderHook(() => useBoard())
      await act(async () => {})
      const callsAtMount = fetchMock.mock.calls.filter((c) =>
        (c[0] as string).includes('/api/tasks'),
      ).length
      await act(async () => {
        vi.advanceTimersByTime(3000)
      })
      const callsAfter3s = fetchMock.mock.calls.filter((c) =>
        (c[0] as string).includes('/api/tasks'),
      ).length
      expect(callsAfter3s).toBeGreaterThan(callsAtMount)
    })

    it('does not fire an extra poll tick before 3 seconds have elapsed', async () => {
      const fetchMock = boardFetch(TASKS_R1)
      vi.stubGlobal('fetch', fetchMock)
      renderHook(() => useBoard())
      await act(async () => {})
      const callsAtMount = fetchMock.mock.calls.filter((c) =>
        (c[0] as string).includes('/api/tasks'),
      ).length
      await act(async () => {
        vi.advanceTimersByTime(2999)
      })
      const callsBefore3s = fetchMock.mock.calls.filter((c) =>
        (c[0] as string).includes('/api/tasks'),
      ).length
      expect(callsBefore3s).toBe(callsAtMount)
    })

    it('polls at least 3 times after 9 seconds', async () => {
      const fetchMock = boardFetch(TASKS_R1)
      vi.stubGlobal('fetch', fetchMock)
      renderHook(() => useBoard())
      await act(async () => {
        vi.advanceTimersByTime(3000)
      })
      await act(async () => {
        vi.advanceTimersByTime(3000)
      })
      await act(async () => {
        vi.advanceTimersByTime(3000)
      })
      const tasksCalls = fetchMock.mock.calls.filter((c) =>
        (c[0] as string).includes('/api/tasks'),
      ).length
      expect(tasksCalls).toBeGreaterThanOrEqual(3)
    })
  })

  // ─── AC2: useRef stores lastMtime; skips setTasks when mtime unchanged ─────

  describe('mtime-aware skip', () => {
    it('keeps the same tasks array reference when mtime is unchanged across polls', async () => {
      const fetchMock = boardFetch(TASKS_R1) // always returns mtime 1000
      vi.stubGlobal('fetch', fetchMock)
      const { result } = renderHook(() => useBoard())
      await act(async () => {})
      const tasksRef = result.current.tasks
      await act(async () => {
        vi.advanceTimersByTime(3000)
      })
      // Poll fired but mtime unchanged — tasks reference must not change
      expect(result.current.tasks).toBe(tasksRef)
    })

    it('updates tasks array reference when mtime changes between polls', async () => {
      let callCount = 0
      const fetchMock = vi.fn((url: string) => {
        if ((url as string).includes('/api/board')) {
          return Promise.resolve({ ok: true, json: () => Promise.resolve(BOARD) })
        }
        callCount++
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(callCount === 1 ? TASKS_R1 : TASKS_R2),
        })
      })
      vi.stubGlobal('fetch', fetchMock)
      const { result } = renderHook(() => useBoard())
      await act(async () => {})
      const tasksRef = result.current.tasks
      await act(async () => {
        vi.advanceTimersByTime(3000)
      })
      expect(result.current.tasks).not.toBe(tasksRef)
    })

    it('tasks content reflects the updated data after a mtime change', async () => {
      let callCount = 0
      const fetchMock = vi.fn((url: string) => {
        if ((url as string).includes('/api/board')) {
          return Promise.resolve({ ok: true, json: () => Promise.resolve(BOARD) })
        }
        callCount++
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(callCount === 1 ? TASKS_R1 : TASKS_R2),
        })
      })
      vi.stubGlobal('fetch', fetchMock)
      const { result } = renderHook(() => useBoard())
      await act(async () => {})
      await act(async () => {
        vi.advanceTimersByTime(3000)
      })
      const tasks = result.current.tasks as typeof TASKS_R2.tasks
      expect(tasks[0]?.id).toBe(2)
    })
  })

  // ─── AC3: /api/board fetched once on mount (quasi-static) ─────────────────

  describe('/api/board single-mount fetch', () => {
    it('fetches /api/board exactly once while /api/tasks is polled multiple times', async () => {
      const fetchMock = boardFetch(TASKS_R1)
      vi.stubGlobal('fetch', fetchMock)
      renderHook(() => useBoard())
      await act(async () => {
        vi.advanceTimersByTime(9000)
      })
      const boardCalls = fetchMock.mock.calls.filter((c) =>
        (c[0] as string).includes('/api/board'),
      ).length
      const tasksCalls = fetchMock.mock.calls.filter((c) =>
        (c[0] as string).includes('/api/tasks'),
      ).length
      expect(boardCalls).toBe(1)
      expect(tasksCalls).toBeGreaterThan(1)
    })

    it('exposes board data from the single mount fetch', async () => {
      const fetchMock = boardFetch(TASKS_R1)
      vi.stubGlobal('fetch', fetchMock)
      const { result } = renderHook(() => useBoard())
      await act(async () => {})
      expect(result.current.board).toEqual(BOARD)
    })
  })

  // ─── AC4: return interface includes isFetching, isStale, refetchTasks ──────

  describe('hook return interface', () => {
    it('exposes all required fields: board, tasks, loading, error, isStale, isFetching, refetchTasks', async () => {
      const fetchMock = boardFetch(TASKS_R1)
      vi.stubGlobal('fetch', fetchMock)
      const { result } = renderHook(() => useBoard())
      await act(async () => {})
      const hook = result.current as unknown as UseBoardResult
      expect(hook).toHaveProperty('board')
      expect(hook).toHaveProperty('tasks')
      expect(hook).toHaveProperty('loading')
      expect(hook).toHaveProperty('error')
      expect(hook).toHaveProperty('isFetching')
      expect(hook).toHaveProperty('isStale')
      expect(hook).toHaveProperty('health')
      expect(hook).toHaveProperty('refetchTasks')
      expect(typeof hook.refetchTasks).toBe('function')
    })

    it('loading is false after the initial mount fetch completes', async () => {
      const fetchMock = boardFetch(TASKS_R1)
      vi.stubGlobal('fetch', fetchMock)
      const { result } = renderHook(() => useBoard())
      await act(async () => {})
      expect(result.current.loading).toBe(false)
    })

    it('refetchTasks triggers an additional /api/tasks fetch', async () => {
      const fetchMock = boardFetch(TASKS_R1)
      vi.stubGlobal('fetch', fetchMock)
      const { result } = renderHook(() => useBoard())
      await act(async () => {})
      const callsBefore = fetchMock.mock.calls.filter((c) =>
        (c[0] as string).includes('/api/tasks'),
      ).length
      await act(async () => {
        ;(result.current as unknown as UseBoardResult).refetchTasks()
      })
      const callsAfter = fetchMock.mock.calls.filter((c) =>
        (c[0] as string).includes('/api/tasks'),
      ).length
      expect(callsAfter).toBeGreaterThan(callsBefore)
    })
  })

  // ─── AC5: skip-when-in-flight (not abort-per-tick) ────────────────────────

  describe('skip-when-in-flight', () => {
    it('skips the interval tick when a poll fetch is already in-flight', async () => {
      let callCount = 0
      let resolvePoll!: () => void
      const deferredPoll = new Promise<unknown>((res) => {
        resolvePoll = res
      })
      const fetchMock = vi.fn((url: string) => {
        if ((url as string).includes('/api/board')) {
          return Promise.resolve({ ok: true, json: () => Promise.resolve(BOARD) })
        }
        callCount++
        if (callCount === 1) {
          return Promise.resolve({ ok: true, json: () => Promise.resolve(TASKS_R1) })
        }
        // Second call (poll) never resolves — keeps it "in-flight"
        return deferredPoll.then(() => ({ ok: true, json: () => Promise.resolve(TASKS_R1) }))
      })
      vi.stubGlobal('fetch', fetchMock)
      renderHook(() => useBoard())
      await act(async () => {})
      // Trigger first poll tick (in-flight, never resolves)
      act(() => {
        vi.advanceTimersByTime(3000)
      })
      const callsAfterFirstTick = callCount
      // Advance another 3s — tick should be skipped because poll is in-flight
      act(() => {
        vi.advanceTimersByTime(3000)
      })
      expect(callCount).toBe(callsAfterFirstTick) // no new fetch started
      // Clean up
      await act(async () => {
        resolvePoll()
      })
    })

    it('isFetching is true while a poll request is in-flight', async () => {
      let callCount = 0
      let resolvePoll!: () => void
      const deferredPoll = new Promise<unknown>((res) => {
        resolvePoll = res
      })
      const fetchMock = vi.fn((url: string) => {
        if ((url as string).includes('/api/board')) {
          return Promise.resolve({ ok: true, json: () => Promise.resolve(BOARD) })
        }
        callCount++
        if (callCount === 1) {
          return Promise.resolve({ ok: true, json: () => Promise.resolve(TASKS_R1) })
        }
        return deferredPoll.then(() => ({ ok: true, json: () => Promise.resolve(TASKS_R1) }))
      })
      vi.stubGlobal('fetch', fetchMock)
      const { result } = renderHook(() => useBoard())
      await act(async () => {})
      // Trigger poll tick — in-flight
      act(() => {
        vi.advanceTimersByTime(3000)
      })
      const hook = result.current as unknown as UseBoardResult
      expect(hook.isFetching).toBe(true)
      // Clean up
      await act(async () => {
        resolvePoll()
      })
    })

    it('isFetching is false once the in-flight poll resolves', async () => {
      const fetchMock = boardFetch(TASKS_R1)
      vi.stubGlobal('fetch', fetchMock)
      const { result } = renderHook(() => useBoard())
      await act(async () => {
        vi.advanceTimersByTime(3000)
      })
      const hook = result.current as unknown as UseBoardResult
      expect(hook.isFetching).toBe(false)
    })
  })

  // ─── AC5: AbortController cancels in-flight request on unmount ────────────

  describe('AbortController cleanup on unmount', () => {
    it('calls AbortController.abort when the hook unmounts', async () => {
      const abortSpy = vi.spyOn(AbortController.prototype, 'abort')
      // Fetch never resolves — keeps a request in-flight at unmount time
      const fetchMock = vi.fn((_url: string, init?: RequestInit) =>
        new Promise<never>((_resolve, reject) => {
          init?.signal?.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')))
        }),
      )
      vi.stubGlobal('fetch', fetchMock)
      const { unmount } = renderHook(() => useBoard())
      await act(async () => {})
      unmount()
      expect(abortSpy).toHaveBeenCalled()
    })

    it('does not update tasks state after unmount when an in-flight poll resolves', async () => {
      let callCount = 0
      let resolvePoll!: () => void
      const deferredPoll = new Promise<unknown>((res) => {
        resolvePoll = res
      })
      const fetchMock = vi.fn((url: string) => {
        if ((url as string).includes('/api/board')) {
          return Promise.resolve({ ok: true, json: () => Promise.resolve(BOARD) })
        }
        callCount++
        if (callCount === 1) {
          return Promise.resolve({ ok: true, json: () => Promise.resolve(TASKS_R1) })
        }
        return deferredPoll.then(() => ({ ok: true, json: () => Promise.resolve(TASKS_R2) }))
      })
      vi.stubGlobal('fetch', fetchMock)
      const { result, unmount } = renderHook(() => useBoard())
      await act(async () => {})
      act(() => {
        vi.advanceTimersByTime(3000)
      })
      expect(callCount).toBeGreaterThanOrEqual(2) // poll is in-flight
      const tasksBeforeUnmount = result.current.tasks
      unmount()
      await act(async () => {
        resolvePoll()
      })
      // State must not change after unmount
      expect(result.current.tasks).toBe(tasksBeforeUnmount)
    })
  })

  // ─── AC4 / error state: isStale and error ─────────────────────────────────

  describe('error and isStale after poll failure', () => {
    it('sets error to truthy when a poll request rejects', async () => {
      let callCount = 0
      const fetchMock = vi.fn((url: string) => {
        if ((url as string).includes('/api/board')) {
          return Promise.resolve({ ok: true, json: () => Promise.resolve(BOARD) })
        }
        callCount++
        if (callCount === 1) {
          return Promise.resolve({ ok: true, json: () => Promise.resolve(TASKS_R1) })
        }
        return Promise.reject(new Error('network failure'))
      })
      vi.stubGlobal('fetch', fetchMock)
      const { result } = renderHook(() => useBoard())
      await act(async () => {})
      expect(result.current.error).toBeNull()
      await act(async () => {
        vi.advanceTimersByTime(3000)
      })
      expect(result.current.error).toBeTruthy()
    })

    it('sets isStale to true after a poll failure', async () => {
      let callCount = 0
      const fetchMock = vi.fn((url: string) => {
        if ((url as string).includes('/api/board')) {
          return Promise.resolve({ ok: true, json: () => Promise.resolve(BOARD) })
        }
        callCount++
        if (callCount === 1) {
          return Promise.resolve({ ok: true, json: () => Promise.resolve(TASKS_R1) })
        }
        return Promise.reject(new Error('failure'))
      })
      vi.stubGlobal('fetch', fetchMock)
      const { result } = renderHook(() => useBoard())
      await act(async () => {})
      await act(async () => {
        vi.advanceTimersByTime(3000)
      })
      const hook = result.current as unknown as UseBoardResult
      expect(hook.isStale).toBe(true)
    })

    it('clears error and isStale to false on the next successful poll', async () => {
      let callCount = 0
      const fetchMock = vi.fn((url: string) => {
        if ((url as string).includes('/api/board')) {
          return Promise.resolve({ ok: true, json: () => Promise.resolve(BOARD) })
        }
        callCount++
        if (callCount === 1) {
          return Promise.resolve({ ok: true, json: () => Promise.resolve(TASKS_R1) })
        }
        if (callCount === 2) {
          return Promise.reject(new Error('transient failure'))
        }
        return Promise.resolve({ ok: true, json: () => Promise.resolve(TASKS_R2) })
      })
      vi.stubGlobal('fetch', fetchMock)
      const { result } = renderHook(() => useBoard())
      await act(async () => {})
      await act(async () => {
        vi.advanceTimersByTime(3000) // poll 2 — fails
      })
      expect(result.current.error).toBeTruthy()
      await act(async () => {
        vi.advanceTimersByTime(3000) // poll 3 — succeeds
      })
      const hook = result.current as unknown as UseBoardResult
      expect(hook.error).toBeNull()
      expect(hook.isStale).toBe(false)
    })
  })
})
