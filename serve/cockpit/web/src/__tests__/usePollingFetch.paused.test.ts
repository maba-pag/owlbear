/**
 * Workflow behavior tests1259: Add paused option to usePollingFetch
 *
 * AC1 (td:1): UsePollingFetchOptions adds paused?: boolean (default false) —
 *             UsePollingFetchResult unchanged
 * AC2 (td:2): When paused=true, interval callback skips poll()
 * AC3 (td:2): When paused=true, pendingPollRef finalizer also skips poll()
 * AC4 (td:2): When paused=true, refetch() still triggers poll()
 * AC5 (td:1): Initial mount poll() fires regardless of paused value
 * AC6 (td:2): Toggling paused true→false resumes on next natural tick —
 *             no timer teardown/setup, no immediate burst
 * AC7 (td:0): Existing tests pass — test-writer skipped per skill
 *
 * All tests must FAIL until builder implements the paused feature.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { usePollingFetch, UsePollingFetchOptions } from '../hooks/usePollingFetch'

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

function makeSlowFetch() {
  let resolve!: () => void
  const fn = vi.fn(
    () =>
      new Promise<{ ok: boolean; status: number; json: () => Promise<unknown> }>((res) => {
        resolve = () => res({ ok: true, status: 200, json: () => Promise.resolve({}) })
      }),
  )
  return { fn, resolve: () => resolve() }
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('TestFromAC_PausedOption', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.unstubAllGlobals()
    vi.clearAllMocks()
  })

  // ─── AC1: UsePollingFetchOptions adds paused?: boolean ────────────────────

  describe('AC1: paused option type contract', () => {
    it('smoke: paused:true is accepted and has behavioral effect — interval tick is skipped', async () => {
      // If UsePollingFetchOptions has no paused field, TypeScript would flag this.
      // Behavioral proof: with paused=true, the interval tick must not call fetch.
      const fetchMock = makeOkFetch()
      vi.stubGlobal('fetch', fetchMock)

      renderHook(() => usePollingFetch('/api/tasks', { intervalMs: 1_000, paused: true }))
      await act(async () => {})
      expect(fetchMock).toHaveBeenCalledTimes(1) // mount fired

      // Interval fires — must be skipped because paused=true.
      // On current impl (paused ignored), the interval calls poll() → fails here.
      await act(async () => { vi.advanceTimersByTime(1_000) })
      expect(fetchMock).toHaveBeenCalledTimes(1)
    })
  })

  it('contract: isFetching and hasFetched have correct lifecycle values — ' +
    'would fail if either were dropped from UsePollingFetchResult', async () => {
    // Discriminating proof for "UsePollingFetchResult unchanged" (AC1).
    // Uses a slow fetch so we can assert the in-flight state before resolution.
    const { fn: slowFetch, resolve } = makeSlowFetch()
    vi.stubGlobal('fetch', slowFetch)

    const { result } = renderHook(() =>
      usePollingFetch('/api/tasks', { intervalMs: 1_000 }),
    )
    await act(async () => {}) // effects settled; mount fetch is in-flight

    // In-flight: isFetching must be true, hasFetched must be false.
    // If either field were dropped, these assertions would throw (undefined ≠ boolean).
    expect(result.current.isFetching).toBe(true)
    expect(result.current.hasFetched).toBe(false)
    expect(typeof result.current.refetch).toBe('function')

    // After fetch resolves: isFetching must flip false, hasFetched must flip true.
    await act(async () => { resolve() })
    expect(result.current.isFetching).toBe(false)
    expect(result.current.hasFetched).toBe(true)
  })

  // ─── AC2: Interval callback skips poll() when paused ─────────────────────

  describe('AC2: interval skips poll when paused=true', () => {
    it('happy path: single interval tick does not call fetch when paused=true', async () => {
      const fetchMock = makeOkFetch()
      vi.stubGlobal('fetch', fetchMock)

      renderHook(() => usePollingFetch('/api/tasks', { intervalMs: 1_000, paused: true }))
      await act(async () => {})
      expect(fetchMock).toHaveBeenCalledTimes(1) // mount only

      await act(async () => { vi.advanceTimersByTime(1_000) })
      expect(fetchMock).toHaveBeenCalledTimes(1) // interval skipped
    })

    it('edge: all consecutive ticks skipped when paused=true throughout session', async () => {
      const fetchMock = makeOkFetch()
      vi.stubGlobal('fetch', fetchMock)

      renderHook(() => usePollingFetch('/api/tasks', { intervalMs: 500, paused: true }))
      await act(async () => {})
      expect(fetchMock).toHaveBeenCalledTimes(1) // mount only

      await act(async () => { vi.advanceTimersByTime(2_500) }) // 5 ticks
      expect(fetchMock).toHaveBeenCalledTimes(1)
    })

    it('boundary: 100 ticks while paused — fetch count remains at mount-only', async () => {
      const fetchMock = makeOkFetch()
      vi.stubGlobal('fetch', fetchMock)

      renderHook(() => usePollingFetch('/api/tasks', { intervalMs: 100, paused: true }))
      await act(async () => {})
      expect(fetchMock).toHaveBeenCalledTimes(1)

      await act(async () => { vi.advanceTimersByTime(10_000) }) // 100 ticks
      expect(fetchMock).toHaveBeenCalledTimes(1)
    })
  })

  // ─── AC3: pendingPollRef finalizer also skips poll() when paused ──────────

  describe('AC3: pendingPollRef drain suppressed when paused=true', () => {
    it('happy path: queued repoll from refetch is suppressed when paused=true at finalize time', async () => {
      // Sequence: mount (paused=false) → slow fetch in-flight → refetch() queues
      // pendingPollRef → set paused=true → slow fetch resolves → finalizer must
      // skip because paused=true.
      const { fn: slowFetch, resolve } = makeSlowFetch()
      vi.stubGlobal('fetch', slowFetch)

      const { result, rerender } = renderHook(
        (props: UsePollingFetchOptions<unknown>) => usePollingFetch('/api/tasks', props),
        { initialProps: { intervalMs: 5_000, paused: false } as UsePollingFetchOptions<unknown> },
      )
      // Mount: slow fetch in-flight (not resolved)
      expect(slowFetch).toHaveBeenCalledTimes(1)

      // refetch() while in-flight → inFlight guard sets pendingPollRef=true
      act(() => { result.current.refetch() })
      expect(slowFetch).toHaveBeenCalledTimes(1) // guard held

      // Set paused=true before the in-flight fetch resolves
      rerender({ intervalMs: 5_000, paused: true })

      // Resolve — finalizer sees pendingPollRef=true BUT paused=true → must skip
      await act(async () => { resolve() })

      // On current impl (no pause check in finalizer): second poll fires → 2 calls.
      // On target impl: drain suppressed → still 1 call.
      expect(slowFetch).toHaveBeenCalledTimes(1)
    })

    it('edge: queued repoll from interval tick is suppressed when paused set before resolve', async () => {
      // Sequence: mount (paused=false) → slow fetch in-flight → interval fires →
      // pendingPollRef=true → set paused=true → resolve → drain suppressed.
      const { fn: slowFetch, resolve } = makeSlowFetch()
      vi.stubGlobal('fetch', slowFetch)

      const { rerender } = renderHook(
        (props: UsePollingFetchOptions<unknown>) => usePollingFetch('/api/tasks', props),
        { initialProps: { intervalMs: 500, paused: false } as UsePollingFetchOptions<unknown> },
      )
      expect(slowFetch).toHaveBeenCalledTimes(1) // mount in-flight

      // Interval fires while in-flight → pendingPollRef=true (inFlight guard)
      await act(async () => { vi.advanceTimersByTime(500) })
      expect(slowFetch).toHaveBeenCalledTimes(1) // still 1 — guard held

      // Pause before resolving
      rerender({ intervalMs: 500, paused: true })

      // Resolve — finalizer must skip drain because paused=true
      await act(async () => { resolve() })
      expect(slowFetch).toHaveBeenCalledTimes(1)
    })
  })

  // ─── AC4: refetch() still triggers poll() when paused ────────────────────

  describe('AC4: refetch() bypasses pause guard', () => {
    it('happy path: refetch fires poll while paused — and interval was correctly bypassed', async () => {
      const fetchMock = makeOkFetch()
      vi.stubGlobal('fetch', fetchMock)

      const { result } = renderHook(() =>
        usePollingFetch('/api/tasks', { intervalMs: 1_000, paused: true }),
      )
      await act(async () => {})
      expect(fetchMock).toHaveBeenCalledTimes(1) // mount

      // Interval tick — must be skipped (proof that paused is respected)
      await act(async () => { vi.advanceTimersByTime(1_000) })
      // On current impl: interval fires → 2 fetches → the next assertion fails here
      expect(fetchMock).toHaveBeenCalledTimes(1)

      // Explicit refetch while paused — must still fire
      await act(async () => { result.current.refetch() })
      expect(fetchMock).toHaveBeenCalledTimes(2)
    })

    it('edge: sequential refetch calls while paused all trigger fetch; interval stays skipped', async () => {
      const fetchMock = makeOkFetch()
      vi.stubGlobal('fetch', fetchMock)

      const { result } = renderHook(() =>
        usePollingFetch('/api/tasks', { intervalMs: 5_000, paused: true }),
      )
      await act(async () => {})
      expect(fetchMock).toHaveBeenCalledTimes(1) // mount

      await act(async () => { result.current.refetch() }) // refetch #1
      await act(async () => { result.current.refetch() }) // refetch #2
      expect(fetchMock).toHaveBeenCalledTimes(3) // mount + 2 refetches

      // Interval stays paused — no extra fetch after advancing
      await act(async () => { vi.advanceTimersByTime(5_000) })
      // On current impl: interval fires → 4 fetches → fails here
      expect(fetchMock).toHaveBeenCalledTimes(3)
    })

    it('boundary: refetch while in-flight and paused — queued pending suppressed by pause guard', async () => {
      // refetch() while in-flight → pendingPollRef=true.
      // paused=true at finalize → drain suppressed (AC3 intersection with AC4).
      // Validates that the pause guard does NOT accidentally block the refetch() call itself —
      // only the subsequent drain is suppressed (because the in-flight guard prevented immediate fire).
      const { fn: slowFetch, resolve } = makeSlowFetch()
      vi.stubGlobal('fetch', slowFetch)

      const { result } = renderHook(() =>
        usePollingFetch('/api/tasks', { intervalMs: 5_000, paused: true }),
      )
      // Mount fires (AC5: unconditional)
      expect(slowFetch).toHaveBeenCalledTimes(1)

      // refetch() while in-flight — in-flight guard queues pendingPollRef
      act(() => { result.current.refetch() })
      expect(slowFetch).toHaveBeenCalledTimes(1) // guard held

      // Resolve — paused=true at finalize → drain suppressed
      await act(async () => { resolve() })
      // On current impl (no pause check): drain fires → 2 calls → fails here
      expect(slowFetch).toHaveBeenCalledTimes(1)
    })
  })

  // ─── AC5: Initial mount poll fires regardless of paused ──────────────────

  describe('AC5: initial mount poll is unconditional', () => {
    it('smoke: mount fires exactly once with paused=true, then interval tick does not add a second fetch', async () => {
      // Mount poll is unconditional (AC5). Combined with interval-skip (AC2) to
      // ensure the test fails on current impl while proving AC5's contract.
      const fetchMock = makeOkFetch()
      vi.stubGlobal('fetch', fetchMock)

      renderHook(() => usePollingFetch('/api/tasks', { intervalMs: 1_000, paused: true }))
      await act(async () => {})
      // Must have fired exactly once — mount is unconditional
      expect(fetchMock).toHaveBeenCalledTimes(1)

      // Interval fires and must be skipped (fails on current impl)
      await act(async () => { vi.advanceTimersByTime(1_000) })
      expect(fetchMock).toHaveBeenCalledTimes(1)
    })
  })

  // ─── AC6: Toggle paused true→false resumes on next natural tick ──────────

  describe('AC6: resume on next tick after paused→false toggle', () => {
    it('happy path: next tick after toggle fires poll — and pre-toggle ticks were skipped', async () => {
      const fetchMock = makeOkFetch()
      vi.stubGlobal('fetch', fetchMock)

      const { rerender } = renderHook(
        (props: UsePollingFetchOptions<unknown>) => usePollingFetch('/api/tasks', props),
        { initialProps: { intervalMs: 1_000, paused: true } as UsePollingFetchOptions<unknown> },
      )
      await act(async () => {})
      expect(fetchMock).toHaveBeenCalledTimes(1) // mount

      // One tick while paused — must be skipped
      await act(async () => { vi.advanceTimersByTime(1_000) })
      // On current impl: interval fires → 2 fetches → fails here
      expect(fetchMock).toHaveBeenCalledTimes(1)

      // Toggle to unpaused — no immediate burst
      rerender({ intervalMs: 1_000, paused: false })
      expect(fetchMock).toHaveBeenCalledTimes(1)

      // Next natural tick resumes polling
      await act(async () => { vi.advanceTimersByTime(1_000) })
      expect(fetchMock).toHaveBeenCalledTimes(2)
    })

    it('edge: no immediate poll fires on toggle — only next interval tick triggers fetch', async () => {
      const fetchMock = makeOkFetch()
      vi.stubGlobal('fetch', fetchMock)

      const { rerender } = renderHook(
        (props: UsePollingFetchOptions<unknown>) => usePollingFetch('/api/tasks', props),
        { initialProps: { intervalMs: 1_000, paused: true } as UsePollingFetchOptions<unknown> },
      )
      await act(async () => {})
      expect(fetchMock).toHaveBeenCalledTimes(1) // mount

      // Prove tick is skipped while paused (fails on current impl — interval fires)
      await act(async () => { vi.advanceTimersByTime(1_000) })
      expect(fetchMock).toHaveBeenCalledTimes(1) // interval skipped

      // Toggle paused → false — must NOT immediately trigger poll (no burst)
      rerender({ intervalMs: 1_000, paused: false })
      await act(async () => {}) // flush microtasks only
      expect(fetchMock).toHaveBeenCalledTimes(1) // no burst

      // Confirm poll resumes on the next tick
      await act(async () => { vi.advanceTimersByTime(1_000) })
      expect(fetchMock).toHaveBeenCalledTimes(2)
    })

    it('timer-stability: interval fires at original timer offset after pause/unpause — ' +
      'would fail if implementation recreated the interval on toggle', async () => {
      // Ref-based approach: pausedRef updates each render, timer stays stable.
      // Conditional-interval approach: clearInterval+setInterval on each toggle → timer resets.
      // Test: pause at t=500ms, unpause at t=600ms, advance to t=1000ms.
      //   Stable timer:      fires at t=1000ms (original 1000ms tick) → fetch #2.
      //   Recreated timer:   fires at t=1600ms (1000ms from toggle at t=600ms) → still 1 fetch.
      const fetchMock = makeOkFetch()
      vi.stubGlobal('fetch', fetchMock)

      const { rerender } = renderHook(
        (props: UsePollingFetchOptions<unknown>) => usePollingFetch('/api/tasks', props),
        { initialProps: { intervalMs: 1_000, paused: false } as UsePollingFetchOptions<unknown> },
      )
      await act(async () => {})
      expect(fetchMock).toHaveBeenCalledTimes(1) // mount

      // t=500ms: interval not yet due
      await act(async () => { vi.advanceTimersByTime(500) })
      expect(fetchMock).toHaveBeenCalledTimes(1)

      // Pause at t=500ms
      rerender({ intervalMs: 1_000, paused: true })

      // t=600ms: still paused
      await act(async () => { vi.advanceTimersByTime(100) })

      // Unpause at t=600ms
      rerender({ intervalMs: 1_000, paused: false })

      // t=1000ms: original 1000ms tick fires
      // Stable: poll() called → fetch #2
      // Recreated (new timer from t=600ms): fires at t=1600ms → no second fetch yet
      await act(async () => { vi.advanceTimersByTime(400) })
      expect(fetchMock).toHaveBeenCalledTimes(2)
    })

    it('boundary: multiple pause/unpause cycles do not accumulate burst fetches', async () => {
      const fetchMock = makeOkFetch()
      vi.stubGlobal('fetch', fetchMock)

      const { rerender } = renderHook(
        (props: UsePollingFetchOptions<unknown>) => usePollingFetch('/api/tasks', props),
        { initialProps: { intervalMs: 1_000, paused: true } as UsePollingFetchOptions<unknown> },
      )
      await act(async () => {})
      expect(fetchMock).toHaveBeenCalledTimes(1) // mount

      // Cycle 1: pause tick → unpause → next tick
      await act(async () => { vi.advanceTimersByTime(1_000) }) // skipped
      // On current impl: fires at tick → fails here with 2 instead of 1
      expect(fetchMock).toHaveBeenCalledTimes(1)
      rerender({ intervalMs: 1_000, paused: false })
      await act(async () => { vi.advanceTimersByTime(1_000) }) // resumes
      expect(fetchMock).toHaveBeenCalledTimes(2)

      // Cycle 2: pause again → tick skipped → unpause → next tick
      rerender({ intervalMs: 1_000, paused: true })
      await act(async () => { vi.advanceTimersByTime(1_000) }) // skipped
      expect(fetchMock).toHaveBeenCalledTimes(2) // no burst from pause+skip
      rerender({ intervalMs: 1_000, paused: false })
      await act(async () => { vi.advanceTimersByTime(1_000) }) // resumes
      expect(fetchMock).toHaveBeenCalledTimes(3)
    })
  })
})
