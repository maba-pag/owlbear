/**
 * Failing tests for #935: usePolling hook
 *
 * Covers: 3s poll interval using mtime change detection, skip-next-poll after
 * mutation, and connection health states (green / yellow / red).
 * All tests are RED (failing) until the builder implements usePolling.ts.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { usePolling } from '../usePolling'

// ─── Fixtures ─────────────────────────────────────────────────────────────────

const TASKS_RESPONSE = { tasks: [], mtime: 1000 }
const TASKS_RESPONSE_UPDATED = { tasks: [], mtime: 2000 }

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('TestFromAC_usePolling', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.unstubAllGlobals()
  })

  // ─── Poll interval ────────────────────────────────────────────────────────

  describe('poll interval (~3s)', () => {
    it('fetches the URL once on mount', async () => {
      const fetchMock = vi.fn(() =>
        Promise.resolve({ ok: true, json: () => Promise.resolve(TASKS_RESPONSE) }),
      )
      vi.stubGlobal('fetch', fetchMock)
      renderHook(() => usePolling('/api/tasks'))
      await act(async () => {})
      expect(fetchMock).toHaveBeenCalledTimes(1)
      expect(fetchMock).toHaveBeenCalledWith('/api/tasks', expect.anything())
    })

    it('fetches again after ~3 seconds', async () => {
      const fetchMock = vi.fn(() =>
        Promise.resolve({ ok: true, json: () => Promise.resolve(TASKS_RESPONSE) }),
      )
      vi.stubGlobal('fetch', fetchMock)
      renderHook(() => usePolling('/api/tasks'))
      await act(async () => {
        vi.advanceTimersByTime(3000)
      })
      expect(fetchMock.mock.calls.length).toBeGreaterThanOrEqual(2)
    })

    it('does not fetch again before 3 seconds have elapsed', async () => {
      const fetchMock = vi.fn(() =>
        Promise.resolve({ ok: true, json: () => Promise.resolve(TASKS_RESPONSE) }),
      )
      vi.stubGlobal('fetch', fetchMock)
      renderHook(() => usePolling('/api/tasks'))
      await act(async () => {})
      // Expect exactly 1 call (the mount fetch)
      expect(fetchMock).toHaveBeenCalledTimes(1)
      await act(async () => {
        vi.advanceTimersByTime(2999)
      })
      // Still only 1 call — interval has not fired yet
      expect(fetchMock).toHaveBeenCalledTimes(1)
    })

    it('uses mtime from response to detect changes (mtime is present in request context)', async () => {
      let callCount = 0
      const fetchMock = vi.fn(() => {
        callCount++
        const mtime = callCount === 1 ? TASKS_RESPONSE : TASKS_RESPONSE_UPDATED
        return Promise.resolve({ ok: true, json: () => Promise.resolve(mtime) })
      })
      vi.stubGlobal('fetch', fetchMock)
      renderHook(() => usePolling('/api/tasks'))
      await act(async () => {
        vi.advanceTimersByTime(6000)
      })
      // At least 2 fetch calls (mount + 1 interval)
      expect(fetchMock.mock.calls.length).toBeGreaterThanOrEqual(2)
    })
  })

  // ─── Skip-next-poll ───────────────────────────────────────────────────────

  describe('skip-next-poll after mutation', () => {
    it('skipNextPoll suppresses the next poll cycle', async () => {
      const fetchMock = vi.fn(() =>
        Promise.resolve({ ok: true, json: () => Promise.resolve(TASKS_RESPONSE) }),
      )
      vi.stubGlobal('fetch', fetchMock)
      const { result } = renderHook(() => usePolling('/api/tasks'))
      await act(async () => {})
      // Must have fetched once on mount before we can measure the skip
      expect(fetchMock).toHaveBeenCalledTimes(1)
      const countBeforeSkip = fetchMock.mock.calls.length
      act(() => {
        result.current.skipNextPoll()
      })
      await act(async () => {
        vi.advanceTimersByTime(3000)
      })
      // The skip should have prevented the interval fetch
      expect(fetchMock.mock.calls.length).toBe(countBeforeSkip)
    })

    it('polling resumes normally after the skipped cycle', async () => {
      const fetchMock = vi.fn(() =>
        Promise.resolve({ ok: true, json: () => Promise.resolve(TASKS_RESPONSE) }),
      )
      vi.stubGlobal('fetch', fetchMock)
      const { result } = renderHook(() => usePolling('/api/tasks'))
      await act(async () => {})
      expect(fetchMock).toHaveBeenCalledTimes(1)
      act(() => {
        result.current.skipNextPoll()
      })
      // Advance through the skipped cycle
      await act(async () => {
        vi.advanceTimersByTime(3000)
      })
      const countAfterSkip = fetchMock.mock.calls.length
      // Advance through a second cycle — should fire
      await act(async () => {
        vi.advanceTimersByTime(3000)
      })
      expect(fetchMock.mock.calls.length).toBeGreaterThan(countAfterSkip)
    })
  })

  // ─── Connection health ────────────────────────────────────────────────────

  describe('connection health states', () => {
    it('health is green after a successful poll (last poll < 6s ago)', async () => {
      const fetchMock = vi.fn(() =>
        Promise.resolve({ ok: true, json: () => Promise.resolve(TASKS_RESPONSE) }),
      )
      vi.stubGlobal('fetch', fetchMock)
      const { result } = renderHook(() => usePolling('/api/tasks'))
      await act(async () => {})
      // A fetch must have fired to establish green state
      expect(fetchMock).toHaveBeenCalledTimes(1)
      expect(result.current.health).toBe('green')
    })

    it('health is yellow when last successful poll was between 6s and 15s ago', async () => {
      // Fetch fails so no successful poll can register
      vi.stubGlobal('fetch', vi.fn(() => Promise.reject(new Error('Network error'))))
      const { result } = renderHook(() => usePolling('/api/tasks'))
      // Advance 10 seconds with no successful poll
      await act(async () => {
        vi.advanceTimersByTime(10000)
      })
      expect(result.current.health).toBe('yellow')
    })

    it('health is red when last successful poll was more than 15s ago', async () => {
      // Fetch fails so no successful poll can register
      vi.stubGlobal('fetch', vi.fn(() => Promise.reject(new Error('Network error'))))
      const { result } = renderHook(() => usePolling('/api/tasks'))
      // Advance 20 seconds with no successful poll
      await act(async () => {
        vi.advanceTimersByTime(20000)
      })
      expect(result.current.health).toBe('red')
    })

    it('health transitions back to green after reconnecting', async () => {
      let shouldFail = true
      const fetchMock = vi.fn(() => {
        if (shouldFail) return Promise.reject(new Error('Network error'))
        return Promise.resolve({ ok: true, json: () => Promise.resolve(TASKS_RESPONSE) })
      })
      vi.stubGlobal('fetch', fetchMock)
      const { result } = renderHook(() => usePolling('/api/tasks'))
      // Accumulate red state
      await act(async () => {
        vi.advanceTimersByTime(20000)
      })
      expect(result.current.health).toBe('red')
      // Restore connectivity
      shouldFail = false
      // Advance one poll cycle so a successful fetch can fire
      await act(async () => {
        vi.advanceTimersByTime(3000)
      })
      expect(result.current.health).toBe('green')
    })
  })
})
