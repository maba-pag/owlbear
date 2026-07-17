import { act, renderHook } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useMemoryPurgeFlow } from '../hooks/useCleanupFlow'

function response(body: unknown, ok = true): Response {
  return { ok, status: ok ? 200 : 500, json: async () => body, text: async () => JSON.stringify(body) } as Response
}

describe('useMemoryPurgeFlow', () => {
  beforeEach(() => vi.restoreAllMocks())

  it('keeps only the preview for the current threshold and executes it once', async () => {
    let resolveFirst!: (value: Response) => void
    const fetchMock = vi.spyOn(globalThis, 'fetch')
      .mockImplementationOnce(() => new Promise((resolve) => { resolveFirst = resolve }))
      .mockResolvedValueOnce(response({ deleted_total: 2, eligible: 2, too_recent: 0 }))
      .mockResolvedValueOnce(response({ purged: 2, skipped: 0, failed: 0 }))
    const onSuccess = vi.fn()
    const { result } = renderHook(() => useMemoryPurgeFlow({ onSuccess }))

    act(() => { result.current.setThreshold('10') })
    const firstPreview = result.current.requestPreview()
    act(() => { result.current.setThreshold('20') })
    await act(async () => { await result.current.requestPreview() })
    expect(result.current.preview?.eligible).toBe(2)
    await act(async () => { resolveFirst(response({ deleted_total: 1, eligible: 1, too_recent: 0 })); await firstPreview })
    expect(result.current.preview?.eligible).toBe(2)

    const firstConfirm = result.current.confirmPurge()
    const secondConfirm = result.current.confirmPurge()
    await act(async () => { await Promise.all([firstConfirm, secondConfirm]) })
    expect(fetchMock).toHaveBeenCalledTimes(3)
    expect(JSON.parse(String(fetchMock.mock.calls[2][1]?.body))).toEqual({ min_age_days: 20 })
    expect(result.current.receipt).toEqual({ purged: 2, skipped: 0, failed: 0 })
    expect(onSuccess).toHaveBeenCalledOnce()
  })

  it('rejects invalid thresholds without requesting preview or purge', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch')
    const { result } = renderHook(() => useMemoryPurgeFlow())
    for (const value of ['-1', '1.5', '', 'days']) {
      act(() => { result.current.setThreshold(value) })
      await act(async () => { await result.current.requestPreview() })
      expect(result.current.error).toBe('Threshold must be a nonnegative whole number')
    }
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('exposes preview and execution errors without completion', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(response({ detail: 'unavailable' }, false))
    const onSuccess = vi.fn()
    const { result } = renderHook(() => useMemoryPurgeFlow({ onSuccess }))
    await act(async () => { await result.current.requestPreview() })
    expect(result.current.phase).toBe('error')
    expect(onSuccess).not.toHaveBeenCalled()
    expect(fetchMock).toHaveBeenCalledOnce()
  })
})