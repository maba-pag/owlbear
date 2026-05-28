/**
 * usePendingDRs polling hook
 *
 * Covers: GET fetch to /api/requests/pending on mount, configurable
 * intervalMs, state shape (count/items/isLoading/error), empty response,
 * error paths (network failure + non-OK HTTP status), and interval cleanup
 * on unmount.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { usePendingDRs } from '../hooks/usePendingDRs'
import type { PendingDR } from '../hooks/usePendingDRs'

// ─── Fixtures ─────────────────────────────────────────────────────────────────

const DR_ITEM: PendingDR = {
  id: 'dr-001',
  task_id: 42,
  agent: 'builder',
  request_type: 'decision',
  created: '2026-04-30T10:00:00Z',
  title: 'Should we proceed with approach A?',
  summary: 'Builder encountered a fork in the road...',
  kind: 'decision',
  options: [],
  body: '',
  body_preview: 'Builder encountered a fork in the road...',
}

const REQUEST_ITEM = {
  request_id: 'dr-001',
  task_id: 42,
  kind: 'decision' as const,
  title: 'Should we proceed with approach A?',
  summary: 'Builder encountered a fork in the road...',
  agent: 'builder',
  created_at: '2026-04-30T10:00:00Z',
  options: [],
  body: '',
}

// Bare-array format returned by GET /api/requests/pending (new contract from #1856)
const PENDING_RESPONSE = [REQUEST_ITEM]
const EMPTY_RESPONSE: PendingDR[] = []

function makeFetch(response: unknown, ok = true) {
  return vi.fn(() =>
    Promise.resolve({
      ok,
      status: ok ? 200 : 500,
      json: () => Promise.resolve(response),
    }),
  )
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('TestFromAC_usePendingDRs', () => {
  beforeEach(() => { vi.useFakeTimers() })
  afterEach(() => { vi.useRealTimers(); vi.unstubAllGlobals() })

  // ─── AC: Test polling hook fetches /api/requests/pending on interval ──────

  describe('AC1: GET fetch to /api/requests/pending on mount', () => {
    it('fetches /api/requests/pending on mount', async () => {
      const fetchMock = makeFetch(PENDING_RESPONSE)
      vi.stubGlobal('fetch', fetchMock)
      renderHook(() => usePendingDRs())
      await act(async () => {})
      expect(fetchMock).toHaveBeenCalledWith('/api/requests/pending', expect.anything())
    })

    it('uses HTTP method GET for the pending DR fetch', async () => {
      const fetchMock = makeFetch(PENDING_RESPONSE)
      vi.stubGlobal('fetch', fetchMock)
      renderHook(() => usePendingDRs())
      await act(async () => {})
      expect(fetchMock).toHaveBeenCalledWith(
        '/api/requests/pending',
        expect.objectContaining({ method: 'GET' }),
      )
    })

    it('fetches exactly once on mount before any interval fires', async () => {
      const fetchMock = makeFetch(PENDING_RESPONSE)
      vi.stubGlobal('fetch', fetchMock)
      renderHook(() => usePendingDRs())
      await act(async () => {})
      expect(fetchMock).toHaveBeenCalledTimes(1)
    })
  })

  describe('AC2: re-fetches at configurable intervalMs', () => {
    it('re-fetches at a custom intervalMs when provided', async () => {
      const fetchMock = makeFetch(PENDING_RESPONSE)
      vi.stubGlobal('fetch', fetchMock)
      renderHook(() => usePendingDRs({ intervalMs: 5_000 }))
      await act(async () => { vi.advanceTimersByTime(5_000) })
      expect(fetchMock.mock.calls.length).toBeGreaterThanOrEqual(2)
    })

    it('does not re-fetch before custom intervalMs has elapsed', async () => {
      const fetchMock = makeFetch(PENDING_RESPONSE)
      vi.stubGlobal('fetch', fetchMock)
      renderHook(() => usePendingDRs({ intervalMs: 5_000 }))
      await act(async () => {})
      expect(fetchMock).toHaveBeenCalledTimes(1)
      await act(async () => { vi.advanceTimersByTime(4_999) })
      expect(fetchMock).toHaveBeenCalledTimes(1)
    })

    it('re-fetches multiple times as interval repeats (AC12: settled between intervals)', async () => {
      // AC12: settle mount fetch first, then advance one interval at a time.
      // Proves independent repeated polling without overlap interaction.
      // With the coalesced boolean-ref pattern, each settled interval adds exactly 1 call.
      const fetchMock = makeFetch(PENDING_RESPONSE)
      vi.stubGlobal('fetch', fetchMock)
      renderHook(() => usePendingDRs({ intervalMs: 5_000 }))
      await act(async () => {})                                    // settle mount fetch (call 1)
      expect(fetchMock).toHaveBeenCalledTimes(1)
      await act(async () => { vi.advanceTimersByTime(5_000) })    // first interval tick + settle (call 2)
      expect(fetchMock).toHaveBeenCalledTimes(2)
      await act(async () => { vi.advanceTimersByTime(5_000) })    // second interval tick + settle (call 3)
      expect(fetchMock).toHaveBeenCalledTimes(3)
    })
  })

  // ─── AC3: hook exposes count, items, isLoading, and error ─────────────────

  describe('AC3: state shape — count, items, isLoading, error', () => {
    it('exposes count as a number after successful fetch', async () => {
      vi.stubGlobal('fetch', makeFetch(PENDING_RESPONSE))
      const { result } = renderHook(() => usePendingDRs())
      await act(async () => {})
      expect(typeof result.current.count).toBe('number')
    })

    it('exposes items as an array after successful fetch', async () => {
      vi.stubGlobal('fetch', makeFetch(PENDING_RESPONSE))
      const { result } = renderHook(() => usePendingDRs())
      await act(async () => {})
      expect(Array.isArray(result.current.items)).toBe(true)
    })

    it('exposes isLoading as a boolean', async () => {
      vi.stubGlobal('fetch', makeFetch(PENDING_RESPONSE))
      const { result } = renderHook(() => usePendingDRs())
      await act(async () => {})
      expect(typeof result.current.isLoading).toBe('boolean')
    })

    it('isLoading is true immediately after mount while fetch is in flight', () => {
      vi.stubGlobal('fetch', makeFetch(PENDING_RESPONSE))
      const { result } = renderHook(() => usePendingDRs())
      expect(result.current.isLoading).toBe(true)
    })

    it('isLoading is false after fetch completes successfully', async () => {
      vi.stubGlobal('fetch', makeFetch(PENDING_RESPONSE))
      const { result } = renderHook(() => usePendingDRs())
      await act(async () => {})
      expect(result.current.isLoading).toBe(false)
    })

    it('error is null after a successful fetch', async () => {
      vi.stubGlobal('fetch', makeFetch(PENDING_RESPONSE))
      const { result } = renderHook(() => usePendingDRs())
      await act(async () => {})
      expect(result.current.error).toBeNull()
    })

    it('populates count from API response', async () => {
      vi.stubGlobal('fetch', makeFetch(PENDING_RESPONSE))
      const { result } = renderHook(() => usePendingDRs())
      await act(async () => {})
      expect(result.current.count).toBe(1)
    })

    it('populates items with PendingDR objects having all required fields', async () => {
      vi.stubGlobal('fetch', makeFetch(PENDING_RESPONSE))
      const { result } = renderHook(() => usePendingDRs())
      await act(async () => {})
      expect(result.current.items).toHaveLength(1)
      const item = result.current.items[0]
      expect(item).toHaveProperty('id', DR_ITEM.id)
      expect(item).toHaveProperty('task_id', DR_ITEM.task_id)
      expect(item).toHaveProperty('agent', DR_ITEM.agent)
      expect(item).toHaveProperty('request_type', DR_ITEM.request_type)
      expect(item).toHaveProperty('created', DR_ITEM.created)
      expect(item).toHaveProperty('title', DR_ITEM.title)
      expect(item).toHaveProperty('body_preview', DR_ITEM.body_preview)
    })
  })

  // ─── AC: Test empty state (0 pending) renders dormant indicator ────────────
  // (hook side: must deliver count=0, items=[] for empty API response)

  describe('AC4: empty response → count=0, items=[]', () => {
    it('sets count to 0 when API returns empty pending list', async () => {
      vi.stubGlobal('fetch', makeFetch(EMPTY_RESPONSE))
      const { result } = renderHook(() => usePendingDRs())
      await act(async () => {})
      expect(result.current.count).toBe(0)
    })

    it('sets items to empty array when API returns empty pending list', async () => {
      vi.stubGlobal('fetch', makeFetch(EMPTY_RESPONSE))
      const { result } = renderHook(() => usePendingDRs())
      await act(async () => {})
      expect(result.current.items).toEqual([])
    })
  })

  // ─── AC5: error paths ──────────────────────────────────────────────────────

  describe('AC5: error paths — network failure and non-OK HTTP status', () => {
    it('sets error to an Error instance on network failure (fetch rejects)', async () => {
      vi.stubGlobal('fetch', vi.fn(() => Promise.reject(new Error('Network error'))))
      const { result } = renderHook(() => usePendingDRs())
      await act(async () => {})
      expect(result.current.error).toBeInstanceOf(Error)
    })

    it('sets error to an Error instance on non-OK HTTP status (500)', async () => {
      vi.stubGlobal('fetch', makeFetch({}, false))
      const { result } = renderHook(() => usePendingDRs())
      await act(async () => {})
      expect(result.current.error).toBeInstanceOf(Error)
    })

    it('keeps items as an array on fetch error (does not crash)', async () => {
      vi.stubGlobal('fetch', vi.fn(() => Promise.reject(new Error('Network error'))))
      const { result } = renderHook(() => usePendingDRs())
      await act(async () => {})
      expect(Array.isArray(result.current.items)).toBe(true)
    })

    it('isLoading is false after a failed fetch', async () => {
      vi.stubGlobal('fetch', vi.fn(() => Promise.reject(new Error('Network error'))))
      const { result } = renderHook(() => usePendingDRs())
      await act(async () => {})
      expect(result.current.isLoading).toBe(false)
    })
  })

  // ─── AC6: interval cleanup on unmount ─────────────────────────────────────

  describe('AC6: interval stops firing after unmount', () => {
    it('stops re-fetching after component unmounts', async () => {
      const fetchMock = makeFetch(PENDING_RESPONSE)
      vi.stubGlobal('fetch', fetchMock)
      const { unmount } = renderHook(() => usePendingDRs({ intervalMs: 5_000 }))
      await act(async () => {})
      const callCountAtUnmount = fetchMock.mock.calls.length
      unmount()
      await act(async () => { vi.advanceTimersByTime(15_000) })
      expect(fetchMock.mock.calls.length).toBe(callCountAtUnmount)
    })
  })

  // ─── AC9: overlap guard — in-flight fetch blocks concurrent second fetch ──

  describe('AC9: overlap guard — interval tick while fetch in-flight does not start a concurrent second fetch', () => {
    it('does not start a second fetch when first interval poll is still in flight', async () => {
      let resolveSlowPoll!: (value: unknown) => void
      const slowPollPromise = new Promise<unknown>((res) => { resolveSlowPoll = res })
      const fetchMock = vi.fn()
        .mockResolvedValueOnce({ ok: true, status: 200, json: () => Promise.resolve(PENDING_RESPONSE) })
        .mockImplementationOnce(() =>
          slowPollPromise.then(() => ({ ok: true, status: 200, json: () => Promise.resolve(PENDING_RESPONSE) })),
        )
        .mockResolvedValue({ ok: true, status: 200, json: () => Promise.resolve(PENDING_RESPONSE) })
      vi.stubGlobal('fetch', fetchMock)

      renderHook(() => usePendingDRs({ intervalMs: 5_000 }))
      await act(async () => {})                           // mount fetch resolves (call 1)
      expect(fetchMock).toHaveBeenCalledTimes(1)

      act(() => { vi.advanceTimersByTime(5_000) })        // first interval tick → slow fetch starts (call 2, in-flight)
      expect(fetchMock).toHaveBeenCalledTimes(2)

      act(() => { vi.advanceTimersByTime(5_000) })        // second interval tick while call 2 still in-flight
      expect(fetchMock).toHaveBeenCalledTimes(2)          // guard: no third fetch started — FAILS with current impl

      await act(async () => { resolveSlowPoll(undefined) }) // settle slow fetch to avoid timer leaks
    })

    it('queues exactly one repoll after the in-flight request resolves when a tick was skipped', async () => {
      let resolveSlowPoll!: (value: unknown) => void
      const slowPollPromise = new Promise<unknown>((res) => { resolveSlowPoll = res })
      const fetchMock = vi.fn()
        .mockResolvedValueOnce({ ok: true, status: 200, json: () => Promise.resolve(PENDING_RESPONSE) })
        .mockImplementationOnce(() =>
          slowPollPromise.then(() => ({ ok: true, status: 200, json: () => Promise.resolve(PENDING_RESPONSE) })),
        )
        .mockResolvedValue({ ok: true, status: 200, json: () => Promise.resolve(PENDING_RESPONSE) })
      vi.stubGlobal('fetch', fetchMock)

      renderHook(() => usePendingDRs({ intervalMs: 5_000 }))
      await act(async () => {})                           // mount fetch resolves (call 1)

      act(() => { vi.advanceTimersByTime(5_000) })        // first interval tick → slow fetch (call 2, in-flight)
      act(() => { vi.advanceTimersByTime(5_000) })        // second tick → pending poll queued (guard), NOT eager call 3
      expect(fetchMock).toHaveBeenCalledTimes(2)          // guard: call 2 still in-flight → FAILS with current impl

      await act(async () => { resolveSlowPoll(undefined) }) // slow fetch settles → queued repoll fires (call 3)
      expect(fetchMock).toHaveBeenCalledTimes(3)            // exactly one queued repoll, not more
    })
  })

  // ─── AC11: multi-tick coalescing — 3+ skipped ticks → exactly 1 repoll ───

  describe('AC11: multi-tick coalescing — 3+ skipped ticks yield exactly 1 repoll', () => {
    it('coalesces 3 skipped interval ticks into exactly 1 repoll after in-flight settles', async () => {
      // Discriminates boolean coalesced (pendingPollRef) from counted replay
      // (pendingPollCountRef). Counted replay fires 3 repolls; coalesced fires 1.
      let resolveSlowPoll!: (value: unknown) => void
      const slowPollPromise = new Promise<unknown>((res) => { resolveSlowPoll = res })
      const fetchMock = vi.fn()
        .mockResolvedValueOnce({ ok: true, status: 200, json: () => Promise.resolve(PENDING_RESPONSE) })
        .mockImplementationOnce(() =>
          slowPollPromise.then(() => ({ ok: true, status: 200, json: () => Promise.resolve(PENDING_RESPONSE) })),
        )
        .mockResolvedValue({ ok: true, status: 200, json: () => Promise.resolve(PENDING_RESPONSE) })
      vi.stubGlobal('fetch', fetchMock)

      renderHook(() => usePendingDRs({ intervalMs: 5_000 }))
      await act(async () => {})                           // mount fetch resolves (call 1)
      expect(fetchMock).toHaveBeenCalledTimes(1)

      act(() => { vi.advanceTimersByTime(5_000) })        // first interval tick → slow fetch starts (call 2, in-flight)
      expect(fetchMock).toHaveBeenCalledTimes(2)

      act(() => { vi.advanceTimersByTime(5_000) })        // tick 2 while call 2 in-flight → skipped
      act(() => { vi.advanceTimersByTime(5_000) })        // tick 3 while call 2 in-flight → skipped
      act(() => { vi.advanceTimersByTime(5_000) })        // tick 4 while call 2 in-flight → skipped
      expect(fetchMock).toHaveBeenCalledTimes(2)          // guard: 3 skipped ticks, no extra fetches started

      await act(async () => { resolveSlowPoll(undefined) }) // slow fetch settles
      // Coalesced (boolean ref): exactly 1 repoll fires → total 3 calls
      // Counted replay (pendingPollCountRef=3): fires 3 repolls → total 5+ calls → FAILS
      expect(fetchMock).toHaveBeenCalledTimes(3)
    })
  })
})
