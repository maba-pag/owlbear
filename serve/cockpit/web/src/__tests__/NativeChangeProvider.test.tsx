import { act, renderHook, waitFor } from '@testing-library/react'
import type { PropsWithChildren } from 'react'
import { MemoryRouter, useLocation } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { NativeChangeProvider, useNativeChangeSelection } from '../hooks/NativeChangeProvider'

const hooks = vi.hoisted(() => ({
  changes: {
    data: {
      changes: [
        { change_id: 'change-a', state: 'loaded', delivery_digest: 'a'.repeat(64), diagnostics: [] },
        { change_id: 'change-b', state: 'invalid', delivery_digest: null, diagnostics: [] },
      ],
    },
    error: null,
    isLoading: false,
    retry: vi.fn(),
  },
  detail: { data: { change_id: 'change-a' }, error: null, isLoading: false, retry: vi.fn() },
}))

vi.mock('../hooks/useNativeResources', () => ({
  useNativeChanges: vi.fn(() => hooks.changes),
  useNativeChange: vi.fn(() => hooks.detail),
}))

function wrapper({ children }: PropsWithChildren) {
  return (
    <MemoryRouter initialEntries={['/?change=change-b']}>
      <NativeChangeProvider>{children}</NativeChangeProvider>
    </MemoryRouter>
  )
}

describe('NativeChangeProvider', () => {
  afterEach(() => vi.clearAllMocks())

  afterEach(() => {
    hooks.changes.data = {
      changes: [
        { change_id: 'change-a', state: 'loaded', delivery_digest: 'a'.repeat(64), diagnostics: [] },
        { change_id: 'change-b', state: 'invalid', delivery_digest: null, diagnostics: [] },
      ],
    }
    hooks.changes.error = null
    hooks.changes.isLoading = false
  })

  it('selects the URL change and exposes invalid authority without loading detail', () => {
    const hook = renderHook(
      () => ({ selection: useNativeChangeSelection(), location: useLocation() }),
      { wrapper },
    )

    expect(hook.result.current.selection.selectedChangeId).toBe('change-b')
    expect(hook.result.current.selection.selectedSummary?.state).toBe('invalid')
    expect(hook.result.current.selection.missingChangeId).toBeNull()
    expect(hook.result.current.selection.detail).toBeNull()
    expect(hook.result.current.location.search).toBe('?change=change-b')
  })

  it('preserves an unknown URL change as an explicit missing state', () => {
    function missingWrapper({ children }: PropsWithChildren) {
      return (
        <MemoryRouter initialEntries={['/?change=missing-change']}>
          <NativeChangeProvider>{children}</NativeChangeProvider>
        </MemoryRouter>
      )
    }
    const hook = renderHook(
      () => ({ selection: useNativeChangeSelection(), location: useLocation() }),
      { wrapper: missingWrapper },
    )

    expect(hook.result.current.selection.selectedChangeId).toBe('missing-change')
    expect(hook.result.current.selection.missingChangeId).toBe('missing-change')
    expect(hook.result.current.selection.selectedSummary).toBeNull()
    expect(hook.result.current.location.search).toBe('?change=missing-change')
  })

  it('does not classify a requested change as missing while summaries load', () => {
    hooks.changes.data = null as unknown as typeof hooks.changes.data
    hooks.changes.isLoading = true
    const hook = renderHook(() => useNativeChangeSelection(), { wrapper })

    expect(hook.result.current.isLoading).toBe(true)
    expect(hook.result.current.missingChangeId).toBeNull()
  })

  it('does not classify a requested change as missing when summaries fail', () => {
    hooks.changes.data = null as unknown as typeof hooks.changes.data
    hooks.changes.error = new Error('summaries unavailable')
    const hook = renderHook(() => useNativeChangeSelection(), { wrapper })

    expect(hook.result.current.error?.message).toBe('summaries unavailable')
    expect(hook.result.current.missingChangeId).toBeNull()
  })

  it('stores a selected change in the existing URL', async () => {
    const hook = renderHook(
      () => ({ selection: useNativeChangeSelection(), location: useLocation() }),
      { wrapper },
    )

    act(() => hook.result.current.selection.selectChange('change-a'))

    await waitFor(() => expect(hook.result.current.location.search).toBe('?change=change-a'))
  })
})
