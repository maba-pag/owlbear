/**
 * useScanPolling hook
 *
 * Covers: POST fetch on mount, configurable intervalMs (default 60 000 ms),
 * state shape (items/isLoading/error), empty-array response, error paths
 * (network failure + non-OK HTTP status), and interval cleanup on unmount.
 */
import React from 'react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useScanPolling } from '../hooks/useScanPolling'
import type { ScanItem } from '../hooks/useScanPolling'

// ─── Fixtures ─────────────────────────────────────────────────────────────────────────────────

const SCAN_ITEM: ScanItem = {
  code: 'TEST001',
  detail: 'A test finding',
  file_path: '/path/to/file.py',
}
const SCAN_ITEMS: ScanItem[] = [SCAN_ITEM]
const EMPTY_SCAN_RESPONSE: ScanItem[] = []

function makeFetch(response: unknown, ok = true) {
  return vi.fn(() =>
    Promise.resolve({ ok, status: ok ? 200 : 500, json: () => Promise.resolve(response) }),
  )
}

// ─── Tests ────────────────────────────────────────────────────────────────────────────────────

describe('TestFromAC_useScanPolling', () => {
  beforeEach(() => { vi.useFakeTimers() })
  afterEach(() => { vi.useRealTimers(); vi.unstubAllGlobals() })

  // ─── AC1: POST fetch on mount ────────────────────────────────────────────────────────────────

  describe('AC1: POST fetch to /api/tasks/scan on mount', () => {
    it('fetches /api/tasks/scan on mount', async () => {
      const fetchMock = makeFetch(SCAN_ITEMS)
      vi.stubGlobal('fetch', fetchMock)
      renderHook(() => useScanPolling())
      await act(async () => {})
      expect(fetchMock).toHaveBeenCalledWith('/api/tasks/scan', expect.anything())
    })

    it('uses HTTP method POST for the scan fetch', async () => {
      const fetchMock = makeFetch(SCAN_ITEMS)
      vi.stubGlobal('fetch', fetchMock)
      renderHook(() => useScanPolling())
      await act(async () => {})
      expect(fetchMock).toHaveBeenCalledWith(
        '/api/tasks/scan',
        expect.objectContaining({ method: 'POST' }),
      )
    })

    it('fetches exactly once on mount before any interval fires', async () => {
      const fetchMock = makeFetch(SCAN_ITEMS)
      vi.stubGlobal('fetch', fetchMock)
      renderHook(() => useScanPolling())
      await act(async () => {})
      expect(fetchMock).toHaveBeenCalledTimes(1)
    })
  })

  // ─── AC2: intervalMs parameter ─────────────────────────────────────────────────────────────────────────────

  describe('AC2: re-fetches at caller-supplied intervalMs (default 60 000 ms)', () => {
    it('re-fetches after the default 60 000 ms interval elapses', async () => {
      const fetchMock = makeFetch(SCAN_ITEMS)
      vi.stubGlobal('fetch', fetchMock)
      renderHook(() => useScanPolling())
      await act(async () => { vi.advanceTimersByTime(60_000) })
      expect(fetchMock.mock.calls.length).toBeGreaterThanOrEqual(2)
    })

    it('does not re-fetch before 60 000 ms have elapsed (default)', async () => {
      const fetchMock = makeFetch(SCAN_ITEMS)
      vi.stubGlobal('fetch', fetchMock)
      renderHook(() => useScanPolling())
      await act(async () => {})
      expect(fetchMock).toHaveBeenCalledTimes(1)
      await act(async () => { vi.advanceTimersByTime(59_999) })
      expect(fetchMock).toHaveBeenCalledTimes(1)
    })

    it('re-fetches at a custom intervalMs when provided', async () => {
      const fetchMock = makeFetch(SCAN_ITEMS)
      vi.stubGlobal('fetch', fetchMock)
      renderHook(() => useScanPolling({ intervalMs: 5_000 }))
      await act(async () => { vi.advanceTimersByTime(5_000) })
      expect(fetchMock.mock.calls.length).toBeGreaterThanOrEqual(2)
    })

    it('does not re-fetch before custom intervalMs has elapsed', async () => {
      const fetchMock = makeFetch(SCAN_ITEMS)
      vi.stubGlobal('fetch', fetchMock)
      renderHook(() => useScanPolling({ intervalMs: 5_000 }))
      await act(async () => {})
      expect(fetchMock).toHaveBeenCalledTimes(1)
      await act(async () => { vi.advanceTimersByTime(4_999) })
      expect(fetchMock).toHaveBeenCalledTimes(1)
    })
  })

  // ─── AC3: state shape ────────────────────────────────────────────────────────────────────────────────────

  describe('AC3: hook exposes items, isLoading, and error', () => {
    it('exposes items as an array', async () => {
      vi.stubGlobal('fetch', makeFetch(SCAN_ITEMS))
      const { result } = renderHook(() => useScanPolling())
      await act(async () => {})
      expect(Array.isArray(result.current.items)).toBe(true)
    })

    it('exposes isLoading as a boolean', async () => {
      vi.stubGlobal('fetch', makeFetch(SCAN_ITEMS))
      const { result } = renderHook(() => useScanPolling())
      await act(async () => {})
      expect(typeof result.current.isLoading).toBe('boolean')
    })

    it('isLoading is true immediately after mount while fetch is in flight', () => {
      vi.stubGlobal('fetch', makeFetch(SCAN_ITEMS))
      const { result } = renderHook(() => useScanPolling())
      expect(result.current.isLoading).toBe(true)
    })

    it('isLoading is false after fetch completes successfully', async () => {
      vi.stubGlobal('fetch', makeFetch(SCAN_ITEMS))
      const { result } = renderHook(() => useScanPolling())
      await act(async () => {})
      expect(result.current.isLoading).toBe(false)
    })

    it('error is null after a successful fetch', async () => {
      vi.stubGlobal('fetch', makeFetch(SCAN_ITEMS))
      const { result } = renderHook(() => useScanPolling())
      await act(async () => {})
      expect(result.current.error).toBeNull()
    })

    it('populates items with ScanItem objects having code, detail, and file_path', async () => {
      vi.stubGlobal('fetch', makeFetch(SCAN_ITEMS))
      const { result } = renderHook(() => useScanPolling())
      await act(async () => {})
      expect(result.current.items).toHaveLength(1)
      const item = result.current.items[0]
      expect(item).toHaveProperty('code', SCAN_ITEM.code)
      expect(item).toHaveProperty('detail', SCAN_ITEM.detail)
      expect(item).toHaveProperty('file_path', SCAN_ITEM.file_path)
    })

    it('ScanItem fields accept null values', async () => {
      const nullItem: ScanItem = { code: null, detail: null, file_path: null }
      vi.stubGlobal('fetch', makeFetch([nullItem]))
      const { result } = renderHook(() => useScanPolling())
      await act(async () => {})
      const item = result.current.items[0]
      expect(item.code).toBeNull()
      expect(item.detail).toBeNull()
      expect(item.file_path).toBeNull()
    })
  })

  // ─── AC4: empty array response ────────────────────────────────────────────────────────────────────────────

  describe('AC4: sets items to [] when response is an empty array', () => {
    it('sets items to empty array when scan response is []', async () => {
      vi.stubGlobal('fetch', makeFetch(EMPTY_SCAN_RESPONSE))
      const { result } = renderHook(() => useScanPolling())
      await act(async () => {})
      expect(result.current.items).toEqual([])
    })

    it('sets items to [] when the 200 OK response payload is not an array (non-array JSON guard)', async () => {
      vi.stubGlobal('fetch', vi.fn(() => Promise.resolve({
        ok: true, status: 200, json: () => Promise.resolve({ not: 'an array' }),
      })))
      const { result } = renderHook(() => useScanPolling())
      await act(async () => {})
      expect(result.current.items).toEqual([])
      expect(result.current.error).toBeNull()
    })
  })

  // ─── AC5: error paths ────────────────────────────────────────────────────────────────────────────────────

  describe('AC5: sets error on network failure or non-OK HTTP status', () => {
    it('sets error to an Error instance on network failure (fetch rejects)', async () => {
      vi.stubGlobal('fetch', vi.fn(() => Promise.reject(new Error('Network error'))))
      const { result } = renderHook(() => useScanPolling())
      await act(async () => {})
      expect(result.current.error).toBeInstanceOf(Error)
    })

    it('sets error to an Error instance on non-OK HTTP status (500)', async () => {
      vi.stubGlobal(
        'fetch',
        vi.fn(() => Promise.resolve({ ok: false, status: 500, json: () => Promise.resolve({}) })),
      )
      const { result } = renderHook(() => useScanPolling())
      await act(async () => {})
      expect(result.current.error).toBeInstanceOf(Error)
    })

    it('items remains [] when a network error occurs', async () => {
      vi.stubGlobal('fetch', vi.fn(() => Promise.reject(new Error('Network error'))))
      const { result } = renderHook(() => useScanPolling())
      await act(async () => {})
      expect(result.current.items).toEqual([])
    })

    it('error is null (not stale) after a successful fetch', async () => {
      vi.stubGlobal('fetch', makeFetch(SCAN_ITEMS))
      const { result } = renderHook(() => useScanPolling())
      await act(async () => {})
      expect(result.current.error).toBeNull()
    })

    it('wraps a non-Error thrown value in an Error instance for the error state ' +
      '(rejection normalization)', async () => {
      vi.stubGlobal(
        'fetch',
        vi.fn(() => Promise.reject('network failure string')),
      )
      const { result } = renderHook(() => useScanPolling())
      await act(async () => {})
      expect(result.current.error).toBeInstanceOf(Error)
      expect(result.current.items).toEqual([])
    })
  })

  // ─── AC6: unmount cleanup ────────────────────────────────────────────────────────────────────────────────

  describe('AC6: clears interval on unmount (no leaked timers)', () => {
    it('does not invoke fetch after the hook is unmounted', async () => {
      const fetchMock = makeFetch(SCAN_ITEMS)
      vi.stubGlobal('fetch', fetchMock)
      const { unmount } = renderHook(() => useScanPolling({ intervalMs: 5_000 }))
      await act(async () => {})
      const callsAfterMount = fetchMock.mock.calls.length
      unmount()
      await act(async () => { vi.advanceTimersByTime(5_000) })
      expect(fetchMock.mock.calls.length).toBe(callsAfterMount)
    })
  })

  // ─── Overlap guard (deferred-fetch proof) ────────────────────────────────────────────────────

  describe('Overlap guard: in-flight request prevents double-fetch', () => {
    it('does not start a second in-flight fetch when the first interval poll is already running', async () => {
      let resolveSlowPoll!: (value: unknown) => void
      const slowPollPromise = new Promise<unknown>((res) => { resolveSlowPoll = res })
      const fetchMock = vi.fn()
        .mockResolvedValueOnce({ ok: true, status: 200, json: () => Promise.resolve(SCAN_ITEMS) })
        .mockImplementationOnce(() =>
          slowPollPromise.then(() => ({ ok: true, status: 200, json: () => Promise.resolve(SCAN_ITEMS) })),
        )
        .mockResolvedValue({ ok: true, status: 200, json: () => Promise.resolve(SCAN_ITEMS) })
      vi.stubGlobal('fetch', fetchMock)

      renderHook(() => useScanPolling({ intervalMs: 5_000 }))
      await act(async () => {})              // mount fetch resolves (call 1)
      expect(fetchMock).toHaveBeenCalledTimes(1)

      act(() => { vi.advanceTimersByTime(5_000) }) // first interval tick → slow fetch starts (call 2, in-flight)
      expect(fetchMock).toHaveBeenCalledTimes(2)

      act(() => { vi.advanceTimersByTime(5_000) }) // second interval tick fires while call 2 is still in-flight
      expect(fetchMock).toHaveBeenCalledTimes(2)   // guard: no third fetch started

      await act(async () => { resolveSlowPoll(undefined) }) // settle slow fetch to avoid timer leaks
    })

    it('queues exactly one repoll after the in-flight request settles when a tick was skipped', async () => {
      let resolveSlowPoll!: (value: unknown) => void
      const slowPollPromise = new Promise<unknown>((res) => { resolveSlowPoll = res })
      const fetchMock = vi.fn()
        .mockResolvedValueOnce({ ok: true, status: 200, json: () => Promise.resolve(SCAN_ITEMS) })
        .mockImplementationOnce(() =>
          slowPollPromise.then(() => ({ ok: true, status: 200, json: () => Promise.resolve(SCAN_ITEMS) })),
        )
        .mockResolvedValue({ ok: true, status: 200, json: () => Promise.resolve(SCAN_ITEMS) })
      vi.stubGlobal('fetch', fetchMock)

      renderHook(() => useScanPolling({ intervalMs: 5_000 }))
      await act(async () => {})              // mount fetch resolves (call 1)

      act(() => { vi.advanceTimersByTime(5_000) }) // first interval tick → slow fetch (call 2, in-flight)
      act(() => { vi.advanceTimersByTime(5_000) }) // second tick skipped → pendingPoll queued
      expect(fetchMock).toHaveBeenCalledTimes(2)

      await act(async () => { resolveSlowPoll(undefined) }) // slow fetch settles → queued repoll fires (call 3)
      expect(fetchMock).toHaveBeenCalledTimes(3)            // exactly one queued repoll, not more
    })
  })

  // ─── AC7: intervalMs reconfiguration during in-flight request ─────────────────────────────────

  describe('AC7: intervalMs reconfiguration during in-flight request', () => {
    it('does not leave isLoading stuck at true when intervalMs changes while a request is in-flight', async () => {
      let resolveSlow!: (value: unknown) => void
      const slowPromise = new Promise<unknown>((res) => { resolveSlow = res })
      const fetchMock = vi.fn()
        .mockImplementationOnce(() =>
          slowPromise.then(() => ({
            ok: true,
            status: 200,
            json: () => Promise.resolve(SCAN_ITEMS),
          })),
        )
        .mockResolvedValue({ ok: true, status: 200, json: () => Promise.resolve(SCAN_ITEMS) })
      vi.stubGlobal('fetch', fetchMock)

      // Mount with intervalMs=5_000; fetch starts in-flight, isLoading=true
      const { result, rerender } = renderHook(
        ({ ms }: { ms: number }) => useScanPolling({ intervalMs: ms }),
        { initialProps: { ms: 5_000 } },
      )
      expect(fetchMock).toHaveBeenCalledTimes(1)
      expect(result.current.isLoading).toBe(true)

      // Rerender with a different intervalMs while call 1 is still in-flight
      rerender({ ms: 10_000 })

      // Settle the original slow request
      await act(async () => { resolveSlow(undefined) })

      // isLoading must reset to false — must not be stuck at true after the request settles
      expect(result.current.isLoading).toBe(false)
    })

    it('items reflect the settled in-flight response after intervalMs reconfiguration', async () => {
      let resolveSlow!: (value: unknown) => void
      const slowPromise = new Promise<unknown>((res) => { resolveSlow = res })
      const fetchMock = vi.fn()
        .mockImplementationOnce(() =>
          slowPromise.then(() => ({
            ok: true,
            status: 200,
            json: () => Promise.resolve(SCAN_ITEMS),
          })),
        )
        .mockResolvedValue({ ok: true, status: 200, json: () => Promise.resolve(SCAN_ITEMS) })
      vi.stubGlobal('fetch', fetchMock)

      const { result, rerender } = renderHook(
        ({ ms }: { ms: number }) => useScanPolling({ intervalMs: ms }),
        { initialProps: { ms: 5_000 } },
      )
      expect(fetchMock).toHaveBeenCalledTimes(1)

      // Rerender while first fetch is in-flight
      rerender({ ms: 10_000 })

      // Settle the slow fetch — items must reflect the response, not remain stale
      await act(async () => { resolveSlow(undefined) })
      expect(result.current.items).toEqual(SCAN_ITEMS)
    })

    // ─── AC7a: no additional fetch starts on rerender while in-flight ──────────────────────────

    it('does not start an additional fetch on rerender when a request is already in-flight (AC7a)', async () => {
      let resolveSlow!: (value: unknown) => void
      const slowPromise = new Promise<unknown>((res) => { resolveSlow = res })
      const fetchMock = vi.fn()
        .mockImplementationOnce(() =>
          slowPromise.then(() => ({
            ok: true,
            status: 200,
            json: () => Promise.resolve(SCAN_ITEMS),
          })),
        )
        .mockResolvedValue({ ok: true, status: 200, json: () => Promise.resolve(SCAN_ITEMS) })
      vi.stubGlobal('fetch', fetchMock)

      const { rerender } = renderHook(
        ({ ms }: { ms: number }) => useScanPolling({ intervalMs: ms }),
        { initialProps: { ms: 5_000 } },
      )
      expect(fetchMock).toHaveBeenCalledTimes(1) // mount call in-flight

      // Rerender while call 1 is in-flight — the new effect's immediate poll() must hit the guard
      rerender({ ms: 10_000 })

      // Fetch count must not increase: the rerender's poll() call hits inFlightRef guard
      expect(fetchMock).toHaveBeenCalledTimes(1)

      // Clean up: settle slow request to avoid timer leaks
      await act(async () => { resolveSlow(undefined) })
    })

    // ─── AC7c: cadence restarts at new intervalMs after settle ────────────────────────────────────

    it('restarts polling at the new intervalMs cadence after the in-flight request settles (AC7c)', async () => {
      let resolveSlow!: (value: unknown) => void
      const slowPromise = new Promise<unknown>((res) => { resolveSlow = res })
      const fetchMock = vi.fn()
        .mockImplementationOnce(() =>
          slowPromise.then(() => ({
            ok: true,
            status: 200,
            json: () => Promise.resolve(SCAN_ITEMS),
          })),
        )
        .mockResolvedValue({ ok: true, status: 200, json: () => Promise.resolve(SCAN_ITEMS) })
      vi.stubGlobal('fetch', fetchMock)

      const { rerender } = renderHook(
        ({ ms }: { ms: number }) => useScanPolling({ intervalMs: ms }),
        { initialProps: { ms: 5_000 } },
      )
      expect(fetchMock).toHaveBeenCalledTimes(1) // mount call in-flight

      // Rerender with new interval while call 1 is in-flight
      rerender({ ms: 10_000 })

      // Settle the slow request — triggers queued repoll (pendingPoll flush)
      await act(async () => { resolveSlow(undefined) })
      const callsAfterSettle = fetchMock.mock.calls.length

      // Advance fake time by the NEW interval — exactly one additional fetch must fire
      await act(async () => { vi.advanceTimersByTime(10_000) })
      expect(fetchMock.mock.calls.length).toBe(callsAfterSettle + 1)
    })
  })

  // ─── AC_StrictMode: isMountedRef lifecycle ───────────────────────────────────

  describe('AC_StrictMode: isMountedRef survives StrictMode effect replay', () => {
    it('clears isLoading and populates items after StrictMode mount-cleanup-remount cycle', async () => {
      // React StrictMode (dev mode) fires effects twice: mount → cleanup → remount.
      // Without restoring isMountedRef.current=true in the effect body, the remounted
      // hook's poll() sees isMountedRef=false (set by cleanup) and suppresses all
      // state updates, leaving isLoading stuck at true and items empty.
      const fetchMock = makeFetch(SCAN_ITEMS)
      vi.stubGlobal('fetch', fetchMock)
      const { result } = renderHook(() => useScanPolling(), { wrapper: React.StrictMode })
      await act(async () => {})
      expect(result.current.isLoading).toBe(false)
      expect(result.current.items).toEqual(SCAN_ITEMS)
    })
  })
})
