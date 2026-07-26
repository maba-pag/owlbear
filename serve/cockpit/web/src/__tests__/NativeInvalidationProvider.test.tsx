import { act, renderHook } from '@testing-library/react'
import type { PropsWithChildren } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import {
  NativeInvalidationProvider,
  useNativeInvalidation,
} from '../hooks/NativeInvalidationProvider'

class MockEventSource {
  static instances: MockEventSource[] = []
  readonly listeners = new Map<string, (event: Event) => void>()
  onopen: (() => void) | null = null
  onerror: (() => void) | null = null

  constructor(readonly url: string) {
    MockEventSource.instances.push(this)
  }

  addEventListener(type: string, listener: (event: Event) => void) {
    this.listeners.set(type, listener)
  }

  close = vi.fn()

  open() {
    this.onopen?.()
  }

  emit(resources: string[], token: string) {
    this.listeners.get('native-changed')?.(
      { data: JSON.stringify({ resources, token }) } as MessageEvent<string>,
    )
  }

  fail() {
    this.onerror?.()
  }
}

function wrapper({ children }: PropsWithChildren) {
  return <NativeInvalidationProvider reconnectMs={1_000}>{children}</NativeInvalidationProvider>
}

describe('NativeInvalidationProvider', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    MockEventSource.instances = []
    vi.stubGlobal('EventSource', MockEventSource)
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.unstubAllGlobals()
  })

  it('publishes only monotonic tokens for the affected resource', () => {
    const hook = renderHook(
      () => ({ jobs: useNativeInvalidation('jobs'), requests: useNativeInvalidation('requests') }),
      { wrapper },
    )
    const source = MockEventSource.instances[0]

    act(() => {
      source.open()
      source.emit(['jobs'], '1785057600602000000')
      source.emit(['jobs'], '1785057600601999999')
    })

    expect(hook.result.current.jobs).toEqual({ status: 'open', token: '1785057600602000000' })
    expect(hook.result.current.requests.token).toBeNull()
  })

  it('closes on disconnect and reconnects after the fallback interval', () => {
    const hook = renderHook(() => useNativeInvalidation('jobs'), { wrapper })
    const source = MockEventSource.instances[0]

    act(() => source.fail())
    expect(hook.result.current.status).toBe('closed')

    act(() => vi.advanceTimersByTime(1_000))
    expect(MockEventSource.instances).toHaveLength(2)
  })
})
