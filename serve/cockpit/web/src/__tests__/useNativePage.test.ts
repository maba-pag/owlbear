import { act, renderHook, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { NativeApiError, type NativePage } from '../api/native'
import { useNativePage } from '../hooks/useNativePage'

const invalidation = vi.hoisted(() => ({ status: 'open' as 'open' | 'closed', token: null as string | null }))

vi.mock('../hooks/NativeInvalidationProvider', () => ({
  useNativeInvalidation: vi.fn(() => invalidation),
}))

interface Row {
  id: number
  label: string
}

function page(items: Row[], nextCursor: string | null): NativePage<Row> {
  return { items, next_cursor: nextCursor }
}

function useRows(load: (cursor?: string) => Promise<NativePage<Row>>, pollIntervalMs = 1_000) {
  return useNativePage({ resource: 'jobs', load, identity: (row) => row.id, pollIntervalMs })
}

describe('useNativePage', () => {
  afterEach(() => {
    vi.useRealTimers()
    invalidation.status = 'open'
    invalidation.token = null
    vi.clearAllMocks()
  })

  it('appends only unseen identities on load more', async () => {
    const load = vi
      .fn<(cursor?: string) => Promise<NativePage<Row>>>()
      .mockResolvedValueOnce(page([{ id: 1, label: 'one' }], 'cursor-1'))
      .mockResolvedValueOnce(page([{ id: 1, label: 'duplicate' }, { id: 2, label: 'two' }], null))
    const hook = renderHook(() => useRows(load))
    await waitFor(() => expect(hook.result.current.items).toEqual([{ id: 1, label: 'one' }]))

    act(() => hook.result.current.loadMore())
    await waitFor(() => expect(hook.result.current.items).toHaveLength(2))

    expect(hook.result.current.items).toEqual([
      { id: 1, label: 'one' },
      { id: 2, label: 'two' },
    ])
    expect(load).toHaveBeenLastCalledWith('cursor-1')
  })

  it('retains rows and resets cursor when load more reports ERR_CURSOR_STALE', async () => {
    const load = vi
      .fn<(cursor?: string) => Promise<NativePage<Row>>>()
      .mockResolvedValueOnce(page([{ id: 1, label: 'one' }], 'cursor-1'))
      .mockRejectedValueOnce(
        new NativeApiError(409, { code: 'ERR_CURSOR_STALE', detail: 'cursor is not current' }),
      )
      .mockResolvedValueOnce(page([{ id: 1, label: 'fresh' }], null))
    const hook = renderHook(() => useRows(load))
    await waitFor(() => expect(hook.result.current.nextCursor).toBe('cursor-1'))

    act(() => hook.result.current.loadMore())
    await waitFor(() => expect(hook.result.current.retryFromStart).toBe(true))

    expect(hook.result.current.items).toEqual([{ id: 1, label: 'one' }])
    expect(hook.result.current.nextCursor).toBeNull()
    act(() => hook.result.current.retry())
    await waitFor(() => expect(hook.result.current.items).toEqual([{ id: 1, label: 'fresh' }]))
    expect(load).toHaveBeenLastCalledWith(undefined)
  })

  it('retains prior payload after failed refresh and exposes retry', async () => {
    const load = vi
      .fn<(cursor?: string) => Promise<NativePage<Row>>>()
      .mockResolvedValueOnce(page([{ id: 1, label: 'one' }], null))
      .mockRejectedValueOnce(new NativeApiError(503, { code: 'ERR_NATIVE_CONTEXT_UNAVAILABLE' }))
      .mockResolvedValueOnce(page([{ id: 1, label: 'recovered' }], null))
    const hook = renderHook(() => useRows(load))
    await waitFor(() => expect(hook.result.current.items).toHaveLength(1))

    act(() => hook.result.current.retry())
    await waitFor(() => expect(hook.result.current.error).toBeInstanceOf(NativeApiError))
    expect(hook.result.current.items[0].label).toBe('one')

    act(() => hook.result.current.retry())
    await waitFor(() => expect(hook.result.current.items[0].label).toBe('recovered'))
    expect(hook.result.current.error).toBeNull()
  })

  it('polls only while SSE is disconnected', async () => {
    vi.useFakeTimers()
    invalidation.status = 'closed'
    const load = vi.fn<(cursor?: string) => Promise<NativePage<Row>>>().mockResolvedValue(page([], null))
    renderHook(() => useRows(load, 1_000))
    await act(async () => {})

    await act(async () => vi.advanceTimersByTime(2_000))
    expect(load.mock.calls.length).toBeGreaterThanOrEqual(2)
  })

  it('refreshes once for a higher native token and ignores repeated tokens', async () => {
    const load = vi.fn<(cursor?: string) => Promise<NativePage<Row>>>().mockResolvedValue(page([], null))
    const hook = renderHook(() => useRows(load))
    await waitFor(() => expect(load).toHaveBeenCalledTimes(1))

    invalidation.token = '1785057600602000000'
    hook.rerender()
    await waitFor(() => expect(load).toHaveBeenCalledTimes(2))
    hook.rerender()

    expect(load).toHaveBeenCalledTimes(2)
  })

  it('does not interval poll while SSE is open', async () => {
    vi.useFakeTimers()
    invalidation.status = 'open'
    const load = vi.fn<(cursor?: string) => Promise<NativePage<Row>>>().mockResolvedValue(page([], null))
    renderHook(() => useRows(load, 1_000))
    await act(async () => {})

    await act(async () => vi.advanceTimersByTime(5_000))
    expect(load).toHaveBeenCalledTimes(1)
  })

  it('does not duplicate the initial page request when a provider token predates mount', async () => {
    invalidation.token = '1785057600602000000'
    const load = vi.fn<(cursor?: string) => Promise<NativePage<Row>>>().mockResolvedValue(page([], null))

    renderHook(() => useRows(load))

    await waitFor(() => expect(load).toHaveBeenCalledTimes(1))
  })

  it('queues an SSE refresh that arrives while the initial request is in flight', async () => {
    let resolveInitial!: (value: NativePage<Row>) => void
    const load = vi
      .fn<(cursor?: string) => Promise<NativePage<Row>>>()
      .mockImplementationOnce(() => new Promise((resolve) => { resolveInitial = resolve }))
      .mockResolvedValueOnce(page([{ id: 1, label: 'fresh' }], null))
    const hook = renderHook(() => useRows(load))
    await waitFor(() => expect(load).toHaveBeenCalledTimes(1))

    invalidation.token = '1785057600602000000'
    hook.rerender()
    await act(async () => resolveInitial(page([{ id: 1, label: 'old' }], null)))

    await waitFor(() => expect(load).toHaveBeenCalledTimes(2))
    await waitFor(() => expect(hook.result.current.items[0].label).toBe('fresh'))
  })

  it('does not publish a late response after the loader owner changes', async () => {
    let resolveA!: (value: NativePage<Row>) => void
    const loadA = vi.fn(() => new Promise<NativePage<Row>>((resolve) => { resolveA = resolve }))
    const loadB = vi.fn().mockResolvedValue(page([{ id: 2, label: 'change-b' }], null))
    const hook = renderHook(({ load }) => useRows(load), { initialProps: { load: loadA } })
    await waitFor(() => expect(loadA).toHaveBeenCalledTimes(1))

    hook.rerender({ load: loadB })
    await act(async () => resolveA(page([{ id: 1, label: 'change-a' }], null)))

    await waitFor(() => expect(loadB).toHaveBeenCalledTimes(1))
    await waitFor(() => expect(hook.result.current.items).toEqual([{ id: 2, label: 'change-b' }]))
  })

  it('starts the replacement loader even when the previous owner never settles', async () => {
    const loadA = vi.fn(() => new Promise<NativePage<Row>>(() => undefined))
    const loadB = vi.fn().mockResolvedValue(page([{ id: 2, label: 'change-b' }], null))
    const hook = renderHook(({ load }) => useRows(load), { initialProps: { load: loadA } })
    await waitFor(() => expect(loadA).toHaveBeenCalledTimes(1))

    hook.rerender({ load: loadB })

    await waitFor(() => expect(loadB).toHaveBeenCalledTimes(1))
    await waitFor(() => expect(hook.result.current.items).toEqual([{ id: 2, label: 'change-b' }]))
  })

  it('keeps the replacement owner loading when the stale request settles first', async () => {
    let resolveA!: (value: NativePage<Row>) => void
    let resolveB!: (value: NativePage<Row>) => void
    const loadA = vi.fn(() => new Promise<NativePage<Row>>((resolve) => { resolveA = resolve }))
    const loadB = vi.fn(() => new Promise<NativePage<Row>>((resolve) => { resolveB = resolve }))
    const hook = renderHook(({ load }) => useRows(load), { initialProps: { load: loadA } })
    await waitFor(() => expect(loadA).toHaveBeenCalledTimes(1))

    hook.rerender({ load: loadB })
    await waitFor(() => expect(loadB).toHaveBeenCalledTimes(1))
    await act(async () => resolveA(page([{ id: 1, label: 'change-a' }], null)))

    expect(hook.result.current.isLoading).toBe(true)
    await act(async () => resolveB(page([{ id: 2, label: 'change-b' }], null)))
    await waitFor(() => expect(hook.result.current.isLoading).toBe(false))
  })
})
