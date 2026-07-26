import { act, renderHook, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { NativeApiError } from '../api/native'
import { useNativeChange } from '../hooks/useNativeResources'

const invalidation = vi.hoisted(() => ({ status: 'open' as const, token: null as string | null }))

vi.mock('../hooks/NativeInvalidationProvider', () => ({
  useNativeInvalidation: vi.fn(() => invalidation),
}))

describe('native retained value hooks', () => {
  afterEach(() => {
    invalidation.token = null
    vi.unstubAllGlobals()
  })

  it('ignores a late response from the previous change owner', async () => {
    let resolveA!: (value: Response) => void
    const fetchMock = vi
      .fn()
      .mockImplementationOnce(() => new Promise<Response>((resolve) => { resolveA = resolve }))
      .mockResolvedValueOnce({ ok: true, json: async () => ({ change_id: 'change-b' }) } as Response)
    vi.stubGlobal('fetch', fetchMock)
    const hook = renderHook(({ changeId }) => useNativeChange(changeId), {
      initialProps: { changeId: 'change-a' },
    })

    hook.rerender({ changeId: 'change-b' })
    await act(async () => resolveA({ ok: true, json: async () => ({ change_id: 'change-a' }) } as Response))

    await waitFor(() => expect(hook.result.current.data).toMatchObject({ change_id: 'change-b' }))
  })

  it('retains prior data after a token refresh fails and recovers on retry', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({ ok: true, json: async () => ({ change_id: 'change' }) } as Response)
      .mockResolvedValueOnce({
        ok: false,
        status: 503,
        json: async () => ({ detail: { code: 'ERR_NATIVE_CONTEXT_UNAVAILABLE', detail: 'unavailable' } }),
      } as Response)
      .mockResolvedValueOnce({ ok: true, json: async () => ({ change_id: 'recovered' }) } as Response)
    vi.stubGlobal('fetch', fetchMock)
    const hook = renderHook(() => useNativeChange('change'))
    await waitFor(() => expect(hook.result.current.data).toMatchObject({ change_id: 'change' }))

    invalidation.token = '1785057600602000000'
    hook.rerender()
    await waitFor(() => expect(hook.result.current.error).toBeInstanceOf(NativeApiError))
    expect(hook.result.current.data).toMatchObject({ change_id: 'change' })

    act(() => hook.result.current.retry())
    await waitFor(() => expect(hook.result.current.data).toMatchObject({ change_id: 'recovered' }))
  })
})
