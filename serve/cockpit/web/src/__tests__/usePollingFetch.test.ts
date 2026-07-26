/**
 * usePollingFetch shared polling utility
 *
 * AC2 (td:2): Shared polling utility extracted — inFlight guard, boolean
 * coalesce, AbortController cleanup, onSuccess/onError callbacks.
 *
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { usePollingFetch } from '../hooks/usePollingFetch'

vi.mock('../hooks/EventSourceProvider', () => ({
  useSSEEvent: vi.fn(() => ({ mtime: null, status: 'closed' as const })),
}))

// ─── Helpers ──────────────────────────────────────────────────────────────────

function makeOkFetch(body: unknown = {}) {
  return vi.fn(() =>
    Promise.resolve({
      ok: true,
      status: 200,
      json: () => Promise.resolve(body),
    }),
  )
}

function makeErrorFetch(status = 500) {
  return vi.fn(() =>
    Promise.resolve({
      ok: false,
      status,
      json: () => Promise.resolve({ error: 'server error' }),
    }),
  )
}

function makeNetworkErrorFetch() {
  return vi.fn(() => Promise.reject(new TypeError('Failed to fetch')))
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('TestFromAC_UsePollingFetch', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.unstubAllGlobals()
    vi.clearAllMocks()
  })

  // ─── Happy path ───────────────────────────────────────────────────────────

  describe('happy path: fetch on mount', () => {
    it('calls fetch once on mount before any interval fires', async () => {
      const fetchMock = makeOkFetch()
      vi.stubGlobal('fetch', fetchMock)

      renderHook(() => usePollingFetch('/api/tasks', { intervalMs: 5_000 }))
      await act(async () => {})

      expect(fetchMock).toHaveBeenCalledTimes(1)
      expect(fetchMock).toHaveBeenCalledWith('/api/tasks', expect.anything())
    })

    it('re-fetches at the configured intervalMs', async () => {
      const fetchMock = makeOkFetch()
      vi.stubGlobal('fetch', fetchMock)

      renderHook(() => usePollingFetch('/api/tasks', { intervalMs: 3_000 }))
      await act(async () => {})
      expect(fetchMock).toHaveBeenCalledTimes(1)
      await act(async () => { vi.advanceTimersByTime(3_000) })
      expect(fetchMock.mock.calls.length).toBeGreaterThanOrEqual(2)
    })

    it('calls onSuccess callback when fetch returns ok response', async () => {
      const fetchMock = makeOkFetch({ mtime: 42 })
      vi.stubGlobal('fetch', fetchMock)
      const onSuccess = vi.fn()

      renderHook(() => usePollingFetch('/api/tasks', { intervalMs: 5_000, onSuccess }))
      await act(async () => {})

      expect(onSuccess).toHaveBeenCalledTimes(1)
    })
  })

  // ─── Error paths ──────────────────────────────────────────────────────────

  describe('error paths: onError callback', () => {
    it('calls onError callback when fetch returns non-OK status', async () => {
      vi.stubGlobal('fetch', makeErrorFetch(503))
      const onError = vi.fn()

      renderHook(() => usePollingFetch('/api/tasks', { intervalMs: 5_000, onError }))
      await act(async () => {})

      expect(onError).toHaveBeenCalledTimes(1)
    })

    it('calls onError callback when fetch throws (network failure)', async () => {
      vi.stubGlobal('fetch', makeNetworkErrorFetch())
      const onError = vi.fn()

      renderHook(() => usePollingFetch('/api/tasks', { intervalMs: 5_000, onError }))
      await act(async () => {})

      expect(onError).toHaveBeenCalledTimes(1)
    })

    it('does NOT call onSuccess when fetch returns non-OK status', async () => {
      vi.stubGlobal('fetch', makeErrorFetch(500))
      const onSuccess = vi.fn()

      renderHook(() => usePollingFetch('/api/tasks', { intervalMs: 5_000, onSuccess }))
      await act(async () => {})

      expect(onSuccess).not.toHaveBeenCalled()
    })
  })

  // ─── Edge cases: inFlight guard and boolean coalesce ─────────────────────

  describe('edge cases: inFlight guard', () => {
    it('inFlight guard: a concurrent poll call while the first is in-flight ' +
    'does not fire a duplicate fetch', async () => {
      let resolveFetch!: () => void
      const slowFetch = vi.fn(
        () =>
          new Promise<{ ok: boolean; status: number; json: () => Promise<unknown> }>(
            (resolve) => {
              resolveFetch = () =>
                resolve({ ok: true, status: 200, json: () => Promise.resolve({}) })
            },
          ),
      )
      vi.stubGlobal('fetch', slowFetch)

      // Use a very short interval so the timer fires while the first fetch is still in-flight
      renderHook(() => usePollingFetch('/api/tasks', { intervalMs: 100 }))
      // Advance timer to trigger interval BEFORE the first fetch resolves
      await act(async () => { vi.advanceTimersByTime(100) })
      // Fetch still in-flight — timer fired but should NOT have started a second fetch
      expect(slowFetch).toHaveBeenCalledTimes(1)
      // Now resolve the first fetch
      await act(async () => { resolveFetch() })
    })

    it('boolean coalesce: at most one pending repoll is queued (not a counted replay)', async () => {
      let resolveFetch!: () => void
      const slowFetch = vi.fn(
        () =>
          new Promise<{ ok: boolean; status: number; json: () => Promise<unknown> }>(
            (resolve) => {
              resolveFetch = () =>
                resolve({ ok: true, status: 200, json: () => Promise.resolve({}) })
            },
          ),
      )
      vi.stubGlobal('fetch', slowFetch)

      renderHook(() => usePollingFetch('/api/tasks', { intervalMs: 100 }))
      // Trigger two interval ticks while the initial fetch is still in-flight
      await act(async () => { vi.advanceTimersByTime(200) })
      // Still only 1 real fetch call (the initial one)
      expect(slowFetch).toHaveBeenCalledTimes(1)
      // Resolve and check that only ONE pending poll fires (not two)
      await act(async () => { resolveFetch() })
      // After resolving, exactly one queued repoll should fire.
      expect(slowFetch).toHaveBeenCalledTimes(2)
    })
  })

  // ─── Boundary conditions: AbortController + cleanup ──────────────────────

  describe('boundary: AbortController and interval cleanup', () => {
    it('cleanup on unmount aborts pending fetch via AbortController signal', async () => {
      const abortCalls: boolean[] = []
      const mockFetch = vi.fn((_url: string, init?: RequestInit) => {
        if (init?.signal) {
          init.signal.addEventListener('abort', () => abortCalls.push(true))
        }
        return new Promise<never>(() => {/* never resolves */})
      })
      vi.stubGlobal('fetch', mockFetch)

      const { unmount } = renderHook(() => usePollingFetch('/api/tasks', { intervalMs: 5_000 }))

      // Unmount before fetch resolves — should trigger abort
      act(() => { unmount() })

      expect(abortCalls).toHaveLength(1)
    })

    it('interval is cleared on unmount — no further fetches after cleanup', async () => {
      const fetchMock = makeOkFetch()
      vi.stubGlobal('fetch', fetchMock)

      const { unmount } = renderHook(() => usePollingFetch('/api/tasks', { intervalMs: 1_000 }))
      await act(async () => {})
      expect(fetchMock).toHaveBeenCalledTimes(1)

      act(() => { unmount() })
      await act(async () => { vi.advanceTimersByTime(5_000) })
      // After unmount, no additional fetches should fire
      expect(fetchMock).toHaveBeenCalledTimes(1)
    })
  })
})
