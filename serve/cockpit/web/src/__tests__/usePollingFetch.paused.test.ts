import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { usePollingFetch, type UsePollingFetchOptions } from '../hooks/usePollingFetch'

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

describe('usePollingFetch paused polling', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.unstubAllGlobals()
    vi.clearAllMocks()
  })

  it('polls on mount but skips scheduled polls while paused', async () => {
    const fetchMock = makeOkFetch()
    vi.stubGlobal('fetch', fetchMock)

    renderHook(() => usePollingFetch('/api/tasks', { intervalMs: 1_000, paused: true }))
    await act(async () => {})
    await act(async () => { vi.advanceTimersByTime(2_000) })

    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it('allows an explicit refetch while scheduled polling is paused', async () => {
    const fetchMock = makeOkFetch()
    vi.stubGlobal('fetch', fetchMock)

    const { result } = renderHook(() => usePollingFetch('/api/tasks', { intervalMs: 1_000, paused: true }))
    await act(async () => {})
    await act(async () => { result.current.refetch() })

    expect(fetchMock).toHaveBeenCalledTimes(2)
  })

  it('runs a queued explicit refetch after an active request while paused', async () => {
    let releaseFirst!: () => void
    const firstResponse = new Promise<{ ok: boolean; status: number; json: () => Promise<unknown> }>((resolve) => {
      releaseFirst = () => resolve({ ok: true, status: 200, json: () => Promise.resolve({}) })
    })
    const fetchMock = vi
      .fn()
      .mockImplementationOnce(() => firstResponse)
      .mockResolvedValue({ ok: true, status: 200, json: () => Promise.resolve({}) })
    vi.stubGlobal('fetch', fetchMock)

    const { result } = renderHook(() => usePollingFetch('/api/tasks', { intervalMs: 1_000, paused: true }))
    await act(async () => {})
    await act(async () => { result.current.refetch() })
    expect(fetchMock).toHaveBeenCalledTimes(1)

    await act(async () => {
      releaseFirst()
      await Promise.resolve()
    })
    await act(async () => {})

    expect(fetchMock).toHaveBeenCalledTimes(2)
  })

  it('drops a queued interval poll when pausing before the active request completes', async () => {
    const { fn: slowFetch, resolve } = makeSlowFetch()
    vi.stubGlobal('fetch', slowFetch)

    const { rerender } = renderHook(
      (props: UsePollingFetchOptions<unknown>) => usePollingFetch('/api/tasks', props),
      { initialProps: { intervalMs: 500, paused: false } as UsePollingFetchOptions<unknown> },
    )
    await act(async () => { vi.advanceTimersByTime(500) })
    rerender({ intervalMs: 500, paused: true })
    await act(async () => { resolve() })

    expect(slowFetch).toHaveBeenCalledTimes(1)
  })

  it('resumes on the next original interval after pausing and unpausing', async () => {
    const fetchMock = makeOkFetch()
    vi.stubGlobal('fetch', fetchMock)

    const { rerender } = renderHook(
      (props: UsePollingFetchOptions<unknown>) => usePollingFetch('/api/tasks', props),
      { initialProps: { intervalMs: 1_000, paused: true } as UsePollingFetchOptions<unknown> },
    )
    await act(async () => {})
    await act(async () => { vi.advanceTimersByTime(500) })
    rerender({ intervalMs: 1_000, paused: false })
    expect(fetchMock).toHaveBeenCalledTimes(1)

    await act(async () => { vi.advanceTimersByTime(500) })

    expect(fetchMock).toHaveBeenCalledTimes(2)
  })
})
