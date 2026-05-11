/**
 * useBoard polling + mtime-skip + error states.
 *
 * Covers: 3s poll interval, mtime-aware skip (no re-render on same mtime),
 * error/isStale/isFetching traffic-light states, AbortController cleanup on
 * unmount, and /api/board single-mount fetch.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useBoard } from '../hooks/useBoard'

vi.mock('../hooks/EventSourceProvider', () => ({
  useSSEEvent: vi.fn(() => ({ mtime: null, status: 'closed' as const })),
}))

// ─── Expected post-implementation hook interface ──────────────────────────────

interface UseBoardWithPolling {
  board: unknown
  tasks: unknown[]
  loading: boolean
  error: string | null
  isFetching: boolean
  isStale: boolean
  refetchTasks: () => void
}

// ─── Fixtures ─────────────────────────────────────────────────────────────────

const BOARD = {
  statuses: [{ name: 'backlog' }],
  priorities: ['important'],
  valid_transitions: { backlog: [] } as Record<string, string[]>,
}

const TASKS_V1 = [
  {
    id: 1,
    title: 'T1',
    status: 'backlog',
    priority: 'important',
    tags: [],
    blocked: false,
    block_reason: null,
    claimed: false,
  },
]

const TASKS_V2 = [
  {
    id: 2,
    title: 'T2',
    status: 'backlog',
    priority: 'important',
    tags: [],
    blocked: false,
    block_reason: null,
    claimed: false,
  },
]

const MTIME_1 = { tasks: TASKS_V1, mtime: 1000 }
const MTIME_2 = { tasks: TASKS_V2, mtime: 2000 }

function makeFetch(tasksData: unknown) {
  return vi.fn((url: string) => {
    if (url.includes('/api/board')) {
      return Promise.resolve({ ok: true, json: () => Promise.resolve(BOARD) })
    }
    return Promise.resolve({ ok: true, json: () => Promise.resolve(tasksData) })
  })
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('TestFromAC_useBoardPolling', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  // ─── AC1: 3-second polling interval ───────────────────────────────────────

  describe('3-second polling interval', () => {
    it('polls /api/tasks at least twice after 6 seconds', async () => {
      const fetchMock = makeFetch(MTIME_1)
      vi.stubGlobal('fetch', fetchMock)
      renderHook(() => useBoard())
      await act(async () => {
        vi.advanceTimersByTime(6000)
      })
      const tasksCalls = fetchMock.mock.calls.filter((c) =>
        (c[0] as string).includes('/api/tasks'),
      ).length
      expect(tasksCalls).toBeGreaterThanOrEqual(2)
    })

    it('fires the first poll at 3 seconds but not before', async () => {
      const fetchMock = makeFetch(MTIME_1)
      vi.stubGlobal('fetch', fetchMock)
      renderHook(() => useBoard())
      await act(async () => {})
      const callsAtMount = fetchMock.mock.calls.filter((c) =>
        (c[0] as string).includes('/api/tasks'),
      ).length
      // Advance to 1ms before the interval
      await act(async () => {
        vi.advanceTimersByTime(2999)
      })
      const callsBefore = fetchMock.mock.calls.filter((c) =>
        (c[0] as string).includes('/api/tasks'),
      ).length
      expect(callsBefore).toBe(callsAtMount) // no extra call before 3s
      // Advance through the interval boundary
      await act(async () => {
        vi.advanceTimersByTime(1)
      })
      const callsAt3s = fetchMock.mock.calls.filter((c) =>
        (c[0] as string).includes('/api/tasks'),
      ).length
      expect(callsAt3s).toBeGreaterThan(callsAtMount) // poll fired at 3s
    })
  })

  // ─── AC2: mtime-aware skip ─────────────────────────────────────────────────

  describe('mtime-aware skip', () => {
    it('does not update tasks reference when poll returns the same mtime', async () => {
      const fetchMock = makeFetch(MTIME_1) // always returns mtime 1000
      vi.stubGlobal('fetch', fetchMock)
      const { result } = renderHook(() => useBoard())
      await act(async () => {})
      const tasksBefore = result.current.tasks
      await act(async () => {
        vi.advanceTimersByTime(3000)
      })
      // Confirm polling occurred (multiple /api/tasks calls)
      const tasksCalls = fetchMock.mock.calls.filter((c) =>
        (c[0] as string).includes('/api/tasks'),
      ).length
      expect(tasksCalls).toBeGreaterThanOrEqual(2) // polling is running
      expect(result.current.tasks).toBe(tasksBefore) // same array reference — no re-render
    })
  })

  // ─── AC3: mtime change triggers task update ────────────────────────────────

  describe('mtime change triggers task update', () => {
    it('updates tasks reference when poll returns a new mtime', async () => {
      let tasksCallCount = 0
      const fetchMock = vi.fn((url: string) => {
        if ((url as string).includes('/api/board')) {
          return Promise.resolve({ ok: true, json: () => Promise.resolve(BOARD) })
        }
        tasksCallCount++
        const data = tasksCallCount === 1 ? MTIME_1 : MTIME_2
        return Promise.resolve({ ok: true, json: () => Promise.resolve(data) })
      })
      vi.stubGlobal('fetch', fetchMock)
      const { result } = renderHook(() => useBoard())
      await act(async () => {})
      const tasksBefore = result.current.tasks
      await act(async () => {
        vi.advanceTimersByTime(3000)
      })
      expect(result.current.tasks).not.toBe(tasksBefore) // new reference when mtime changed
    })

    it('tasks content reflects updated data after mtime change', async () => {
      let tasksCallCount = 0
      const fetchMock = vi.fn((url: string) => {
        if ((url as string).includes('/api/board')) {
          return Promise.resolve({ ok: true, json: () => Promise.resolve(BOARD) })
        }
        tasksCallCount++
        const data = tasksCallCount === 1 ? MTIME_1 : MTIME_2
        return Promise.resolve({ ok: true, json: () => Promise.resolve(data) })
      })
      vi.stubGlobal('fetch', fetchMock)
      const { result } = renderHook(() => useBoard())
      await act(async () => {})
      await act(async () => {
        vi.advanceTimersByTime(3000)
      })
      // After the poll, tasks content should match TASKS_V2 (from MTIME_2)
      const tasks = result.current.tasks as typeof TASKS_V2
      expect(tasks[0]?.id).toBe(2)
    })
  })

  // ─── AC4: error state ──────────────────────────────────────────────────────

  describe('error state', () => {
    it('sets error when a poll fetch rejects after a successful initial load', async () => {
      let tasksCallCount = 0
      const fetchMock = vi.fn((url: string) => {
        if ((url as string).includes('/api/board')) {
          return Promise.resolve({ ok: true, json: () => Promise.resolve(BOARD) })
        }
        tasksCallCount++
        if (tasksCallCount === 1) {
          return Promise.resolve({ ok: true, json: () => Promise.resolve(MTIME_1) })
        }
        return Promise.reject(new Error('network failure'))
      })
      vi.stubGlobal('fetch', fetchMock)
      const { result } = renderHook(() => useBoard())
      await act(async () => {})
      expect(result.current.error).toBeNull() // initial load succeeded
      await act(async () => {
        vi.advanceTimersByTime(3000) // poll fails
      })
      expect(result.current.error).toBeTruthy()
    })

    it('sets error when a poll returns a non-ok HTTP response', async () => {
      let tasksCallCount = 0
      const fetchMock = vi.fn((url: string) => {
        if ((url as string).includes('/api/board')) {
          return Promise.resolve({ ok: true, json: () => Promise.resolve(BOARD) })
        }
        tasksCallCount++
        if (tasksCallCount === 1) {
          return Promise.resolve({ ok: true, json: () => Promise.resolve(MTIME_1) })
        }
        return Promise.resolve({ ok: false, status: 503, json: () => Promise.resolve({}) })
      })
      vi.stubGlobal('fetch', fetchMock)
      const { result } = renderHook(() => useBoard())
      await act(async () => {})
      expect(result.current.error).toBeNull() // initial load succeeded
      await act(async () => {
        vi.advanceTimersByTime(3000) // poll returns non-ok
      })
      expect(result.current.error).toBeTruthy()
    })

    it('clears error to null on the next successful poll after a failure', async () => {
      let tasksCallCount = 0
      const fetchMock = vi.fn((url: string) => {
        if ((url as string).includes('/api/board')) {
          return Promise.resolve({ ok: true, json: () => Promise.resolve(BOARD) })
        }
        tasksCallCount++
        if (tasksCallCount === 1) {
          return Promise.resolve({ ok: true, json: () => Promise.resolve(MTIME_1) })
        }
        if (tasksCallCount === 2) {
          return Promise.reject(new Error('transient failure'))
        }
        return Promise.resolve({ ok: true, json: () => Promise.resolve(MTIME_2) })
      })
      vi.stubGlobal('fetch', fetchMock)
      const { result } = renderHook(() => useBoard())
      await act(async () => {})
      await act(async () => {
        vi.advanceTimersByTime(3000) // poll 2 — fails
      })
      expect(result.current.error).toBeTruthy() // error is set
      await act(async () => {
        vi.advanceTimersByTime(3000) // poll 3 — succeeds
      })
      expect(result.current.error).toBeNull() // error cleared on recovery
    })
  })

  // ─── AC5: isFetching / isStale traffic-light states ───────────────────────

  describe('isFetching and isStale', () => {
    it('isFetching is true while a poll request is in-flight', async () => {
      let tasksCallCount = 0
      let resolvePollFn!: () => void
      const deferredPoll = new Promise<unknown>((res) => {
        resolvePollFn = res
      })
      const fetchMock = vi.fn((url: string) => {
        if ((url as string).includes('/api/board')) {
          return Promise.resolve({ ok: true, json: () => Promise.resolve(BOARD) })
        }
        tasksCallCount++
        if (tasksCallCount === 1) {
          return Promise.resolve({ ok: true, json: () => Promise.resolve(MTIME_1) })
        }
        // Poll request is deferred — keeps isFetching true while pending
        return deferredPoll.then(() => ({
          ok: true,
          json: () => Promise.resolve(MTIME_1),
        }))
      })
      vi.stubGlobal('fetch', fetchMock)
      const { result } = renderHook(() => useBoard())
      await act(async () => {}) // initial load completes
      // Trigger interval without flushing the deferred promise
      act(() => {
        vi.advanceTimersByTime(3000)
      })
      const hookResult = result.current as unknown as UseBoardWithPolling
      expect(hookResult.isFetching).toBe(true)
      // Clean up — resolve the in-flight request
      await act(async () => {
        resolvePollFn()
      })
    })

    it('isStale is true after a poll failure', async () => {
      let tasksCallCount = 0
      const fetchMock = vi.fn((url: string) => {
        if ((url as string).includes('/api/board')) {
          return Promise.resolve({ ok: true, json: () => Promise.resolve(BOARD) })
        }
        tasksCallCount++
        if (tasksCallCount === 1) {
          return Promise.resolve({ ok: true, json: () => Promise.resolve(MTIME_1) })
        }
        return Promise.reject(new Error('failure'))
      })
      vi.stubGlobal('fetch', fetchMock)
      const { result } = renderHook(() => useBoard())
      await act(async () => {})
      await act(async () => {
        vi.advanceTimersByTime(3000) // poll fails
      })
      const hookResult = result.current as unknown as UseBoardWithPolling
      expect(hookResult.isStale).toBe(true)
    })

    it('isStale returns to false after a successful poll following a failure', async () => {
      let tasksCallCount = 0
      const fetchMock = vi.fn((url: string) => {
        if ((url as string).includes('/api/board')) {
          return Promise.resolve({ ok: true, json: () => Promise.resolve(BOARD) })
        }
        tasksCallCount++
        if (tasksCallCount === 1) {
          return Promise.resolve({ ok: true, json: () => Promise.resolve(MTIME_1) })
        }
        if (tasksCallCount === 2) {
          return Promise.reject(new Error('failure'))
        }
        return Promise.resolve({ ok: true, json: () => Promise.resolve(MTIME_2) })
      })
      vi.stubGlobal('fetch', fetchMock)
      const { result } = renderHook(() => useBoard())
      await act(async () => {})
      await act(async () => {
        vi.advanceTimersByTime(3000) // poll 2 — fails, isStale → true
      })
      await act(async () => {
        vi.advanceTimersByTime(3000) // poll 3 — succeeds, isStale → false
      })
      const hookResult = result.current as unknown as UseBoardWithPolling
      expect(hookResult.isStale).toBe(false)
    })
  })

  // ─── AC6: unmount cleanup ──────────────────────────────────────────────────

  describe('unmount cleanup', () => {
    it('calls AbortController.abort on unmount', async () => {
      const abortSpy = vi.spyOn(AbortController.prototype, 'abort')
      const fetchMock = vi.fn((url: string, init?: RequestInit) => {
        if ((url as string).includes('/api/board')) {
          return Promise.resolve({ ok: true, json: () => Promise.resolve(BOARD) })
        }
        return new Promise<never>((_resolve, reject) => { // never resolves — keeps request in-flight
          init?.signal?.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')))
        })
      })
      vi.stubGlobal('fetch', fetchMock)
      const { unmount } = renderHook(() => useBoard())
      await act(async () => {})
      unmount()
      expect(abortSpy).toHaveBeenCalled()
    })

    it('does not update tasks state after unmount when an in-flight poll resolves', async () => {
      let tasksCallCount = 0
      let resolvePollFn!: () => void
      const deferredPoll = new Promise<unknown>((res) => {
        resolvePollFn = res
      })
      const fetchMock = vi.fn((url: string) => {
        if ((url as string).includes('/api/board')) {
          return Promise.resolve({ ok: true, json: () => Promise.resolve(BOARD) })
        }
        tasksCallCount++
        if (tasksCallCount === 1) {
          return Promise.resolve({ ok: true, json: () => Promise.resolve(MTIME_1) })
        }
        return deferredPoll.then(() => ({
          ok: true,
          json: () => Promise.resolve(MTIME_2),
        }))
      })
      vi.stubGlobal('fetch', fetchMock)
      const { result, unmount } = renderHook(() => useBoard())
      await act(async () => {})
      // Trigger the poll (in-flight, not yet resolved)
      act(() => {
        vi.advanceTimersByTime(3000)
      })
      // Confirm poll is in-flight (polling must be implemented for this to pass)
      expect(tasksCallCount).toBeGreaterThanOrEqual(2)
      const tasksBeforeUnmount = result.current.tasks
      unmount()
      // Resolve the poll after unmount — should NOT update state
      await act(async () => {
        resolvePollFn()
      })
      expect(result.current.tasks).toBe(tasksBeforeUnmount) // no post-unmount update
    })
  })

  // ─── AC7: /api/board fetched once on mount (not polled) ───────────────────

  describe('/api/board single-mount fetch', () => {
    it('fetches /api/board exactly once while /api/tasks is polled multiple times', async () => {
      const fetchMock = makeFetch(MTIME_1)
      vi.stubGlobal('fetch', fetchMock)
      renderHook(() => useBoard())
      await act(async () => {
        vi.advanceTimersByTime(9000) // 3 polling cycles
      })
      const boardCalls = fetchMock.mock.calls.filter((c) =>
        (c[0] as string).includes('/api/board'),
      ).length
      const tasksCalls = fetchMock.mock.calls.filter((c) =>
        (c[0] as string).includes('/api/tasks'),
      ).length
      expect(boardCalls).toBe(1) // board fetched once on mount only
      expect(tasksCalls).toBeGreaterThan(1) // tasks polled multiple times
    })
  })
})

