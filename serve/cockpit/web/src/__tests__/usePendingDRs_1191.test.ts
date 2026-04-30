/**
 * RED phase tests for #1191: usePendingDRs polling hook
 *
 * Covers: GET fetch to /api/decisions/pending on mount, configurable
 * intervalMs, state shape (count/items/isLoading/error), empty response,
 * error paths (network failure + non-OK HTTP status), and interval cleanup
 * on unmount.
 * All tests are RED (failing) until the builder implements usePendingDRs.ts.
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
  request_type: 'scope-decision',
  created: '2026-04-30T10:00:00Z',
  title: 'Should we proceed with approach A?',
  body_preview: 'Builder encountered a fork in the road...',
}

const PENDING_RESPONSE = { count: 1, items: [DR_ITEM] }
const EMPTY_RESPONSE = { count: 0, items: [] }

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

  // ─── AC: Test polling hook fetches /api/decisions/pending on interval ──────

  describe('AC1: GET fetch to /api/decisions/pending on mount', () => {
    it('fetches /api/decisions/pending on mount', async () => {
      const fetchMock = makeFetch(PENDING_RESPONSE)
      vi.stubGlobal('fetch', fetchMock)
      renderHook(() => usePendingDRs())
      await act(async () => {})
      expect(fetchMock).toHaveBeenCalledWith('/api/decisions/pending', expect.anything())
    })

    it('uses HTTP method GET for the pending DR fetch', async () => {
      const fetchMock = makeFetch(PENDING_RESPONSE)
      vi.stubGlobal('fetch', fetchMock)
      renderHook(() => usePendingDRs())
      await act(async () => {})
      expect(fetchMock).toHaveBeenCalledWith(
        '/api/decisions/pending',
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

    it('re-fetches multiple times as interval repeats', async () => {
      const fetchMock = makeFetch(PENDING_RESPONSE)
      vi.stubGlobal('fetch', fetchMock)
      renderHook(() => usePendingDRs({ intervalMs: 5_000 }))
      await act(async () => { vi.advanceTimersByTime(15_000) })
      expect(fetchMock.mock.calls.length).toBeGreaterThanOrEqual(3)
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
})
