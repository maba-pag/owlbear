import { isValidElement } from 'react'
import { render } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

const calls = vi.hoisted(() => ({ invalidation: [] as unknown[], change: [] as unknown[] }))

vi.mock('../hooks/NativeInvalidationProvider', () => ({
  NativeInvalidationProvider: vi.fn(({ children }: { children: unknown }) => {
    calls.invalidation.push(children)
    return <div data-testid="invalidation-provider">{children}</div>
  }),
}))
vi.mock('../hooks/NativeChangeProvider', () => ({
  NativeChangeProvider: vi.fn(function NativeChangeProvider({ children }: { children: unknown }) {
    calls.change.push(children)
    return <div data-testid="change-provider">{children}</div>
  }),
  useNativeChangeSelection: () => ({ selectedChangeId: 'change-a' }),
}))
vi.mock('../NativeShell', () => ({ default: () => <div data-testid="native-shell" /> }))

import App from '../App'

describe('App native provider wiring', () => {
  afterEach(() => {
    calls.invalidation.length = 0
    calls.change.length = 0
    vi.clearAllMocks()
  })

  it('mounts NativeInvalidationProvider outside NativeChangeProvider', () => {
    const { getByTestId } = render(<App />)

    expect(calls.invalidation).toHaveLength(1)
    expect(calls.change).toHaveLength(1)
    expect(isValidElement(calls.invalidation[0])).toBe(true)
    expect(getByTestId('invalidation-provider')).toContainElement(getByTestId('change-provider'))
  })

  it('mounts the native shell beneath the change provider', () => {
    const { getByTestId } = render(<App />)
    expect(calls.change).toHaveLength(1)
    expect(getByTestId('native-shell')).toBeInTheDocument()
  })
})
