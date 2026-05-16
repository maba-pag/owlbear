/**
 * Wire usePendingDRs to SSE decisions-changed early-refetch
 * Scope: AC5 — usePendingDRs 60s polling remains active and unchanged.
 *
 * Reviewer gap: the Shell_1263 smoke test mocks usePendingDRs entirely, so it cannot
 * detect a change to the default polling interval or removal of the setInterval call.
 * These tests call usePendingDRs() directly (no mock) with fake timers and assert
 * the live 60 000 ms default interval behaviour.
 *
 * All tests PASS immediately (implementation is already correct at 60 000 ms) —
 * they are regression guards that will FAIL if the default interval is changed or
 * polling is removed.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { usePendingDRs } from '../hooks/usePendingDRs'

// ─── Fixtures ─────────────────────────────────────────────────────────────────

const EMPTY_RESPONSE = { count: 0, items: [] }

function makeFetch(response: unknown, ok = true) {
  return vi.fn(() =>
    Promise.resolve({
      ok,
      status: ok ? 200 : 404,
      json: () => Promise.resolve(response),
    }),
  )
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('TestFromAC_PendingDRsPollingActive', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.unstubAllGlobals()
  })

  // ─── AC5: default 60s interval is live ────────────────────────────────────
  //
  // Regression guards: these fail if DEFAULT_INTERVAL_MS is changed away from
  // 60 000, or if the polling setInterval is removed from usePendingDRs.

  it('does NOT refetch before 60 000 ms have elapsed (59 999 ms boundary)', async () => {
    const fetchMock = makeFetch(EMPTY_RESPONSE)
    vi.stubGlobal('fetch', fetchMock)

    renderHook(() => usePendingDRs()) // no options — uses default interval
    await act(async () => {}) // settle initial mount fetch
    expect(fetchMock).toHaveBeenCalledTimes(1)

    // 1 ms before the default 60 s interval fires
    await act(async () => { vi.advanceTimersByTime(59_999) })
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it('refetches after exactly 60 000 ms (default interval is 60s, not shortened)', async () => {
    const fetchMock = makeFetch(EMPTY_RESPONSE)
    vi.stubGlobal('fetch', fetchMock)

    renderHook(() => usePendingDRs()) // no options — uses default interval
    await act(async () => {}) // settle initial mount fetch
    expect(fetchMock).toHaveBeenCalledTimes(1)

    await act(async () => { vi.advanceTimersByTime(60_000) })
    // At least 2 calls: 1 mount + 1 interval
    expect(fetchMock.mock.calls.length).toBeGreaterThanOrEqual(2)
  })

  it('polling continues beyond the first interval (not a one-shot timer)', async () => {
    const fetchMock = makeFetch(EMPTY_RESPONSE)
    vi.stubGlobal('fetch', fetchMock)

    renderHook(() => usePendingDRs()) // no options — uses default interval
    await act(async () => {}) // mount
    await act(async () => { vi.advanceTimersByTime(60_000) }) // first interval
    await act(async () => { vi.advanceTimersByTime(60_000) }) // second interval
    // At least 3 calls: 1 mount + 2 intervals
    expect(fetchMock.mock.calls.length).toBeGreaterThanOrEqual(3)
  })
})
